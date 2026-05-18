#!/usr/bin/env bash
# Atalho para iniciar o app Streamlit do BluaDiagnostics.
#
# Uso:
#   bash scripts/launch_ui.sh           # roda na porta 8501 (default)
#   bash scripts/launch_ui.sh 8888      # roda em porta customizada

set -e
cd "$(dirname "$0")/.."

PORTA="${1:-8501}"

# Garante que dependências de UI estão instaladas
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Instalando Streamlit..."
    pip install streamlit --quiet
fi

# Garante diretório de logs
mkdir -p logs/traces

echo "🩺 Lançando BluaDiagnostics UI em http://localhost:$PORTA"
echo "   Logs de trace em: logs/traces/"
echo ""
echo "   Para parar: Ctrl+C"
echo ""

streamlit run src/ui/app.py \
    --server.port="$PORTA" \
    --server.address=localhost \
    --browser.gatherUsageStats=false
