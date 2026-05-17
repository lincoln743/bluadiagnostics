#!/usr/bin/env bash
# Atalho para rodar suite pytest com cobertura.
#
# Uso:
#   bash scripts/run_tests.sh           # tudo + cobertura terminal + HTML
#   bash scripts/run_tests.sh --quick   # só tests, sem cobertura
#   bash scripts/run_tests.sh --html    # abre HTML no final

set -e

cd "$(dirname "$0")/.."  # raiz do projeto

QUICK=0
ABRIR_HTML=0
for arg in "$@"; do
    [ "$arg" = "--quick" ] && QUICK=1
    [ "$arg" = "--html" ] && ABRIR_HTML=1
done

# Verifica pytest-cov
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo "📦 Instalando pytest-cov..."
    pip install pytest-cov --quiet
fi

if [ $QUICK -eq 1 ]; then
    echo "🧪 Rodando suite pytest (modo rápido, sem cobertura)..."
    pytest tests/
else
    echo "🧪 Rodando suite pytest com cobertura..."
    pytest tests/ \
        --cov=src/tools \
        --cov=src/guardrails \
        --cov=src/agents \
        --cov=src/providers \
        --cov=src/rag \
        --cov-report=term-missing \
        --cov-report=html:.coverage_html

    echo ""
    echo "📊 Relatório HTML em: .coverage_html/index.html"

    if [ $ABRIR_HTML -eq 1 ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open .coverage_html/index.html
        elif command -v open &> /dev/null; then
            open .coverage_html/index.html
        fi
    fi
fi
