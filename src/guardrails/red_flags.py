"""
Detector de Red Flags clínicas.

Implementação em DOIS níveis:
1. Rule-based (rápido, determinístico): regex sobre lista da kb05_red_flags.md
2. LLM-based (preciso, contextual): classifier semântico para casos ambíguos

Categorias de red flag (vindas de kb05_red_flags.md da Sprint 1):
- cardiovascular: dor torácica + irradiação, suor frio, falta de ar súbita
- neurológica: AVC (FAST), perda de consciência, convulsão, cefaleia súbita intensa
- respiratória: dispneia grave, cianose, estridor
- abdominal: dor súbita intensa, sangramento, abdome em tábua
- mental: ideação suicida, autoagressão, surto psicótico
- materno-infantil: sangramento gestacional, redução de movimentos fetais
- pediátrica: febre + petéquias, letargia em <2 anos

Output: RedFlagResult{detectada, categoria, frase_gatilho, severidade}

Implementação prevista (Dia 5):
- Função detectar(texto: str) -> RedFlagResult
- Listas de keywords por categoria
- Fallback LLM (modelo 8B, prompt curto) se rule-based não decide
"""
from __future__ import annotations

# TODO Sprint 2 — Dia 5
# Implementar detectar() reusando kb05_red_flags.md da Sprint 1
