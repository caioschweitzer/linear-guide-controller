# Encoder PCNT Driver Specification

## Purpose
Specifies the ESP32-S3 hardware PCNT pulse counter driver for quadrature X4 encoder reading, 16-bit hardware overflow accumulation into a 32-bit software integer, GPIO internal pull-up configuration, glitch filtering, and atomic zero reset.

## Requirements

### Requirement: Quadrature X4 Hardware Counting
The system SHALL initialize an ESP32-S3 PCNT unit with two quadrature channels on GPIO 14 (Channel A) and GPIO 15 (Channel B) evaluating both rising and falling edges to yield 1000 accumulated counts per revolution for a 250 PPR encoder.

#### Scenario: Normal quadrature counting
- **WHEN** encoder turns 1 full revolution forward
- **THEN** accumulated count SHALL increase by exactly 1000 counts

#### Scenario: Reverse quadrature counting
- **WHEN** encoder turns 1 full revolution backward
- **THEN** accumulated count SHALL decrease by exactly 1000 counts

### Requirement: GPIO Internal Pull-Up Configuration
The system SHALL configure internal pull-up resistors (`GPIO_PULLUP_ONLY`) on GPIO 14 and GPIO 15 during driver initialization to prevent floating signal states and noise.

#### Scenario: Pin state initialization
- **WHEN** driver `encoder_init()` is called
- **THEN** GPIO 14 and GPIO 15 SHALL be configured with internal Pull-Up enabled

### Requirement: Glitch Filter Noise Suppression
The system SHALL enable the PCNT glitch filter with a maximum glitch width threshold `max_glitch_ns = 1000` (1 microsecond) to reject high-frequency electromagnetic noise.

#### Scenario: Glitch noise rejection
- **WHEN** noise spikes shorter than 1000 ns occur on encoder GPIO lines
- **THEN** PCNT unit SHALL ignore the noise spikes without modifying count value

### Requirement: 16-bit Hardware Overflow Accumulation into 32-bit Integer
The system SHALL configure PCNT watch points at +30000 and -30000 and register an ISR callback to track hardware overflows/underflows into a 32-bit signed software accumulator (`int32_t`).

#### Scenario: Positive 16-bit hardware overflow
- **WHEN** hardware count reaches +30000 limit
- **THEN** ISR callback SHALL increment 32-bit overflow counter and reset hardware count seamlessly without losing position

#### Scenario: Negative 16-bit hardware underflow
- **WHEN** hardware count reaches -30000 limit
- **THEN** ISR callback SHALL decrement 32-bit overflow counter and reset hardware count seamlessly without losing position

### Requirement: Atomic Zero Reset
The system SHALL provide an atomic `encoder_clear_count()` function that clears both the hardware PCNT counter and the 32-bit software overflow accumulator under thread-safe spinlock protection.

#### Scenario: Zero reset invocation
- **WHEN** `encoder_clear_count()` is called with an accumulated count of 150000
- **THEN** total count returned on subsequent reads SHALL be 0
