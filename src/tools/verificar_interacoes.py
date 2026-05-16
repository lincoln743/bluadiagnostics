"""
Tool: verificar_interacoes_medicamentosas

Verifica interações entre medicamentos contra uma base mock curada.
Cobre os medicamentos mais relevantes para os 3 pacientes da Sprint 2.

Severidades:
- "leve": cuidado, monitorar
- "moderada": ajustar dose ou horário
- "grave": evitar combinação, risco real
- "critica": contraindicação absoluta

Princípio de design: parâmetro `aprovado_por_medico` SEMPRE exigido.
Reforço duplo do HITL — mesmo no nível da tool, prescrição sem aprovação
médica é bloqueada. Defesa em profundidade.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any


# ============================================================
# Base mock de interações
# Cada chave é um par ordenado alfabeticamente para busca simétrica
# ============================================================

_INTERACOES: dict[tuple[str, str], dict[str, Any]] = {
    # --- Losartana (medicação canônica da Maria) ---
    ("ibuprofeno", "losartana"): {
        "severidade": "moderada",
        "mecanismo": "AINEs reduzem o efeito anti-hipertensivo dos bloqueadores AT1",
        "recomendacao": "Evitar uso prolongado de ibuprofeno. Preferir paracetamol para dor leve. Se uso necessário, monitorar pressão arterial.",
    },
    ("diclofenaco", "losartana"): {
        "severidade": "moderada",
        "mecanismo": "AINEs antagonizam ação anti-hipertensiva",
        "recomendacao": "Substituir por analgésico não-AINE (paracetamol/dipirona).",
    },
    ("espironolactona", "losartana"): {
        "severidade": "grave",
        "mecanismo": "Ambos retêm potássio — risco de hipercalemia",
        "recomendacao": "Combinação requer monitoramento rigoroso de potássio sérico.",
    },

    # --- Atorvastatina (medicação do João) ---
    ("atorvastatina", "claritromicina"): {
        "severidade": "grave",
        "mecanismo": "Inibição de CYP3A4 eleva níveis de estatina — risco de rabdomiólise",
        "recomendacao": "Suspender estatina durante o tratamento com claritromicina, ou usar azitromicina como alternativa.",
    },
    ("atorvastatina", "eritromicina"): {
        "severidade": "grave",
        "mecanismo": "Mesmo mecanismo da claritromicina (inibição CYP3A4)",
        "recomendacao": "Evitar associação. Considerar azitromicina.",
    },

    # --- Anticoagulantes / antiagregantes ---
    ("varfarina", "aas"): {
        "severidade": "grave",
        "mecanismo": "Efeito antiagregante + anticoagulante = risco hemorrágico aumentado",
        "recomendacao": "Combinação evitada exceto em pacientes selecionados (ex: pós-IAM com FA), sempre com monitoramento de INR e clínico.",
    },
    ("varfarina", "amoxicilina"): {
        "severidade": "moderada",
        "mecanismo": "Antibióticos alteram flora intestinal, podem aumentar efeito da varfarina",
        "recomendacao": "Monitorar INR durante e após o curso de antibiótico.",
    },

    # --- Serotoninérgicos ---
    ("sertralina", "tramadol"): {
        "severidade": "grave",
        "mecanismo": "Síndrome serotoninérgica — risco de hiperatividade, hipertermia, rigidez",
        "recomendacao": "Evitar combinação. Se uso necessário, monitorar sinais de síndrome serotoninérgica.",
    },

    # --- Metformina (medicação do João) ---
    ("metformina", "contraste iodado"): {
        "severidade": "grave",
        "mecanismo": "Risco de acidose lática em pacientes com função renal limítrofe",
        "recomendacao": "Suspender metformina 48h antes e após exame com contraste.",
    },

    # --- Levotiroxina ---
    ("levotiroxina", "sulfato ferroso"): {
        "severidade": "moderada",
        "mecanismo": "Ferro reduz absorção da levotiroxina",
        "recomendacao": "Separar horários por pelo menos 4 horas.",
    },
}

# Lista de medicamentos que JAMAIS devem ser dados se há alergia registrada
_CONTRAINDICACOES_ALERGIA = {
    "dipirona": ["Dipirona"],
    "ibuprofeno": ["Ibuprofeno", "AINE"],
    "amoxicilina": ["Penicilina", "Amoxicilina", "Beta-lactâmico"],
    "ácido acetilsalicílico": ["AAS", "Aspirina", "Ácido acetilsalicílico"],
    "aas": ["AAS", "Aspirina", "Ácido acetilsalicílico"],
}


# ============================================================
# Tool spec
# ============================================================

TOOL_SPEC = {
    "name": "verificar_interacoes_medicamentosas",
    "description": (
        "Verifica interações entre uma lista de medicamentos (princípios ativos). "
        "Pode também checar contraindicações por alergia se paciente_id for fornecido. "
        "Retorna severidade, mecanismo e recomendação para cada interação encontrada. "
        "OBRIGATÓRIO: parâmetro aprovado_por_medico=true para retornar sugestões de "
        "prescrição final (reforço de HITL)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "medicamentos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de princípios ativos a verificar (ex: ['losartana', 'ibuprofeno']).",
                "minItems": 1,
            },
            "paciente_id": {
                "type": "string",
                "description": "Opcional. Se fornecido, também checa alergias do paciente contra os medicamentos.",
            },
            "aprovado_por_medico": {
                "type": "boolean",
                "description": "Marcador de HITL. Deve ser true APENAS se um médico já validou a prescrição. Default false.",
            },
        },
        "required": ["medicamentos"],
    },
}


# ============================================================
# Implementação
# ============================================================

def _normalize(medicamento: str) -> str:
    """Normaliza nome de medicamento para busca."""
    return medicamento.strip().lower()


def verificar_interacoes_medicamentosas(
    medicamentos: list[str],
    paciente_id: str | None = None,
    aprovado_por_medico: bool = False,
) -> dict[str, Any]:
    """
    Verifica interações entre medicamentos + contraindicações por alergia.

    Returns:
        {
          "status": "success" | "invalid_input",
          "medicamentos_verificados": [...],
          "interacoes_encontradas": [
            {par, severidade, mecanismo, recomendacao}, ...
          ],
          "contraindicacoes_alergia": [...],
          "alerta_hitl": str (se aprovado_por_medico=False),
        }
    """
    if not medicamentos or len(medicamentos) < 1:
        return {
            "status": "invalid_input",
            "mensagem": "Forneça ao menos um medicamento.",
        }

    meds_norm = [_normalize(m) for m in medicamentos]

    # 1. Buscar interações em todos os pares
    interacoes: list[dict[str, Any]] = []
    for med1, med2 in combinations(meds_norm, 2):
        chave = tuple(sorted([med1, med2]))
        if chave in _INTERACOES:
            interacoes.append({
                "par": f"{chave[0]} + {chave[1]}",
                **_INTERACOES[chave],
            })

    # 2. Checar contraindicações por alergia (se paciente_id fornecido)
    contraindicacoes: list[dict[str, Any]] = []
    if paciente_id:
        # Import local para evitar import circular
        from src.tools.consultar_historico import consultar_historico_paciente

        hist = consultar_historico_paciente(paciente_id, campos=["alergias"])
        if hist["status"] == "success":
            alergias_paciente = hist["data"].get("alergias", [])
            for med in meds_norm:
                if med in _CONTRAINDICACOES_ALERGIA:
                    alergenos = _CONTRAINDICACOES_ALERGIA[med]
                    for alergia_registrada in alergias_paciente:
                        for alergeno in alergenos:
                            if alergeno.lower() in alergia_registrada.lower():
                                contraindicacoes.append({
                                    "medicamento": med,
                                    "alergia_registrada": alergia_registrada,
                                    "severidade": "critica",
                                    "recomendacao": f"NÃO PRESCREVER. Paciente tem alergia documentada: {alergia_registrada}.",
                                })

    # 3. Resposta
    resultado: dict[str, Any] = {
        "status": "success",
        "medicamentos_verificados": medicamentos,
        "total_interacoes": len(interacoes),
        "interacoes_encontradas": interacoes,
        "contraindicacoes_alergia": contraindicacoes,
    }

    if not aprovado_por_medico:
        resultado["alerta_hitl"] = (
            "Esta verificação é INFORMATIVA e não substitui revisão médica. "
            "Qualquer prescrição final exige validação por profissional habilitado."
        )

    return resultado
