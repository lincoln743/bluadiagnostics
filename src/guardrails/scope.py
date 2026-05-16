"""
Validador de Escopo — v1.2 (Dia 5 fix).

CHANGELOG v1.1 → v1.2:
- FIX receita culinária: aceita "como faço/preparo" além de "como fazer/preparar"
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


# Padrões OFF-TOPIC claros
OFF_TOPIC_PATTERNS = [
    # Finanças
    r"\b(investir|investimento|ação|ações|bolsa|bitcoin|cripto|criptomoeda)\b",
    r"\b(rentabilidade|cdb|tesouro direto|imposto de renda)\b",
    # Tecnologia
    r"\b(programar|código fonte|python|javascript|html|github)\b",
    r"\b(api rest|sql|database|servidor)\b",
    # Esportes / entretenimento
    r"\b(time de futebol|copa do mundo|brasileirão|libertadores)\b",
    r"\b(filme|série|netflix|spotify|videogame)\b",
    # Política
    r"\b(eleição|presidente do brasil|governador|deputado|senador|partido político)\b",
    # Receitas culinárias (V1.2 — aceita "faço/preparo" também + "uma lasanha")
    r"\bcomo\s+(faço|fazer|preparo|preparar|cozinhar)\s+(uma?\s+)?(bolo|massa|pão|lasanha|risoto|feijoada|sopa|comida)\b",
    r"\breceita de (bolo|massa|pão|lasanha|risoto|comida)\b",
    # Clima
    r"\b(previsão do tempo|vai chover|temperatura amanhã)\b",
]

# Padrões ON-TOPIC
ON_TOPIC_HINTS = [
    r"\b(dor|sintoma|sintomas|febre|tosse|cansaço|n[aá]usea|vômito|tontura|fadiga)\b",
    r"\b(remédio|medicamento|medicação|comprimido|cápsula|posologia|bula)\b",
    r"\b(consulta|teleconsulta|m[eé]dico|doutor|doutora|enfermeira|enfermeiro)\b",
    r"\b(care plus|blua|plano de saúde|beneficiário|carteirinha)\b",
    r"\b(exame|laboratório|raio-x|ultrassom|tomografia|ressonância)\b",
    r"\b(diagnóstico|tratamento|prescrição|receita médica)\b",
    r"\bsaúde\b",
    r"\bpressão (alta|baixa|arterial)\b",
    r"\b(diabetes|hipertensão|colesterol|asma|alergia)\b",
    r"\b(losartana|metformina|paracetamol|ibuprofeno|dipirona|aas|atorvastatina)\b",
    r"\b(coração|pulmão|estômago|rim|fígado|articulação)\b",
    r"\b(gestante|grávida|gestação)\b",
    r"\b(criança|bebê|infantil)\s+(com|está|tem)",
]


@dataclass
class ScopeResult:
    no_escopo: bool
    motivo: str = ""
    confianca: str = "alta"
    fonte_deteccao: str = "regra"


_OFF_RX = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in OFF_TOPIC_PATTERNS]
_ON_RX = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in ON_TOPIC_HINTS]


def validar_escopo(mensagem: str) -> ScopeResult:
    """Validação rule-based."""
    if not mensagem or not mensagem.strip():
        return ScopeResult(no_escopo=True, motivo="mensagem vazia", confianca="baixa")

    on_match = any(rx.search(mensagem) for rx in _ON_RX)
    off_match = next((rx.search(mensagem) for rx in _OFF_RX if rx.search(mensagem)), None)

    if on_match:
        return ScopeResult(
            no_escopo=True,
            motivo="mensagem contém termos clínicos/Care Plus",
            confianca="alta",
            fonte_deteccao="regra",
        )

    if off_match:
        return ScopeResult(
            no_escopo=False,
            motivo=f"off-topic identificado: '{off_match.group(0)}'",
            confianca="alta",
            fonte_deteccao="regra",
        )

    return ScopeResult(
        no_escopo=True,
        motivo="sem sinal claro de off-topic — aceitando por default",
        confianca="baixa",
        fonte_deteccao="regra",
    )


# ============================================================
# LLM-classifier (v1.1 — sem mudanças)
# ============================================================

LLM_SCOPE_PROMPT = """\
Você é um classificador binário para um chatbot de saúde da operadora Care Plus.

Sua tarefa: decidir se a mensagem do usuário ESTÁ DENTRO do escopo do \
BluaDiagnostics (saúde, bem-estar, sintomas, medicações, agendamento, \
cobertura do plano) ou FORA (clima, finanças, política, entretenimento, etc).

POLÍTICA: na dúvida, ACEITE (no_escopo=true). É melhor responder uma pergunta \
borderline do que rejeitar uma legítima do beneficiário.

Responda APENAS com JSON:
{"no_escopo": true|false, "motivo": "1 frase explicando"}

NÃO adicione texto fora do JSON.
"""


def validar_via_llm(mensagem: str) -> ScopeResult:
    """Validação semântica via LLM para casos ambíguos."""
    from src.providers.llm_provider import get_provider

    if not mensagem or not mensagem.strip():
        return ScopeResult(
            no_escopo=True,
            motivo="vazio — aceitando por default",
            confianca="alta",
            fonte_deteccao="llm",
        )

    try:
        provider = get_provider()
        response = provider.chat_completion(
            messages=[
                {"role": "system", "content": LLM_SCOPE_PROMPT},
                {"role": "user", "content": mensagem},
            ],
            temperature=0.0,
            max_tokens=80,
        )

        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)

        return ScopeResult(
            no_escopo=bool(data.get("no_escopo", True)),
            motivo=str(data.get("motivo", "decisão do LLM"))[:120],
            confianca="alta",
            fonte_deteccao="llm",
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return ScopeResult(
            no_escopo=True,
            motivo="LLM JSON inválido — aceitando por default",
            confianca="baixa",
            fonte_deteccao="llm",
        )
    except Exception:
        return ScopeResult(
            no_escopo=True,
            motivo="LLM erro de chamada — aceitando por default",
            confianca="baixa",
            fonte_deteccao="llm",
        )


def validar_hibrido(mensagem: str, usar_llm_fallback: bool = True) -> ScopeResult:
    """Validador híbrido — função PRINCIPAL para uso pelo supervisor."""
    rb = validar_escopo(mensagem)
    if rb.confianca == "alta" or not usar_llm_fallback:
        return rb
    return validar_via_llm(mensagem)
