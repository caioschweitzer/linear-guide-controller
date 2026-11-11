#include "modbus_slave.h"
#include "gpio_safety.h"
#include "shared_data.h"
#include <math.h>
#include <string.h>

#ifndef HOST_TEST
#include "driver/usb_serial_jtag.h"
#include "driver/uart.h"
#include "esp_log.h"
#endif

// Internal buffers mapped to Modbus stack
holding_reg_params_t g_modbus_holding_reg = {0};
input_reg_params_t g_modbus_input_reg = {0};
discrete_reg_params_t g_modbus_discrete_reg = {0};
coil_reg_params_t g_modbus_coil_reg = {0};

// Helper to convert float to 2 x uint16 (Big-Endian IEEE 754)
static void float_to_registers(float src, uint16_t *hi, uint16_t *lo) {
  uint32_t val;
  memcpy(&val, &src, sizeof(float));
  *hi = (uint16_t)((val >> 16) & 0xFFFF);
  *lo = (uint16_t)(val & 0xFFFF);
}

// Helper to convert 2 x uint16 (Big-Endian IEEE 754) to float
static float registers_to_float(uint16_t hi, uint16_t lo) {
  uint32_t val = ((uint32_t)hi << 16) | lo;
  float result;
  memcpy(&result, &val, sizeof(float));
  return result;
}

// Modbus CRC-16 calculation (Polynomial: 0xA001)
static uint16_t modbus_crc16(const uint8_t *buffer, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < length; i++) {
    crc ^= (uint16_t)buffer[i];
    for (int j = 0; j < 8; j++) {
      if (crc & 0x0001) {
        crc = (crc >> 1) ^ 0xA001;
      } else {
        crc = crc >> 1;
      }
    }
  }
  return crc;
}

esp_err_t modbus_slave_init(void) {
  // Populate default holding register values
  float_to_registers(0.0f, &g_modbus_holding_reg.setpoint_hi,
                     &g_modbus_holding_reg.setpoint_lo);
  g_modbus_holding_reg.command = CMD_NONE;
  float_to_registers(2.0f, &g_modbus_holding_reg.kp_hi,
                     &g_modbus_holding_reg.kp_lo);
  float_to_registers(0.5f, &g_modbus_holding_reg.ki_hi,
                     &g_modbus_holding_reg.ki_lo);
  float_to_registers(0.05f, &g_modbus_holding_reg.kd_hi,
                     &g_modbus_holding_reg.kd_lo);
  g_modbus_holding_reg.burst_read_index = 0;

#ifndef HOST_TEST
  // 1. Suppress ASCII logging: USB/UART carries binary Modbus RTU frames
  esp_log_level_set("*", ESP_LOG_NONE);

  // 2. Install USB Serial JTAG driver for native USB Modbus RTU communication
  usb_serial_jtag_driver_config_t usj_config = {
      .tx_buffer_size = 1024,
      .rx_buffer_size = 1024,
  };
  esp_err_t err = usb_serial_jtag_driver_install(&usj_config);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    return err;
  }
#endif

  return ESP_OK;
}

