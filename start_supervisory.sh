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

echo "🚀 Iniciando Supervisório da Guia Linear..."
echo "🐍 Python: $PYTHON_EXEC"
echo "📂 Diretório: $SCRIPT_DIR"

# Executa o ponto de entrada do supervisório
exec "$PYTHON_EXEC" -m tools.supervisory.main "$@"
