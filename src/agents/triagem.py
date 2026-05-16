"""
Agente de Triagem — v1.1 (Dia 4b corrigido)

Mudanças v1.0 → v1.1:
- Detector de vazamento de sintaxe de tool calling no texto da resposta
- Se detectado, ele tenta UM retry com aviso explícito; se falhar de novo,
  sanitiza a resposta removendo o vazamento.
- Mantém o tool loop interno (decisão arquitetural confirmada).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from src.graph.state import BluaState, ToolCallRecord, DocRecuperado
from src.prompts.system_prompts import TRIAGEM_PROMPT
from src.providers.llm_provider import get_provider
from src.tools import dispatch_tool, get_tool_specs_for_agent


# Limite de iterações do tool loop
MAX_TOOL_ITERATIONS = 5

# Padrões que indicam vazamento de sintaxe de tool calling em texto
# (Llama 3.1 8B às vezes escapa de chamadas estruturadas)
LEAKED_TOOL_PATTERNS = [
    r"</?function>",                       # </function> ou <function>
    r"\b\w+\s*\{[^}]*\}\s*</function>",   # nome_tool{...}</function>
    r"<tool_call>",
    r"</tool_call>",
    r"^\s*\w+\(\{",                        # nome_tool({ no início
]
_LEAK_RX = re.compile("|".join(LEAKED_TOOL_PATTERNS), re.IGNORECASE | re.MULTILINE)


def _detectar_vazamento(texto: str) -> bool:
    """True se a resposta contém sintaxe de tool calling vazada como texto."""
    if not texto:
        return False
    return bool(_LEAK_RX.search(texto))


def _sanitizar_resposta(texto: str) -> str:
    """
    Remove sintaxe de tool calling vazada e substitui por mensagem de fallback
    sensata. Usado quando retry falha.
    """
    return (
        "Vou te ajudar com isso. Para te dar uma orientação mais precisa, "
        "preciso de mais informações: há quanto tempo está com esse sintoma "
        "e qual a intensidade (de 0 a 10)?"
        "\n\n---\n⚕️ *Informação preliminar. Em emergência, ligue 192 (SAMU).*"
    )


def _formatar_contexto_paciente(state: BluaState) -> str:
    paciente = state.get("paciente", {})
    if not paciente or not paciente.get("paciente_id"):
        return ""

    linhas = ["", "## Contexto do Paciente (já disponível no estado)"]
    linhas.append(f"- ID: {paciente.get('paciente_id', 'N/A')}")
    if nome := paciente.get("nome_apelido"):
        linhas.append(f"- Apelido: {nome}")
    if idade := paciente.get("idade"):
        linhas.append(f"- Idade: {idade} anos")
    if condicoes := paciente.get("condicoes_cronicas"):
        linhas.append(f"- Condições conhecidas: {', '.join(condicoes)}")
    if alergias := paciente.get("alergias"):
        linhas.append(f"- Alergias: {', '.join(alergias)}")
    if meds := paciente.get("medicamentos_em_uso"):
        linhas.append(f"- Medicações em uso: {', '.join(meds)}")
    linhas.append("")
    linhas.append(
        "Use consultar_historico_paciente se precisar de mais detalhes "
        "(exames, última consulta, etc)."
    )
    return "\n".join(linhas)


def _registrar_tool_call(
    nome: str,
    args: dict[str, Any],
    resultado: dict[str, Any],
) -> ToolCallRecord:
    """Cria registro padronizado de chamada de tool — agora cobrindo todos os branches."""
    status = resultado.get("status", "unknown")

    if status == "success":
        # Detecção mais robusta do tipo de tool (ORDEM IMPORTA — RAG primeiro)
        if "chunks" in resultado or "total_encontrados" in resultado:
            resumo = f"ok — {resultado.get('total_encontrados', 0)} chunks recuperados"
        elif "agendamento_id" in resultado:
            resumo = f"ok — agendamento {resultado['agendamento_id']}"
        elif "total_interacoes" in resultado:
            n = resultado["total_interacoes"]
            ci = len(resultado.get("contraindicacoes_alergia", []))
            extra = f" + {ci} contraindicação" if ci > 0 else ""
            resumo = f"ok — {n} interação(ões){extra}"
        elif "dispositivo" in resultado:
            resumo = f"ok — {resultado['dispositivo']}"
        elif "data" in resultado and isinstance(resultado["data"], dict):
            nome_pac = resultado["data"].get("nome_apelido", "")
            resumo = f"ok — {nome_pac}" if nome_pac else "ok"
        else:
            resumo = "ok"
    else:
        resumo = f"{status}: {resultado.get('mensagem', '')[:80]}"

    return ToolCallRecord(
        nome=nome,
        args=args,
        result_resumo=resumo,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _extrair_docs_recuperados(resultado_tool: dict[str, Any]) -> list[DocRecuperado]:
    if "chunks" not in resultado_tool:
        return []
    return [
        DocRecuperado(
            source_file=c["source_file"],
            kb_id=c["kb_id"],
            section=c["section"],
            score=c["score"],
            text_snippet=c["text"][:200],
        )
        for c in resultado_tool["chunks"]
    ]


def triagem_node(state: BluaState) -> dict[str, Any]:
    """Nó de triagem — tool loop interno com detector de vazamento."""
    provider = get_provider()
    tool_specs = get_tool_specs_for_agent("triagem")

    system_content = TRIAGEM_PROMPT + _formatar_contexto_paciente(state)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]
    for msg in state.get("mensagens", []):
        role = msg.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": msg.get("content", "")})

    tools_executadas: list[ToolCallRecord] = []
    docs_recuperados_turno: list[DocRecuperado] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = provider.chat_completion(
            messages=messages,
            tools=tool_specs,
            temperature=0.3,
        )

        # Caso 1: resposta final (sem tool_calls)
        if not response.tool_calls:
            texto = response.text.strip()

            # FIX V1.1: detectar vazamento de tool syntax
            if _detectar_vazamento(texto):
                # Retry UMA vez com aviso explícito ao LLM
                messages.append({"role": "assistant", "content": texto})
                messages.append({
                    "role": "user",
                    "content": (
                        "ATENÇÃO: sua resposta anterior continha sintaxe técnica "
                        "de tool calling como texto (ex: </function>, nome_tool{...}). "
                        "Isso é PROIBIDO. Reescreva sua resposta SEM nenhuma menção "
                        "técnica — apenas texto natural em português para o paciente."
                    ),
                })
                response_retry = provider.chat_completion(
                    messages=messages,
                    tools=None,  # sem tools no retry — força resposta textual
                    temperature=0.2,
                )
                texto = response_retry.text.strip()
                # Se vazou de novo, sanitiza
                if _detectar_vazamento(texto) or not texto:
                    texto = _sanitizar_resposta(texto)

            mensagem_final = texto or (
                "Desculpe, não consegui gerar uma resposta agora. "
                "Pode tentar reformular sua mensagem?"
            )
            nova_mensagem = {"role": "assistant", "content": mensagem_final}

            return {
                "mensagens": [nova_mensagem],
                "agentes_acionados": ["triagem"],
                "tools_chamadas": tools_executadas,
                "docs_recuperados": docs_recuperados_turno,
            }

        # Caso 2: LLM pediu tool calls
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.text or "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in response.tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in response.tool_calls:
            nome = tc["name"]
            args_raw = tc["arguments"]

            try:
                args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args_dict = {}

            resultado = dispatch_tool(nome, args_dict)

            if nome == "buscar_conhecimento_clinico":
                docs_recuperados_turno.extend(_extrair_docs_recuperados(resultado))

            tools_executadas.append(_registrar_tool_call(nome, args_dict, resultado))

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": nome,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

    # Estourou iterações
    return {
        "mensagens": [{
            "role": "assistant",
            "content": (
                "Desculpe, estou tendo dificuldade para processar sua solicitação agora. "
                "Posso te ajudar a agendar uma teleconsulta com um clínico para uma "
                "avaliação completa?"
                "\n\n---\n⚕️ *Informação preliminar. Em emergência, ligue 192 (SAMU).*"
            ),
        }],
        "agentes_acionados": ["triagem"],
        "tools_chamadas": tools_executadas,
        "docs_recuperados": docs_recuperados_turno,
    }