void modbus_slave_sync_buffers(void) {
  // Process Command Register if set
  uint16_t cmd = g_modbus_holding_reg.command;
  if (cmd != CMD_NONE) {
    g_modbus_holding_reg.command = CMD_NONE; // Reset command register after reading
    if (cmd == CMD_START) {
      shared_data_request_state_change(MACHINE_STATE_MOVING);
    } else if (cmd == CMD_STOP) {
      shared_data_request_state_change(MACHINE_STATE_IDLE);
    } else if (cmd == CMD_RESET) {
      shared_data_request_state_change(MACHINE_STATE_IDLE);
    } else if (cmd == CMD_HOME) {
      shared_data_request_state_change(MACHINE_STATE_HOMING);
    } else if (cmd == CMD_OPEN_LOOP_TEST) {
      shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST);
    } else if (cmd == CMD_SIMULATE_EMERGENCY) {
      gpio_safety_trigger_emergency_software();
    }
  }

  // Process Coil Triggers (Bit 1: Remote Emergency, Bit 2: Remote Start)
  if (g_modbus_coil_reg.coils & (1 << 1)) {
    g_modbus_coil_reg.coils &= ~(1 << 1); // Clear remote emergency trigger coil
    gpio_safety_trigger_emergency_software();
  }
  if (g_modbus_coil_reg.coils & (1 << 2)) {
    g_modbus_coil_reg.coils &= ~(1 << 2); // Clear remote start trigger coil
    shared_data_request_state_change(MACHINE_STATE_MOVING);
  }

  if (shared_data_lock(pdMS_TO_TICKS(10))) {
    // Read setpoint from Modbus holding registers
    g_system_data.position_setpoint = registers_to_float(
        g_modbus_holding_reg.setpoint_hi, g_modbus_holding_reg.setpoint_lo);

    // Synchronize PID gains with Modbus holding registers
    float mb_kp = registers_to_float(g_modbus_holding_reg.kp_hi,
                                     g_modbus_holding_reg.kp_lo);
    float mb_ki = registers_to_float(g_modbus_holding_reg.ki_hi,
                                     g_modbus_holding_reg.ki_lo);
    float mb_kd = registers_to_float(g_modbus_holding_reg.kd_hi,
                                     g_modbus_holding_reg.kd_lo);

    if (!isnan(mb_kp) && !isinf(mb_kp) && mb_kp >= 0.0f)
      g_system_data.kp = mb_kp;
    if (!isnan(mb_ki) && !isinf(mb_ki) && mb_ki >= 0.0f)
      g_system_data.ki = mb_ki;
    if (!isnan(mb_kd) && !isinf(mb_kd) && mb_kd >= 0.0f)
      g_system_data.kd = mb_kd;

    float_to_registers(g_system_data.kp, &g_modbus_holding_reg.kp_hi,
                       &g_modbus_holding_reg.kp_lo);
    float_to_registers(g_system_data.ki, &g_modbus_holding_reg.ki_hi,
                       &g_modbus_holding_reg.ki_lo);
    float_to_registers(g_system_data.kd, &g_modbus_holding_reg.kd_hi,
                       &g_modbus_holding_reg.kd_lo);

    // Populate Modbus Input Registers from telemetry
    float_to_registers(g_system_data.current_position,
                       &g_modbus_input_reg.pos_hi, &g_modbus_input_reg.pos_lo);
    float_to_registers(g_system_data.current_velocity,
                       &g_modbus_input_reg.vel_hi, &g_modbus_input_reg.vel_lo);
    float_to_registers(g_system_data.duty_cycle,
                       &g_modbus_input_reg.duty_hi,
                       &g_modbus_input_reg.duty_lo);
    g_modbus_input_reg.state = (uint16_t)shared_data_get_state();

    // Burst mode telemetry mapping
    g_burst_buffer.read_index = g_modbus_holding_reg.burst_read_index;
    g_modbus_input_reg.burst_status = g_burst_buffer.status;
    g_modbus_input_reg.burst_sample_count =
        g_burst_buffer.sample_count;

    uint16_t r_idx = g_modbus_holding_reg.burst_read_index;
    if (r_idx < g_burst_buffer.sample_count && r_idx < BURST_BUFFER_MAX_SAMPLES) {
      uint32_t t_ms = g_burst_buffer.samples[r_idx].time_ms;
      g_modbus_input_reg.sample_time_hi = (uint16_t)((t_ms >> 16) & 0xFFFF);
      g_modbus_input_reg.sample_time_lo = (uint16_t)(t_ms & 0xFFFF);
      float_to_registers(g_burst_buffer.samples[r_idx].position,
                         &g_modbus_input_reg.sample_pos_hi,
                         &g_modbus_input_reg.sample_pos_lo);
      float_to_registers(g_burst_buffer.samples[r_idx].velocity,
                         &g_modbus_input_reg.sample_vel_hi,
                         &g_modbus_input_reg.sample_vel_lo);
    } else {
      g_modbus_input_reg.sample_time_hi = 0;
      g_modbus_input_reg.sample_time_lo = 0;
      float_to_registers(0.0f, &g_modbus_input_reg.sample_pos_hi,
                         &g_modbus_input_reg.sample_pos_lo);
      float_to_registers(0.0f, &g_modbus_input_reg.sample_vel_hi,
                         &g_modbus_input_reg.sample_vel_lo);
    }

    // Update Discrete Inputs register (Bit 0: E-Stop, Bit 1: Start, Bit 2: Safety Enable, Bit 3: Home Sensor)
    uint8_t discrete_bits = 0;
#ifndef HOST_TEST
    if (gpio_get_level(GPIO_EMERGENCY_PIN) != 0) // Active-HIGH: 1 = Pressed / Active
      discrete_bits |= (1 << 0);
    if (gpio_get_level(GPIO_START_PIN) != 0)     // Active-HIGH: 1 = Pressed
      discrete_bits |= (1 << 1);
    if (gpio_get_level(GPIO_SAFETY_ENABLE_PIN) != 0) // 1 = Hardware enabled
      discrete_bits |= (1 << 2);
    if (gpio_get_level(GPIO_HOME_PIN) != 0)      // Active-HIGH: 1 = Home Sensor Detected
      discrete_bits |= (1 << 3);
#else
    if (g_system_data.button_estop)
      discrete_bits |= (1 << 0);
    if (g_system_data.button_start)
      discrete_bits |= (1 << 1);
    if (g_system_data.safety_enable)
      discrete_bits |= (1 << 2);
#endif
    g_modbus_discrete_reg.discrete_inputs = discrete_bits;

    // Reflect LED status coil (Bit 0)
    g_system_data.led_status = (g_modbus_coil_reg.coils & (1 << 0)) != 0;

    shared_data_unlock();
  }
}

