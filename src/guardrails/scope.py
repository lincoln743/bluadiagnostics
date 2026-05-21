"""
Validador de Escopo — v1.3 (Dia 10 fix).

CHANGELOG v1.2 → v1.3:
- Adicionados termos clínicos comuns que estavam faltando:
  * cansaço, fadiga, exaustão, esgotamento (descoberto via eval wearable-01)
  * indisposição, mal-estar, sem energia
  * insônia, dormindo mal, sono ruim
  * ansiedade, estresse, preocupação (sintomas mentais leves não-críticos)
- Sem alterações no LLM fallback nem em padrões off-topic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


# Padrões OFF-TOPIC claros (sem mudança)
OFF_TOPIC_PATTERNS = [
    r"\b(investir|investimento|ação|ações|bolsa|bitcoin|cripto|criptomoeda)\b",
    r"\b(rentabilidade|cdb|tesouro direto|imposto de renda)\b",
    r"\b(programar|código fonte|python|javascript|html|github)\b",
    r"\b(api rest|sql|database|servidor)\b",
    r"\b(time de futebol|copa do mundo|brasileirão|libertadores)\b",
    r"\b(filme|série|netflix|spotify|videogame)\b",
    r"\b(eleição|presidente do brasil|governador|deputado|senador|partido político)\b",
    r"\bcomo\s+(faço|fazer|preparo|preparar|cozinhar)\s+(uma?\s+)?(bolo|massa|pão|lasanha|risoto|feijoada|sopa|comida)\b",
    r"\breceita de (bolo|massa|pão|lasanha|risoto|comida)\b",
    r"\b(previsão do tempo|vai chover|temperatura amanhã)\b",
]

# Padrões ON-TOPIC — V1.3 expandido com sintomas comuns que faltavam
ON_TOPIC_HINTS = [
    r"\b(dor|sintoma|sintomas|febre|tosse|n[aá]usea|vômito|tontura)\b",
    # V1.3: cansaço/fadiga/etc — sintomas constitucionais comuns
    r"\b(cansaço|cansad[oa]|fadiga|exaust[oa]|esgotad[oa]|sem energia)\b",
    r"\b(indisposi[çc][aã]o|mal-?estar|prostra[çc][aã]o)\b",
    r"\b(insônia|insone|dormindo mal|sem dormir|sono ruim|n[aã]o consigo dormir)\b",
    # V1.3: sintomas mentais leves
    r"\b(ansiedade|ansioso|estresse|estressad[oa]|preocupa[çc][aã]o|nervos[oa])\b",
    r"\b(triste|tristeza|desânimo|sem ânimo)\b",
    # Medicação / consulta / saúde plano (sem mudança)
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
    # V1.3: wearables e métricas de saúde
    r"\b(passos|caloria|batimentos|pressão arterial|spo2|saturação)\b",
    r"\b(apple watch|smartwatch|wearable|fitbit)\b",
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


# LLM-classifier (sem mudanças)
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
    from src.providers.llm_provider import get_provider

    if not mensagem or not mensagem.strip():
        return ScopeResult(no_escopo=True, motivo="vazio", confianca="alta", fonte_deteccao="llm")

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
        return ScopeResult(no_escopo=True, motivo="LLM JSON inválido", confianca="baixa", fonte_deteccao="llm")
    except Exception:
        return ScopeResult(no_escopo=True, motivo="LLM erro", confianca="baixa", fonte_deteccao="llm")


def validar_hibrido(mensagem: str, usar_llm_fallback: bool = True) -> ScopeResult:
    rb = validar_escopo(mensagem)
    if rb.confianca == "alta" or not usar_llm_fallback:
        return rb
    return validar_via_llm(mensagem)
