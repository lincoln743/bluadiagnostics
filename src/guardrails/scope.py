"""
Validador de Escopo — versão MÍNIMA do Dia 3.

Rejeita perguntas claramente FORA do domínio Care Plus (clima, investimentos,
política, etc). No Dia 5 expandimos com LLM-classifier para casos ambíguos.

Princípio: ASSUMIR ESCOPO POSITIVO POR DEFAULT.
Em saúde, na dúvida, atender. O usuário escreveu na plataforma Blua — alta
probabilidade de ser dúvida clínica/Care Plus. Só rejeitamos quando há
sinal CLARO de off-topic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Padrões que indicam OFF-TOPIC claro (não-clínico, não-Care Plus)
OFF_TOPIC_PATTERNS = [
    # Finanças / investimentos
    r"\b(investir|investimento|ação|ações|bolsa|bitcoin|cripto|criptomoeda)\b",
    r"\b(rentabilidade|cdb|tesouro direto|imposto de renda)\b",

    # Tecnologia / código
    r"\b(programar|código|python|javascript|html|github)\b",
    r"\b(api|sql|database|servidor)\b",

    # Esportes / entretenimento
    r"\b(time de futebol|copa do mundo|brasileirão|libertadores)\b",
    r"\b(filme|série|netflix|spotify|música|jogo de videogame)\b",

    # Política / religião
    r"\b(eleição|presidente|governador|deputado|senador|partido político)\b",

    # Receitas culinárias
    r"\bcomo (fazer|preparar) (bolo|massa|pão|lasanha)\b",
    r"\breceita de\b(?! medicamento)",  # "receita de medicamento" é OK

    # Clima
    r"\b(previsão do tempo|vai chover|temperatura amanhã)\b",
]

# Padrões que indicam CLARAMENTE on-topic (clínico/Care Plus)
ON_TOPIC_HINTS = [
    r"\b(dor|sintoma|sintomas|febre|tosse|cansaço|náusea|vômito|tontura)\b",
    r"\b(remédio|medicamento|medicação|comprimido|cápsula|posologia|bula)\b",
    r"\b(consulta|teleconsulta|médico|doutor|doutora|enfermeira)\b",
    r"\b(care plus|blua|plano de saúde|beneficiário|carteirinha)\b",
    r"\b(exame|laboratório|raio-x|ultrassom|tomografia|ressonância)\b",
    r"\b(diagnóstico|tratamento|prescrição|receita médica)\b",
    r"\bsaúde\b",
    r"\bpressão (alta|baixa|arterial)\b",
    r"\b(diabetes|hipertensão|colesterol|asma)\b",
]


@dataclass
class ScopeResult:
    """Resultado da validação de escopo."""
    no_escopo: bool                     # True = aceitar, False = rejeitar
    motivo: str = ""                    # razão da decisão
    confianca: str = "alta"             # "alta" | "media" | "baixa"


_OFF_RX = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in OFF_TOPIC_PATTERNS]
_ON_RX = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in ON_TOPIC_HINTS]


def validar_escopo(mensagem: str) -> ScopeResult:
    """
    Decide se a mensagem está no escopo Care Plus.

    Estratégia:
        1. Se tem dica forte de on-topic clínico → aceita (mesmo se também
           tem termo off-topic — pode ser pergunta clínica que menciona algo).
        2. Se tem dica forte de off-topic E nenhuma on-topic → rejeita.
        3. Caso ambíguo (nem on nem off) → aceita por default (princípio
           ASSUMIR ESCOPO POSITIVO).
    """
    if not mensagem or not mensagem.strip():
        return ScopeResult(no_escopo=True, motivo="mensagem vazia, sem decisão", confianca="baixa")

    on_match = any(rx.search(mensagem) for rx in _ON_RX)
    off_match = next((rx.search(mensagem) for rx in _OFF_RX if rx.search(mensagem)), None)

    # 1. On-topic explícito vence
    if on_match:
        return ScopeResult(
            no_escopo=True,
            motivo="mensagem contém termos clínicos/Care Plus",
            confianca="alta",
        )

    # 2. Off-topic explícito + sem on-topic → rejeita
    if off_match:
        return ScopeResult(
            no_escopo=False,
            motivo=f"mensagem aparenta ser off-topic: '{off_match.group(0)}'",
            confianca="alta",
        )

    # 3. Ambíguo → aceita por default
    return ScopeResult(
        no_escopo=True,
        motivo="sem sinal claro de off-topic — aceitando por default",
        confianca="baixa",
    )


# ============================================================
# TODO Dia 5: LLM-classifier para casos ambíguos
# ============================================================
# Quando confianca == "baixa", chamar LLM para decidir.
