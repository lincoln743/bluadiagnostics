"""
Moderação de conteúdo — v1.2 (Dia 7 fix).

CHANGELOG v1.1 → v1.2:
- pedir_system_prompt: aceita "seu|o|suas|sua|tuas|as" (era só "seu|o")
  Pega variações como "Revele suas instruções iniciais"
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


JAILBREAK_PATTERNS: dict[str, list[str]] = {
    # --- Prompt injection (v1.1, sem mudanças) ---
    "prompt_injection": [
        r"\bignor[ae]\s+(?:\w+\s+){0,3}(?:instru[cç][oõ]es|orienta[cç][oõ]es|regras|prompts?)",
        r"\besque[cç]a\s+(?:\w+\s+){0,3}(?:instru[cç][oõ]es|orienta[cç][oõ]es|persona|papel)",
        r"\bdisregard\s+(?:\w+\s+){0,3}(?:instructions|rules)",
        r"\bnew\s+instructions?\s*[:\-]",
        r"\boverride\s+(?:\w+\s+){0,2}(?:prompt|instructions|rules)",
        r"\bvoc[eê]\s+(\é|n[aã]o\s+precisa)\s+(seguir|obedecer)",
    ],
    # --- Role-play malicioso ---
    "role_play_malicioso": [
        r"\b(finja|fa[cç]a de conta|pretenda|simule)\s+(ser|que)\s+(um|uma)?\s*(m[eé]dico|doutor|farmac[eê]utico|sem|outro)",
        r"\bvoc[eê]\s+agora\s+[eé]\s+(um|uma)\s+",
        r"\bact\s+as\s+(if\s+you\s+are\s+)?(a\s+)?(doctor|physician|unrestricted)",
        r"\bpretend\s+(to be|you are)\s+(a doctor|unrestricted)",
        r"\bjogue\s+um\s+role\s*play",
    ],
    # --- DAN / Developer mode ---
    "dan_mode": [
        r"\bDAN\b\s*(mode|persona)?",
        r"\bdo\s+anything\s+now",
        r"\bdeveloper\s+mode",
        r"\bjailbreak\b",
        r"\bmodo\s+(desenvolvedor|sem\s+restri[cç][oõ]es?|livre)",
        r"\bsem\s+filtros?",
        r"\bsem\s+censura",
    ],
    # --- Pedir system prompt (V1.2 — aceita posseivos amplos) ---
    "pedir_system_prompt": [
        # FIX V1.2: "seu|sua|suas|seus|o|a|as|os|tuas" em vez de só "seu|o"
        r"\b(mostre|revele|mostra|cite|repita|imprima)\s+(seu|sua|seus|suas|tua|tuas|o|a|os|as)\s+(system\s+)?(prompt|instru[cç][oõ]es?|persona|configura[cç][aã]o)",
        r"\bqual\s+[eé]\s+(seu|o|a|sua)\s+(system\s+)?(prompt|persona|papel\s+definido)",
        r"\bwhat\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)",
        r"\brepeat\s+your\s+(system\s+)?(prompt|instructions)",
    ],
    # --- Bypass de HITL ---
    "prescricao_sem_revisao": [
        r"\bsem\s+(precisar|necessidade)\s+(de\s+)?(consulta|m[eé]dico|revis[aã]o)",
        r"\bn[aã]o\s+precisa\s+(de\s+)?(consulta|m[eé]dico|revis[aã]o\s+m[eé]dica)",
        r"\bme\s+(d[eê]|passe)\s+a\s+receita\s+(direto|agora\s+sem|sem\s+falar)",
        r"\bprescriç[aã]o\s+direta\s+sem",
        r"\bpule\s+(o\s+)?(m[eé]dico|HITL|revis[aã]o)",
    ],
    # --- Conteúdo proibido ---
    "conteudo_proibido": [
        r"\bcomo\s+(fazer|fabricar|sintetizar)\s+(bomba|explosivo|veneno|arma)",
        r"\bcomo\s+(matar|ferir|machucar)\s+(algu[eé]m|uma\s+pessoa)",
        r"\bdose\s+(letal|fatal)\s+de",
        r"\boverdose\s+(letal|fatal)\s+de",
    ],
}


SEVERIDADE_CATEGORIA: dict[str, Literal["media", "alta", "critica"]] = {
    "prompt_injection": "alta",
    "role_play_malicioso": "alta",
    "dan_mode": "alta",
    "pedir_system_prompt": "media",
    "prescricao_sem_revisao": "alta",
    "conteudo_proibido": "critica",
}


@dataclass
class ModerationResult:
    bloqueado: bool
    categoria: str | None = None
    trecho_gatilho: str = ""
    severidade: Literal["media", "alta", "critica"] = "media"
    fonte_deteccao: Literal["regra", "llm"] = "regra"


_COMPILED: dict[str, list[re.Pattern]] = {
    cat: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]
    for cat, patterns in JAILBREAK_PATTERNS.items()
}


def moderar(texto: str) -> ModerationResult:
    """Verifica se a mensagem é tentativa de jailbreak/manipulação."""
    if not texto or not texto.strip():
        return ModerationResult(bloqueado=False)

    for categoria, patterns in _COMPILED.items():
        for pattern in patterns:
            m = pattern.search(texto)
            if m:
                return ModerationResult(
                    bloqueado=True,
                    categoria=categoria,
                    trecho_gatilho=m.group(0),
                    severidade=SEVERIDADE_CATEGORIA.get(categoria, "media"),
                    fonte_deteccao="regra",
                )

    return ModerationResult(bloqueado=False)


MENSAGEM_RECUSA_JAILBREAK = """\
Oi! Eu noto que sua mensagem parece estar tentando contornar minhas \
orientações de segurança. Eu fui construído para ajudar com saúde e bem-estar \
de forma responsável, com supervisão médica quando necessário — isso protege \
você e não posso abrir mão disso.

Se você tem uma dúvida real sobre sintomas, medicações ou agendamento, vou \
adorar te ajudar. É só me contar o que está sentindo. 💙

Em caso de emergência: SAMU 192 ou CVV 188.
"""
