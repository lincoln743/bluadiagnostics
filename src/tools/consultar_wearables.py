"""
Tool: consultar_wearables — BÔNUS Sprint 2.

Retorna dados simulados de wearables (Apple Health, Google Fit, Oura) para
enriquecer o check-up digital com dados objetivos de saúde.

Schema baseado em Apple HealthKit (referência de mercado).

Dados mockados são DETERMINÍSTICOS por paciente_id — Maria sempre tem o mesmo
perfil. Isso permite reproducibilidade em demos e testes.

Caso de uso típico (briefing Sprint 2):
- Maria reclama de "cansaço" -> consultar_wearables -> HRV baixo + sono ruim
- Triagem correlaciona com hipertensão + Losartana
- Sugere teleconsulta com cardio para reavaliar horário da medicação
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


# ============================================================
# Perfis mock — determinísticos por paciente
# ============================================================

_PERFIS_WEARABLES: dict[str, dict[str, Any]] = {
    # Maria — hipertensa, fadiga + sono ruim (correlato clínico do briefing)
    "BNF-04821": {
        "dispositivo": "Apple Watch Series 9",
        "fonte": "Apple HealthKit",
        "frequencia_cardiaca": {
            "repouso_bpm": 78,           # ligeiramente elevado para mulher 34a
            "media_24h_bpm": 84,
            "maxima_7d_bpm": 142,
            "minima_7d_bpm": 62,
            "tendencia": "estavel",
        },
        "pressao_arterial_estimada": {
            "sistolica_media_mmhg": 132,   # ligeiramente acima da meta com Losartana
            "diastolica_media_mmhg": 84,
            "ultima_aferição": "2026-05-13 09:14",
            "observacao": "Estimativa baseada em PPG do Apple Watch — não substitui aferição clínica.",
        },
        "spo2": {
            "media_percent": 97,
            "minima_7d_percent": 94,
        },
        "sono": {
            "media_horas_7d": 5.8,           # baixo — correlato de fadiga
            "qualidade_score_100": 62,       # baixo
            "rem_media_minutos": 68,         # abaixo do ideal (~90+)
            "despertar_noturno_media": 3.4,
            "tendencia": "deteriorando",
        },
        "atividade": {
            "passos_media_diaria_7d": 4200,  # abaixo da meta 10k
            "calorias_ativas_media_kcal": 220,
            "minutos_exercicio_semana": 45,  # bem abaixo da recomendação OMS (150min)
        },
        "hrv_ms": {                          # variabilidade — indicador de estresse
            "media_7d": 28,                  # baixo (estresse/recuperação ruim)
            "tendencia": "baixando",
        },
        "eventos_anormais": [
            {
                "tipo": "frequencia_cardiaca_repouso_elevada",
                "data": "2026-05-12",
                "valor": 92,
                "severidade": "leve",
            }
        ],
    },
    # João — diabético, perfil mais ativo, sono melhor
    "BNF-09732": {
        "dispositivo": "Fitbit Charge 6",
        "fonte": "Google Fit",
        "frequencia_cardiaca": {
            "repouso_bpm": 68,
            "media_24h_bpm": 78,
            "maxima_7d_bpm": 138,
            "minima_7d_bpm": 56,
            "tendencia": "estavel",
        },
        "glicemia_estimada": {
            "media_mg_dl": 128,
            "ultima_aferição": "2026-05-13 07:30",
            "observacao": "Estimativa de tendência — não substitui glicemia capilar/laboratorial.",
        },
        "sono": {
            "media_horas_7d": 7.2,
            "qualidade_score_100": 81,
            "rem_media_minutos": 92,
            "despertar_noturno_media": 1.8,
            "tendencia": "estavel",
        },
        "atividade": {
            "passos_media_diaria_7d": 8900,
            "calorias_ativas_media_kcal": 380,
            "minutos_exercicio_semana": 165,  # ótimo
        },
        "hrv_ms": {"media_7d": 45, "tendencia": "estavel"},
        "eventos_anormais": [],
    },
    # Ana — gestante, perfil dentro do esperado para 22 semanas
    "BNF-15604": {
        "dispositivo": "Oura Ring Gen 4",
        "fonte": "Oura",
        "frequencia_cardiaca": {
            "repouso_bpm": 82,               # elevada — fisiológico na gestação
            "media_24h_bpm": 88,
            "maxima_7d_bpm": 144,
            "minima_7d_bpm": 70,
            "tendencia": "aumentando_gradual",
            "nota_clinica": "Aumento esperado na gestação (volume sanguíneo).",
        },
        "spo2": {"media_percent": 98, "minima_7d_percent": 95},
        "sono": {
            "media_horas_7d": 7.8,
            "qualidade_score_100": 76,
            "rem_media_minutos": 88,
            "despertar_noturno_media": 2.5,   # aumenta na gestação
            "tendencia": "estavel",
        },
        "atividade": {
            "passos_media_diaria_7d": 6500,
            "calorias_ativas_media_kcal": 180,
            "minutos_exercicio_semana": 90,
        },
        "hrv_ms": {"media_7d": 38, "tendencia": "estavel"},
        "eventos_anormais": [],
    },
}


# ============================================================
# Tool spec
# ============================================================

TOOL_SPEC = {
    "name": "consultar_wearables",
    "description": (
        "Consulta dados objetivos de wearable do beneficiário (Apple Watch, Fitbit, "
        "Oura Ring). Útil quando o paciente relata sintomas que podem ser correlacionados "
        "com sono, frequência cardíaca, pressão, oxigenação ou atividade. Retorna métricas "
        "dos últimos 7 dias e eventos anormais detectados pelo dispositivo. NÃO substitui "
        "aferição clínica — dados estimados por wearable têm margem de erro."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID do beneficiário (BNF-XXXXX).",
            },
            "periodo_dias": {
                "type": "integer",
                "description": "Período em dias para análise (1-30, default 7).",
                "minimum": 1,
                "maximum": 30,
            },
            "metricas": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "frequencia_cardiaca", "pressao_arterial_estimada", "spo2",
                        "sono", "atividade", "hrv_ms", "glicemia_estimada", "eventos_anormais",
                    ],
                },
                "description": "Subset opcional de métricas. Omita para receber todas as disponíveis.",
            },
        },
        "required": ["paciente_id"],
    },
}


# ============================================================
# Implementação
# ============================================================

def consultar_wearables(
    paciente_id: str,
    periodo_dias: int = 7,
    metricas: list[str] | None = None,
) -> dict[str, Any]:
    """
    Consulta dados de wearable do paciente.

    Returns:
        {
          "status": "success" | "not_found" | "sem_dispositivo",
          "paciente_id": str,
          "dispositivo": str,
          "fonte": str,
          "periodo_dias": int,
          "periodo_inicio": str (ISO),
          "periodo_fim": str (ISO),
          "metricas": {...},
        }
    """
    if not paciente_id:
        return {"status": "invalid_input", "mensagem": "paciente_id é obrigatório."}

    pid = paciente_id.strip().upper()
    if not pid.startswith("BNF-"):
        pid = f"BNF-{pid.lstrip('BNF').lstrip('-')}"

    if pid not in _PERFIS_WEARABLES:
        return {
            "status": "sem_dispositivo",
            "paciente_id": pid,
            "mensagem": f"Beneficiário {pid} não tem wearable conectado ao app Blua.",
        }

    perfil = _PERFIS_WEARABLES[pid]
    periodo_dias = max(1, min(30, periodo_dias))
    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(days=periodo_dias)

    # Filtra métricas se solicitado
    if metricas:
        metricas_filtradas = {
            k: v for k, v in perfil.items()
            if k in metricas or k in ("dispositivo", "fonte")
        }
    else:
        metricas_filtradas = {
            k: v for k, v in perfil.items() if k not in ("dispositivo", "fonte")
        }

    return {
        "status": "success",
        "paciente_id": pid,
        "dispositivo": perfil["dispositivo"],
        "fonte": perfil["fonte"],
        "periodo_dias": periodo_dias,
        "periodo_inicio": inicio.isoformat(),
        "periodo_fim": fim.isoformat(),
        "metricas": metricas_filtradas,
        "disclaimer": "Dados de wearable são estimativas. Para diagnóstico clínico, é necessária aferição médica.",
    }
