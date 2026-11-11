#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização do Supervisório (SCADA) - Guia Linear
# ==============================================================================

set -e

# Define o diretório raiz do projeto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configura o PYTHONPATH para enxergar o pacote 'tools'
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Detecta o ambiente virtual Python disponível
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/tests/.venv/bin/python" ]; then
    PYTHON_EXEC="$SCRIPT_DIR/tests/.venv/bin/python"
else
    PYTHON_EXEC="$(command -v python3 || command -v python)"
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "❌ Erro: Interpretador Python não encontrado no sistema." >&2
    exit 1
fi

# Limpa variáveis de ambiente do Snap (ex: terminais integrados do VS Code Snap) que conflitam com GTK/Qt do host
if [ -n "$SNAP" ] || [ -n "$SNAP_NAME" ] || [[ "$GTK_PATH" == *"/snap/"* ]] || [[ "$LOCPATH" == *"/snap/"* ]]; then
    unset LOCPATH
    unset GTK_PATH
    unset GTK_EXE_PREFIX
    unset GTK_IM_MODULE_FILE
fi

# Corrige XAUTHORITY desatualizado em sessões GNOME/Wayland (quando o mutter recria o arquivo de autorização)
if [ -z "$XAUTHORITY" ] || [ ! -f "$XAUTHORITY" ]; then
    MUTTER_AUTH="$(ls -t /run/user/"$(id -u)"/.mutter-Xwaylandauth.* 2>/dev/null | head -n 1 || true)"
    if [ -n "$MUTTER_AUTH" ] && [ -f "$MUTTER_AUTH" ]; then
        export XAUTHORITY="$MUTTER_AUTH"
    elif [ -f "$HOME/.Xauthority" ]; then
        export XAUTHORITY="$HOME/.Xauthority"
    fi
fi

# Configura suporte para Wayland/X11 no Qt
if [ -z "$QT_QPA_PLATFORM" ] && [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi

# ==============================================================================
# Configuração de IP na Interface de Rede (Wi-Fi / Ethernet) para falar com o ESP32
# ==============================================================================
TARGET_IP="192.168.1.50/24"
ESP_IP="192.168.1.100"

echo "🌐 Verificando IP estático na faixa 192.168.1.x no PC (alvo ESP32: $ESP_IP)..."

# 1. Detecta a interface Wi-Fi
WIFI_IFACE=$(nmcli -t -f DEVICE,TYPE device status 2>/dev/null | grep ":wifi" | cut -d: -f1 | head -n 1 || true)
if [ -z "$WIFI_IFACE" ]; then
    WIFI_IFACE=$(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | grep -E '^(wl|wlan)' | head -n 1 || true)
fi

# 2. Se houver interface Wi-Fi, garante que ela possui um IP na faixa 192.168.1.x
if [ -n "$WIFI_IFACE" ]; then
    if ip -4 addr show dev "$WIFI_IFACE" 2>/dev/null | grep -q "192.168.1\."; then
        CURRENT_IP=$(ip -4 addr show dev "$WIFI_IFACE" | grep "192.168.1\." | awk '{print $2}')
        echo "✅ Interface Wi-Fi ($WIFI_IFACE) já possui IP na faixa correta: $CURRENT_IP"
    else
        echo "⚙️ Configurando IP estático $TARGET_IP na interface Wi-Fi ($WIFI_IFACE)..."
        # Tenta via NetworkManager na conexão ativa (não requer sudo se gerenciado pelo usuário)
        ACTIVE_CON=$(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null | grep ":$WIFI_IFACE" | cut -d: -f1 | head -n 1 || true)
        if [ -n "$ACTIVE_CON" ]; then
            nmcli connection modify "$ACTIVE_CON" +ipv4.addresses "$TARGET_IP" 2>/dev/null || true
        fi

        # Adiciona diretamente o alias de IP na interface se ainda não estiver presente
        if ! ip -4 addr show dev "$WIFI_IFACE" 2>/dev/null | grep -q "192.168.1\."; then
            if [ "$(id -u)" -eq 0 ]; then
                ip addr add "$TARGET_IP" dev "$WIFI_IFACE" 2>/dev/null || true
            else
                sudo ip addr add "$TARGET_IP" dev "$WIFI_IFACE" 2>/dev/null || true
            fi
        fi

        if ip -4 addr show dev "$WIFI_IFACE" 2>/dev/null | grep -q "192.168.1\."; then
            echo "✅ IP $TARGET_IP atribuído com sucesso à interface Wi-Fi $WIFI_IFACE!"
        else
            echo "⚠️ Não foi possível adicionar $TARGET_IP automaticamente em $WIFI_IFACE."
            echo "   Para aplicar manualmente, execute: sudo ip addr add $TARGET_IP dev $WIFI_IFACE"
        fi
    fi
fi

# 3. Verifica também interface Ethernet caso esteja plugado via cabo
ETH_IFACE=$(nmcli -t -f DEVICE,TYPE device status 2>/dev/null | grep ":ethernet" | grep -v "veth\|docker\|br-" | cut -d: -f1 | head -n 1 || true)
if [ -n "$ETH_IFACE" ] && [ -d "/sys/class/net/$ETH_IFACE" ]; then
    if ! ip -4 addr show dev "$ETH_IFACE" 2>/dev/null | grep -q "192.168.1\."; then
        if [ "$(id -u)" -eq 0 ]; then
            ip addr add "$TARGET_IP" dev "$ETH_IFACE" 2>/dev/null || true
        else
            sudo ip addr add "$TARGET_IP" dev "$ETH_IFACE" 2>/dev/null || true
        fi
    fi
fi

echo "🚀 Iniciando Supervisório da Guia Linear..."
echo "🐍 Python: $PYTHON_EXEC"
echo "📂 Diretório: $SCRIPT_DIR"

# Executa o ponto de entrada do supervisório
exec "$PYTHON_EXEC" -m tools.supervisory.main "$@"
