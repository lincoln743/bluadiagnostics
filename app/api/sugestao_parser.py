"""Parser do bloco <sugestao>...</sugestao> embutido no texto da resposta."""
from __future__ import annotations

import json
import re
from typing import Any

_SUGESTAO_RE = re.compile(r"<sugestao>\s*(.*?)\s*</sugestao>", re.DOTALL | re.IGNORECASE)


def extrair_sugestao(texto_resposta: str) -> tuple[str, dict[str, Any] | None]:
    if not texto_resposta:
        return "", None
    match = _SUGESTAO_RE.search(texto_resposta)
    if not match:
        return texto_resposta.strip(), None
    bloco_json = match.group(1).strip()
    texto_limpo = _SUGESTAO_RE.sub("", texto_resposta).strip()
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo)
    sugestao = _parse_json_seguro(bloco_json)
    if isinstance(sugestao, dict):
        sugestao["requer_revisao_medica"] = True  # HITL inegociável
    return texto_limpo, sugestao


def _parse_json_seguro(bloco: str) -> dict[str, Any] | None:
    if not bloco:
        return None
    candidato = bloco.strip()
    if candidato.startswith("```"):
        candidato = re.sub(r"^```(?:json)?\s*", "", candidato)
        candidato = re.sub(r"\s*```$", "", candidato)
    try:
        parsed = json.loads(candidato)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    sem_virgula = re.sub(r",(\s*[}\]])", r"\1", candidato)
    try:
        parsed = json.loads(sem_virgula)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None
