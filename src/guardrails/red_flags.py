"""
Detector de Red Flags clínicas — versão MÍNIMA do Dia 3.

Esta versão é RULE-BASED apenas (regex sobre keywords da kb05_red_flags.md).
No Dia 5 vamos adicionar um LLM-classifier como fallback para casos ambíguos
(detecção semântica em vez de match literal).

Por que rule-based primeiro?
- Determinístico (mesma entrada → mesma saída — bom para testes)
- Zero latência (ms vs ~500ms do LLM)
- Zero custo de tokens
- Falsos NEGATIVOS são o risco real aqui — mitigados pelo LLM fallback no Dia 5

Princípio de design: PREFERIR FALSO POSITIVO a FALSO NEGATIVO.
Em saúde, escalar uma dor de cabeça leve por engano é melhor que perder um
AVC. O custo de "escalar a mais" é uma orientação extra para o paciente;
o custo de "escalar a menos" pode ser uma vida.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ============================================================
# Padrões por categoria de red flag (extraídos de kb05_red_flags.md)
# ============================================================
# Cada padrão é compilado com IGNORECASE.
# Padrões usam \b (word boundary) onde fizer sentido, e variações comuns.

RED_FLAG_PATTERNS: dict[str, list[str]] = {
    # --- Cardiovascular ---
    "cardiovascular": [
        r"\bdor (no |de )?peito\b.*\b(braço|costas|mandíbula|queixo)\b",
        r"\bdor (no |de )?peito\b.*\b(suor|sudorese|frio)\b",
        r"\bdor torácica\b",
        r"\baperto (no |de )?peito\b",
        r"\binfarto\b",
        r"\bpalpitação\b.*\b(tontura|síncope|desmai)",
        r"\barritmia\b.*\b(sintom|tontura|dispneia)",
    ],
    # --- Neurológica ---
    "neurologica": [
        r"\b(avc|derrame|acidente vascular)\b",
        r"\bperdi (a )?(fala|força|movimento)\b",
        r"\bnão consigo (falar|mexer|levantar)\b",
        r"\bboca (torta|caída)\b",
        r"\brosto (caído|caindo)\b",
        r"\b(perda|perdi).*(consci[eê]ncia|sentid)",
        r"\bdesmaiei\b",
        r"\bconvuls[aã]o\b",
        r"\b(cefaleia|dor de cabeça).*(súbita|pior|nunca senti|trovoada)",
        r"\bpior dor (da|de minha) vida\b",
    ],
    # --- Respiratória ---
    "respiratoria": [
        r"\bnão (consigo|estou conseguindo) respirar\b",
        r"\bfalta de ar\b.*\b(súbita|grave|intensa|piorando)",
        r"\bdispneia\b.*\b(súbita|grave|intensa)",
        r"\b(roxo|azul|cianos)",  # cianose
        r"\bsufocando\b",
    ],
    # --- Anafilaxia / alergia grave ---
    "anafilaxia": [
        r"\b(inchaço|incha)\b.*\b(rosto|lábio|língua|garganta)\b",
        r"\banafilaxia\b",
        r"\burticária\b.*\b(falta de ar|tontura|dispneia)",
        r"\bgarganta (fechando|inchando)\b",
    ],
    # --- Abdominal grave ---
    "abdominal": [
        r"\bdor abdominal\b.*\b(intensa|súbita|insuportável)",
        r"\babdome (em tábua|rígido|duro)\b",
        r"\bsangrando\b.*\b(muito|abundantemente|sem parar)",
        r"\b(hematêmese|vomitando sangue)\b",
    ],
    # --- Mental / autoextermínio ---
    "mental_grave": [
        r"\b(suicídio|suicidar|me matar|tirar minha vida)\b",
        r"\b(não quero|cansei de) viver\b",
        r"\bme machucar\b",
        r"\bideação suicida\b",
        r"\bautoextermínio\b",
    ],
    # --- Gestacional / materno-infantil ---
    "gestacional": [
        r"\bgestante\b.*\b(sangramento|sangrando|cefaleia intensa|visão)",
        r"\bgrávida\b.*\b(sangramento|sangrando|dor forte|convulsão)",
        r"\b(eclâmpsia|pré-eclâmpsia)\b",
        r"\b(bebê|feto) (parou|não está) (mexendo|se movendo)\b",
    ],
    # --- Pediátrica ---
    "pediatrica": [
        r"\b(bebê|criança|filho|filha)\b.*\b(letárgic|mole|não responde)",
        r"\b(bebê|criança)\b.*\b(febre|temperatura)\b.*\b(petéquia|manchas roxas)",
        r"\bconvuls[aã]o (no |da |em )?(bebê|criança|filho|filha)\b",
    ],
}


# Severidade por categoria — algumas são SEMPRE críticas
SEVERIDADE_CATEGORIA: dict[str, Literal["alta", "critica"]] = {
    "cardiovascular": "critica",
    "neurologica": "critica",
    "respiratoria": "critica",
    "anafilaxia": "critica",
    "abdominal": "critica",
    "mental_grave": "critica",
    "gestacional": "critica",
    "pediatrica": "critica",
}


@dataclass
class RedFlagResult:
    """Resultado da detecção. `detectada=False` é o caminho normal."""
    detectada: bool
    categoria: str | None = None
    frase_gatilho: str = ""
    severidade: Literal["alta", "critica"] = "alta"
    fonte_deteccao: Literal["regra", "llm"] = "regra"
    todas_categorias: list[str] = field(default_factory=list)  # se múltiplas


# Pré-compila regex (executa uma vez no import — performance)
_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    cat: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]
    for cat, patterns in RED_FLAG_PATTERNS.items()
}


def detectar(texto: str) -> RedFlagResult:
    """
    Detecta red flags em uma mensagem do paciente.

    Args:
        texto: mensagem em texto livre (pt-BR)

    Returns:
        RedFlagResult com flag, categoria e frase gatilho.

    Estratégia:
        Itera por categoria; se qualquer padrão der match, marca detectada=True.
        Se múltiplas categorias matcham, retorna a PRIMEIRA na ordem do dict
        (cardiovascular > neurologica > ...) mas guarda todas em
        `todas_categorias` para auditoria.
    """
    if not texto or not texto.strip():
        return RedFlagResult(detectada=False)

    matches: list[tuple[str, str]] = []  # (categoria, trecho_matched)

    for categoria, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            m = pattern.search(texto)
            if m:
                matches.append((categoria, m.group(0)))
                break  # já achou nessa categoria, vai pra próxima

    if not matches:
        return RedFlagResult(detectada=False)

    categoria_principal, trecho = matches[0]
    return RedFlagResult(
        detectada=True,
        categoria=categoria_principal,
        frase_gatilho=trecho,
        severidade=SEVERIDADE_CATEGORIA.get(categoria_principal, "alta"),
        fonte_deteccao="regra",
        todas_categorias=[c for c, _ in matches],
    )


# ============================================================
# TODO Dia 5: adicionar LLM-classifier como fallback
# ============================================================
# def detectar_via_llm(texto: str) -> RedFlagResult:
#     """Classifier semântico para casos que regex não pegou."""
#     ...
#
# def detectar_hibrido(texto: str) -> RedFlagResult:
#     """Tenta regra primeiro; se negativo, tenta LLM."""
#     r = detectar(texto)
#     if r.detectada:
#         return r
#     return detectar_via_llm(texto)