// Process a single Modbus RTU frame and produce response into resp_buf.
// Returns response length, or 0 if frame should be ignored / incomplete.
static size_t modbus_process_frame(const uint8_t *req, size_t req_len,
                                   uint8_t *resp, size_t max_resp) {
  if (req_len < 4)
    return 0; // Too short to even have slave_id + fc + crc

  uint8_t slave_id = req[0];
  if (slave_id != MB_SLAVE_ADDR)
    return 0; // Not addressed to us

  // Check expected request length based on function code
  uint8_t fc = req[1];
  size_t expected_len = 0;
  switch (fc) {
  case 0x01: // Read Coils
  case 0x02: // Read Discrete Inputs
  case 0x03: // Read Holding Registers
  case 0x04: // Read Input Registers
  case 0x05: // Write Single Coil
  case 0x06: // Write Single Register
    expected_len = 8;
    break;
  case 0x10: // Write Multiple Registers
    if (req_len < 7)
      return 0;
    expected_len = 7 + req[6] + 2; // header(7) + byte_count + crc(2)
    break;
  default:
    return 0; // Unsupported function code
  }

  if (req_len < expected_len)
    return 0; // Incomplete frame, wait for more bytes

  // Verify CRC16 over the expected frame
  uint16_t expected_crc = ((uint16_t)req[expected_len - 1] << 8) | req[expected_len - 2];
  uint16_t calc_crc = modbus_crc16(req, (uint16_t)(expected_len - 2));
  if (calc_crc != expected_crc) {
    return 0; // Corrupted CRC, drop frame
  }

  // Ensure buffers are up to date
  modbus_slave_sync_buffers();

  size_t resp_len = 0;

  switch (fc) {
  case 0x01: { // Read Coils
    uint16_t start_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t quantity = ((uint16_t)req[4] << 8) | req[5];
    if (start_addr >= COIL_REG_COUNT || quantity == 0 || (start_addr + quantity) > 16) {
      // Exception: Illegal Data Address
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    uint8_t byte_count = (uint8_t)((quantity + 7) / 8);
    resp[0] = slave_id;
    resp[1] = fc;
    resp[2] = byte_count;
    uint8_t coil_data = (g_modbus_coil_reg.coils >> start_addr) & ((1 << quantity) - 1);
    resp[3] = coil_data;
    resp_len = 4;
    break;
  }

  case 0x02: { // Read Discrete Inputs
    uint16_t start_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t quantity = ((uint16_t)req[4] << 8) | req[5];
    if (start_addr >= DISCRETE_REG_COUNT + 1 || quantity == 0 || (start_addr + quantity) > 16) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    uint8_t byte_count = (uint8_t)((quantity + 7) / 8);
    resp[0] = slave_id;
    resp[1] = fc;
    resp[2] = byte_count;
    uint8_t disc_data = (g_modbus_discrete_reg.discrete_inputs >> start_addr) & ((1 << quantity) - 1);
    resp[3] = disc_data;
    resp_len = 4;
    break;
  }

  case 0x03: { // Read Holding Registers
    uint16_t start_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t quantity = ((uint16_t)req[4] << 8) | req[5];
    size_t total_regs = sizeof(g_modbus_holding_reg) / sizeof(uint16_t);
    if (start_addr + quantity > total_regs || quantity == 0) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    resp[0] = slave_id;
    resp[1] = fc;
    resp[2] = (uint8_t)(quantity * 2);
    const uint16_t *reg_ptr = (const uint16_t *)&g_modbus_holding_reg;
    for (uint16_t i = 0; i < quantity; i++) {
      uint16_t val = reg_ptr[start_addr + i];
      resp[3 + i * 2] = (uint8_t)((val >> 8) & 0xFF);
      resp[4 + i * 2] = (uint8_t)(val & 0xFF);
    }
    resp_len = 3 + quantity * 2;
    break;
  }

  case 0x04: { // Read Input Registers
    uint16_t start_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t quantity = ((uint16_t)req[4] << 8) | req[5];
    size_t total_regs = sizeof(g_modbus_input_reg) / sizeof(uint16_t);
    if (start_addr + quantity > total_regs || quantity == 0) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    resp[0] = slave_id;
    resp[1] = fc;
    resp[2] = (uint8_t)(quantity * 2);
    const uint16_t *reg_ptr = (const uint16_t *)&g_modbus_input_reg;
    for (uint16_t i = 0; i < quantity; i++) {
      uint16_t val = reg_ptr[start_addr + i];
      resp[3 + i * 2] = (uint8_t)((val >> 8) & 0xFF);
      resp[4 + i * 2] = (uint8_t)(val & 0xFF);
    }
    resp_len = 3 + quantity * 2;
    break;
  }

  case 0x05: { // Write Single Coil
    uint16_t coil_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t val = ((uint16_t)req[4] << 8) | req[5];
    if (coil_addr >= COIL_REG_COUNT) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    if (val == 0xFF00) {
      g_modbus_coil_reg.coils |= (1 << coil_addr);
    } else if (val == 0x0000) {
      g_modbus_coil_reg.coils &= ~(1 << coil_addr);
    }
    modbus_slave_sync_buffers();
    memcpy(resp, req, 6);
    resp_len = 6;
    break;
  }

  case 0x06: { // Write Single Register
    uint16_t reg_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t val = ((uint16_t)req[4] << 8) | req[5];
    size_t total_regs = sizeof(g_modbus_holding_reg) / sizeof(uint16_t);
    if (reg_addr >= total_regs) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    uint16_t *reg_ptr = (uint16_t *)&g_modbus_holding_reg;
    reg_ptr[reg_addr] = val;
    modbus_slave_sync_buffers();
    memcpy(resp, req, 6);
    resp_len = 6;
    break;
  }

  case 0x10: { // Write Multiple Registers
    uint16_t start_addr = ((uint16_t)req[2] << 8) | req[3];
    uint16_t quantity = ((uint16_t)req[4] << 8) | req[5];
    uint8_t byte_count = req[6];
    size_t total_regs = sizeof(g_modbus_holding_reg) / sizeof(uint16_t);
    if (start_addr + quantity > total_regs || quantity == 0 || byte_count != quantity * 2) {
      resp[0] = slave_id;
      resp[1] = fc | 0x80;
      resp[2] = 0x02;
      resp_len = 3;
      break;
    }
    uint16_t *reg_ptr = (uint16_t *)&g_modbus_holding_reg;
    for (uint16_t i = 0; i < quantity; i++) {
      uint16_t val = ((uint16_t)req[7 + i * 2] << 8) | req[8 + i * 2];
      reg_ptr[start_addr + i] = val;
    }
    modbus_slave_sync_buffers();
    memcpy(resp, req, 6); // Slave ID + FC + Start Address + Quantity
    resp_len = 6;
    break;
  }

  default:
    return 0;
  }

  // Append CRC-16 (Low byte first, then High byte)
  if (resp_len > 0 && (resp_len + 2) <= max_resp) {
    uint16_t crc = modbus_crc16(resp, (uint16_t)resp_len);
    resp[resp_len++] = (uint8_t)(crc & 0xFF);
    resp[resp_len++] = (uint8_t)((crc >> 8) & 0xFF);
    return resp_len;
  }

  return 0;
}

#ifndef HOST_TEST
static void modbus_slave_task(void *pvParameters) {
  (void)pvParameters;

  uint8_t rx_buf[256];
  uint8_t tx_buf[256];
  size_t rx_len = 0;

  while (1) {
    modbus_slave_sync_buffers();

    int n = usb_serial_jtag_read_bytes(rx_buf + rx_len, sizeof(rx_buf) - rx_len, pdMS_TO_TICKS(10));
    if (n > 0) {
      rx_len += (size_t)n;
      size_t resp_len = modbus_process_frame(rx_buf, rx_len, tx_buf, sizeof(tx_buf));
      if (resp_len > 0) {
        usb_serial_jtag_write_bytes(tx_buf, resp_len, pdMS_TO_TICKS(100));
        rx_len = 0;
      } else if (rx_len >= sizeof(rx_buf)) {
        rx_len = 0; // Buffer full without matching frame, flush
      }
    } else {
      // Read timeout: if bytes were pending, try processing or flush if stale
      if (rx_len > 0) {
        size_t resp_len = modbus_process_frame(rx_buf, rx_len, tx_buf, sizeof(tx_buf));
        if (resp_len > 0) {
          usb_serial_jtag_write_bytes(tx_buf, resp_len, pdMS_TO_TICKS(100));
        }
        rx_len = 0;
      }
    }
  }
}
#endif

void modbus_slave_start_task(void) {
#ifndef HOST_TEST
  xTaskCreatePinnedToCore(modbus_slave_task, "ModbusSlaveTask", 4096, NULL, 4,
                          NULL,
                          0 // Core 0
  );
#endif
}
