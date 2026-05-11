"""
Tool: buscar_conhecimento_clinico

Wrapper do ClinicalRetriever no formato de function calling (OpenAI/Groq schema).

Por que ter o RAG como TOOL (não como retrieval cego em todo turno)?
- O agente decide quando precisa buscar contexto.
- Permite reformulação da query pelo próprio LLM antes da busca.
- Cada chamada é logada na trajetória (state["tools_chamadas"]) — bom para
  evals, observabilidade e o painel da UI Streamlit.

Schema sem `pattern` regex (lição aprendida da Sprint 1: Groq rejeita patterns
em JSON Schema).
"""
from __future__ import annotations

from typing import Any

from src.rag.retriever import get_retriever


# Especificação no formato Anthropic (mais limpo). Conversor para OpenAI/Groq
# está em src/providers/llm_provider.py — mesma estratégia da Sprint 1.
TOOL_SPEC = {
    "name": "buscar_conhecimento_clinico",
    "description": (
        "Busca informações clínicas relevantes na base de conhecimento Care Plus "
        "(protocolo Manchester, bulas resumidas, política de telemedicina, cartilha "
        "do beneficiário, lista de red flags clínicas). Use quando precisar de "
        "informação factual específica para responder ao paciente — NÃO use para "
        "perguntas conversacionais genéricas. Retorna até 4 trechos relevantes "
        "com fonte e score de relevância."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Pergunta ou tópico clínico. Seja específico — em vez de "
                    "'dor', prefira 'dor torácica irradiando para braço esquerdo'. "
                    "Pode reformular a query do paciente para termos médicos mais "
                    "precisos antes de buscar."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "Número de trechos a retornar (1-6, default 4).",
                "minimum": 1,
                "maximum": 6,
            },
            "kb_filter": {
                "type": "string",
                "description": (
                    "Opcional — restringe a busca a uma base específica. Valores: "
                    "'kb01' (protocolo Manchester), 'kb02' (bulas), 'kb03' (política "
                    "telemedicina), 'kb04' (cartilha beneficiário), 'kb05' (red flags). "
                    "Omita para buscar em todas."
                ),
                "enum": ["kb01", "kb02", "kb03", "kb04", "kb05"],
            },
        },
        "required": ["query"],
    },
}


def buscar_conhecimento_clinico(
    query: str,
    top_k: int = 4,
    kb_filter: str | None = None,
) -> dict[str, Any]:
    """
    Implementação da tool. Chamada quando o agente decide via function calling.

    Returns:
        {
          "query": str,
          "total_encontrados": int,
          "chunks": [
            {"text", "source_file", "kb_id", "section", "score"},
            ...
          ]
        }
    """
    # Validação defensiva (LLM às vezes manda top_k = 0 ou string)
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 4
    top_k = max(1, min(6, top_k))

    retriever = get_retriever()
    chunks = retriever.retrieve(query=query, top_k=top_k, kb_filter=kb_filter)

    return {
        "query": query,
        "kb_filter": kb_filter,
        "total_encontrados": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
    }
