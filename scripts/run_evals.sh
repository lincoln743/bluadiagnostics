#!/usr/bin/env bash
# Atalho para rodar o eval suite do BluaDiagnostics.
#
# Uso:
#   bash scripts/run_evals.sh              # roda ambos (Sprint 1 + Sprint 2)
#   bash scripts/run_evals.sh --sprint2    # só Sprint 2 (mais rápido)
#   bash scripts/run_evals.sh --sprint1    # só Sprint 1 (LLM-as-judge)
#   bash scripts/run_evals.sh --rapido     # sem pausa entre casos
#
# AVISO: consome tokens Groq.
# Sprint 2 puro: ~8 mil tokens (~2-3 min com rate limit)
# Sprint 1 + 2: ~25 mil tokens (~6-8 min com rate limit)

set -e
cd "$(dirname "$0")/.."

echo "📊 BluaDiagnostics — Eval Runner"
echo ""

# Garante diretório de resultados
mkdir -p evals/results

python -m evals.runner "$@"
