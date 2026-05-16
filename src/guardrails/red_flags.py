"""
Detector de Red Flags clínicas — v1.1 (Dia 5).

CHANGELOG v1.0 → v1.1:
- Adicionada função detectar_via_llm() para fallback semântico
- Adicionada função detectar_hibrido() — usar essa nos agentes
- Adicionados padrões pediátricos cobrindo "filha/filho de N anos"
  (resolve o miss do caso pediátrico do smoke test do Dia 3)

DESIGN HÍBRIDO:
    detectar_hibrido():
        1. detectar() rule-based → se positivo, retorna imediatamente
        2. Se negativo, detectar_via_llm() → LLM classificador binário
        3. Resultado merged com metadata da fonte

LATÊNCIA:
- Caso 1 (regra positiva): <1ms
- Caso 2 (LLM acionado): ~500-800ms
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal


# ============================================================
# Padrões rule-based (v1.0 + correções pediátricas v1.1)
# ============================================================

RED_FLAG_PATTERNS: dict[str, list[str]] = {
    "cardiovascular": [
        r"\bdor (no |de )?peito\b.*\b(braço|costas|mandíbula|queixo)\b",
        r"\bdor (no |de )?peito\b.*\b(suor|sudorese|frio)\b",
        r"\bdor torácica\b",
        r"\baperto (no |de )?peito\b",
        r"\binfarto\b",
        r"\bpalpitação\b.*\b(tontura|síncope|desmai)",
        r"\barritmia\b.*\b(sintom|tontura|dispneia)",
    ],
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
    "respiratoria": [
        r"\bnão (consigo|estou conseguindo) respirar\b",
        r"\bfalta de ar\b.*\b(súbita|grave|intensa|piorando)",
        r"\bdispneia\b.*\b(súbita|grave|intensa)",
        r"\b(roxo|azul|cianos)",
        r"\bsufocando\b",
    ],
    "anafilaxia": [
        r"\b(inchaço|incha)\b.*\b(rosto|lábio|língua|garganta)\b",
        r"\banafilaxia\b",
        r"\burticária\b.*\b(falta de ar|tontura|dispneia)",
        r"\bgarganta (fechando|inchando)\b",
    ],
    "abdominal": [
        r"\bdor abdominal\b.*\b(intensa|súbita|insuportável)",
        r"\babdome (em tábua|rígido|duro)\b",
        r"\bsangrando\b.*\b(muito|abundantemente|sem parar)",
        r"\b(hematêmese|vomitando sangue)\b",
    ],
    "mental_grave": [
        r"\b(suicídio|suicidar|me matar|tirar minha vida)\b",
        r"\b(não quero|cansei de) viver\b",
        r"\bme machucar\b",
        r"\bideação suicida\b",
        r"\bautoextermínio\b",
    ],
    "gestacional": [
        r"\bgestante\b.*\b(sangramento|sangrando|cefaleia intensa|visão)",
        r"\bgrávida\b.*\b(sangramento|sangrando|dor forte|convulsão)",
        r"\b(eclâmpsia|pré-eclâmpsia)\b",
        r"\b(bebê|feto) (parou|não está) (mexendo|se movendo)\b",
    ],
    # V1.1: expandido para cobrir "filha/filho de X anos/meses"
    "pediatrica": [
        # Termos coletivos
        r"\b(bebê|criança|filho|filha)\b.*\b(letárgic|mole|não responde)",
        r"\b(bebê|criança)\b.*\b(febre|temperatura)\b.*\b(petéquia|manchas roxas)",
        r"\bconvuls[aã]o (no |da |em )?(bebê|criança|filho|filha)\b",
        # FIX V1.1: "filho/filha/bebê de X (anos|meses)" como sujeito
        r"\b(filho|filha|bebê|menino|menina)\s+de\s+\d+\s+(anos?|meses?)\b.*\b(febre|petéquia|manchas roxas|convuls|letárgic|mole|não responde)",
        r"\bminha?\s+(filha|filho|bebê)\b.*\b(petéquia|manchas roxas)",
        r"\bminha?\s+(filha|filho|bebê)\b.*\b(letárgic|não acorda|sem responder)",
    ],
}


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
    detectada: bool
    categoria: str | None = None
    frase_gatilho: str = ""
    severidade: Literal["alta", "critica"] = "alta"
    fonte_deteccao: Literal["regra", "llm"] = "regra"
    todas_categorias: list[str] = field(default_factory=list)


# Pré-compila
_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    cat: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]
    for cat, patterns in RED_FLAG_PATTERNS.items()
}


# ============================================================
# Detector rule-based (v1.0 — preservado)
# ============================================================

def detectar(texto: str) -> RedFlagResult:
    """Detecta red flag via regex. Função pura, determinística, <1ms."""
    if not texto or not texto.strip():
        return RedFlagResult(detectada=False)

    matches: list[tuple[str, str]] = []
    for categoria, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            m = pattern.search(texto)
            if m:
                matches.append((categoria, m.group(0)))
                break

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
# Detector LLM (v1.1 — novo)
# ============================================================

LLM_CLASSIFIER_PROMPT = """\
Você é um classificador binário de sintomas clínicos para um sistema de \
triagem de saúde. Sua única tarefa: dada a mensagem de um paciente, decidir \
se ela contém SINAL DE ALERTA CLÍNICO que exija atendimento médico imediato \
(SAMU 192 ou CVV 188).

