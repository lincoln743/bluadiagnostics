"""
Runner de evals — executa a suite de testes sobre o sistema completo.

Reusa sprint1_eval_set.json (12 casos) e adiciona ~8 novos casos cobrindo
o que é específico da Sprint 2:
- RAG retrieval correto (3 casos)
- Roteamento multi-agente (3 casos)
- Trajetória esperada (2 casos)

Total: ~20 casos.

Output: evals/sprint2_results.json com formato definido no briefing:
{
  "metadata": {data, modelo, versao_prompt, ...},
  "casos": [
    {
      "id": "...",
      "categoria": "happy_path|red_flag|jailbreak|out_of_scope|rag|routing",
      "input": "...",
      "expected": {...},
      "actual": {
        "resposta": "...",
        "trajetoria_agentes": ["supervisor", "triagem", ...],
        "tools_chamadas": [{nome, args, result}],
        "docs_recuperados": [{source, score, text_snippet}],
        "tempo_ms": 1234,
        "tokens": {input, output, total}
      },
      "avaliacao": {
        "score": 0.85,
        "qualitativa": "adequada|parcial|inadequada",
        "criterios": {acuracia: bool, tom: bool, escalada: bool, ...},
        "comentario": "..."
      }
    }
  ],
  "metricas_agregadas": {
    "acuracia_por_categoria": {...},
    "taxa_escalada_correta": 0.95,
    "tempo_medio_ms": 1850,
    "custo_estimado_usd_por_conversa": 0.003
  }
}

Implementação prevista (Dia 10):
- Função run_evals(eval_set_path, output_path) -> None
- Avaliação automática (rule-based) + LLM-as-judge para qualitativa
- Geração de gráficos matplotlib em docs/img/ para o relatório
"""
from __future__ import annotations


def main() -> None:
    """Entrypoint CLI: blua-eval"""
    raise NotImplementedError("Implementar Dia 10 da Sprint 2")


if __name__ == "__main__":
    main()
