#!/usr/bin/env bash
# ============================================================
# BluaDiagnostics Sprint 2 — Setup local
# ============================================================
# Uso: bash scripts/setup_local.sh
#
# Faz:
# 1. Verifica Python 3.11+
# 2. Cria .venv se não existir
# 3. Instala dependências
# 4. Copia .env.example -> .env (se .env não existir)
# 5. Lembra de copiar a KB
# ============================================================

set -e  # falha rápido

echo "🩺 BluaDiagnostics Sprint 2 — Setup"
echo "===================================="

# 1. Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale Python 3.11+ primeiro."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PY_VERSION detectado"

# 2. Venv
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual em .venv/..."
    python3 -m venv .venv
fi

# 3. Ativar e instalar
echo "📥 Instalando dependências..."
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet

# 4. .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📋 .env criado a partir do template"
    echo "   ⚠️  Edite .env e cole sua chave Groq real ANTES de rodar o sistema"
else
    echo "✅ .env já existe"
fi

# 5. KB
KB_DIR="data/knowledge_base"
KB_COUNT=$(find "$KB_DIR" -name "kb*.md" 2>/dev/null | wc -l)
if [ "$KB_COUNT" -lt 5 ]; then
    echo ""
    echo "⚠️  Knowledge Base incompleta ($KB_COUNT/5 arquivos)"
    echo "   Copie os 5 .md da Sprint 1 para $KB_DIR/"
    echo "   Veja $KB_DIR/README.md para instruções"
else
    echo "✅ KB completa ($KB_COUNT/5 arquivos)"
fi

echo ""
echo "🎉 Setup completo!"
echo ""
echo "Próximos passos:"
echo "  1. Editar .env com sua chave Groq"
echo "  2. Garantir KB em $KB_DIR/"
echo "  3. Rodar: source .venv/bin/activate"
echo "  4. Rodar: blua-ingest    (popula vector store)"
echo "  5. Rodar: streamlit run app/streamlit_app.py"