CATEGORIAS QUE EXIGEM ESCALADA IMEDIATA:
- cardiovascular: dor torácica com irradiação, suor frio, infarto suspeito, arritmia sintomática
- neurologica: AVC (perda de força, fala, consciência), convulsão, cefaleia súbita intensíssima
- respiratoria: falta de ar súbita grave, cianose, sufocação
- anafilaxia: inchaço de língua/garganta, urticária com falta de ar
- abdominal: abdome em tábua, sangramento intenso, hematêmese
- mental_grave: ideação suicida, autoagressão, intenção de morte
- gestacional: sangramento gestacional, eclâmpsia, redução de movimentos fetais
- pediatrica: criança com febre + petéquias, letargia, convulsão em <2a

NÃO são red flags (deixe passar):
- Sintomas leves a moderados sem irradiação ou gravidade
- Sintomas crônicos sem piora aguda
- Dúvidas sobre medicação ou agendamento

Responda APENAS com JSON:
{"detectada": true|false, "categoria": "<uma das acima>" ou null, "justificativa": "1 frase"}

NÃO adicione texto fora do JSON.
"""


def detectar_via_llm(texto: str) -> RedFlagResult:
    """
    Detector semântico via LLM. Usado como fallback do rule-based.

    Returns:
        RedFlagResult com fonte_deteccao="llm".
        Em caso de erro de parsing/API, retorna detectada=False (fail-safe).
    """
    # Import local para evitar import circular (red_flags é importado em supervisor)
    from src.providers.llm_provider import get_provider

    if not texto or not texto.strip():
        return RedFlagResult(detectada=False)

    try:
        provider = get_provider()
        response = provider.chat_completion(
            messages=[
                {"role": "system", "content": LLM_CLASSIFIER_PROMPT},
                {"role": "user", "content": texto},
            ],
            temperature=0.0,  # determinístico
            max_tokens=120,
        )

        text = response.text.strip()
        # Remove markdown fences se houver
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)
        detectada = bool(data.get("detectada", False))
        categoria = data.get("categoria")
        justificativa = data.get("justificativa", "")

        if not detectada or not categoria:
            return RedFlagResult(detectada=False)

        # Valida categoria
        if categoria not in SEVERIDADE_CATEGORIA:
            return RedFlagResult(detectada=False)

        return RedFlagResult(
            detectada=True,
            categoria=categoria,
            frase_gatilho=justificativa[:120],
            severidade=SEVERIDADE_CATEGORIA[categoria],
            fonte_deteccao="llm",
            todas_categorias=[categoria],
        )

    except (json.JSONDecodeError, KeyError, ValueError):
        # Fail-safe: em caso de erro, não detecta (regra já tentou e falhou também)
        return RedFlagResult(detectada=False)
    except Exception:
        # Catch-all defensivo (API down, rate limit esgotado, etc)
        return RedFlagResult(detectada=False)


# ============================================================
# Detector híbrido (v1.1 — função principal a ser usada nos agentes)
# ============================================================

def detectar_hibrido(texto: str, usar_llm_fallback: bool = True) -> RedFlagResult:
    """
    Detector híbrido. Esta é a função PRINCIPAL a ser usada pelo supervisor.

    Estratégia:
        1. Tenta detectar() rule-based — se positivo, retorna em <1ms.
        2. Se rule-based negativo E usar_llm_fallback=True:
           Tenta detectar_via_llm() — ~500-800ms.
        3. Resultado final tem fonte_deteccao="regra" ou "llm".

    Args:
        texto: mensagem do paciente
        usar_llm_fallback: se False, equivale ao detectar() puro (útil em testes)

    Returns:
        RedFlagResult com metadados de fonte.
    """
    rb = detectar(texto)
    if rb.detectada or not usar_llm_fallback:
        return rb
    return detectar_via_llm(texto)
