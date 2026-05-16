"""
Tool: consultar_historico_paciente

Retorna histórico clínico simulado de beneficiários Care Plus.

Pacientes mock:
- BNF-04821: Maria, 34, hipertensa, Losartana 50mg (CANÔNICO do briefing Sprint 2)
- BNF-09732: João, 58, diabético tipo 2, Metformina + Glibenclamida
- BNF-15604: Ana, 28, gestante 22 semanas, sem comorbidades prévias

Decisão de design: validação aceita BNF-XXXXX com 4 OU 5 dígitos.
Lição da Sprint 1: regex strict (^BNF-[0-9]{5}$) quebrava com IDs parciais.
"""
from __future__ import annotations

from typing import Any


# ============================================================
# Base de pacientes mock
# ============================================================

_PACIENTES: dict[str, dict[str, Any]] = {
    "BNF-04821": {
        "paciente_id": "BNF-04821",
        "nome_apelido": "Maria",
        "idade": 34,
        "sexo": "F",
        "condicoes_cronicas": ["Hipertensão arterial sistêmica (HAS)"],
        "alergias": ["Dipirona (rash cutâneo, 2022)"],
        "medicamentos_em_uso": [
            {
                "nome": "Losartana",
                "dose": "50mg",
                "via": "oral",
                "frequencia": "1x/dia, pela manhã",
                "inicio": "2023-08",
                "indicacao": "controle de HAS",
            }
        ],
        "ultima_consulta": {
            "data": "2026-03-15",
            "profissional": "Dr. João Almeida",
            "especialidade": "Clínica Médica",
            "tipo": "teleconsulta",
            "resumo": "Controle pressórico estável. PA 128x82 mmHg.",
        },
        "exames_recentes": [
            {"nome": "Hemograma completo", "data": "2026-02-20", "status": "normal"},
            {"nome": "Perfil lipídico", "data": "2026-02-20", "status": "normal"},
            {"nome": "Creatinina", "data": "2026-02-20", "status": "normal"},
        ],
        "imunizacoes": ["Influenza 2026", "COVID-19 (atualizada)"],
    },
    "BNF-09732": {
        "paciente_id": "BNF-09732",
        "nome_apelido": "João",
        "idade": 58,
        "sexo": "M",
        "condicoes_cronicas": [
            "Diabetes mellitus tipo 2",
            "Dislipidemia",
        ],
        "alergias": [],
        "medicamentos_em_uso": [
            {
                "nome": "Metformina",
                "dose": "850mg",
                "via": "oral",
                "frequencia": "2x/dia, com refeições",
                "inicio": "2020-03",
                "indicacao": "controle glicêmico",
            },
            {
                "nome": "Atorvastatina",
                "dose": "20mg",
                "via": "oral",
                "frequencia": "1x/dia, à noite",
                "inicio": "2021-06",
                "indicacao": "dislipidemia",
            },
        ],
        "ultima_consulta": {
            "data": "2026-04-02",
            "profissional": "Dra. Carolina Ferreira",
            "especialidade": "Endocrinologia",
            "tipo": "presencial",
            "resumo": "HbA1c 6.9%. Mantida conduta.",
        },
        "exames_recentes": [
            {"nome": "HbA1c", "data": "2026-04-02", "status": "alterado leve", "valor": "6.9%"},
            {"nome": "Glicemia jejum", "data": "2026-04-02", "status": "normal", "valor": "112 mg/dL"},
        ],
        "imunizacoes": ["Influenza 2026", "Pneumocócica"],
    },
    "BNF-15604": {
        "paciente_id": "BNF-15604",
        "nome_apelido": "Ana",
        "idade": 28,
        "sexo": "F",
        "condicoes_cronicas": [],
        "alergias": [],
        "medicamentos_em_uso": [
            {
                "nome": "Ácido fólico",
                "dose": "5mg",
                "via": "oral",
                "frequencia": "1x/dia",
                "inicio": "2025-12",
                "indicacao": "suplementação gestacional",
            },
            {
                "nome": "Sulfato ferroso",
                "dose": "40mg",
                "via": "oral",
                "frequencia": "1x/dia",
                "inicio": "2026-02",
                "indicacao": "profilaxia de anemia gestacional",
            },
        ],
        "gestacao": {
            "idade_gestacional_semanas": 22,
            "dum": "2025-12-08",
            "dpp": "2026-09-15",
            "pre_natal_ativo": True,
        },
        "ultima_consulta": {
            "data": "2026-04-28",
            "profissional": "Dra. Mariana Souza",
            "especialidade": "Ginecologia/Obstetrícia",
            "tipo": "presencial",
            "resumo": "Gestação evoluindo bem. USG morfológico normal.",
        },
        "exames_recentes": [
            {"nome": "USG morfológico", "data": "2026-04-15", "status": "normal"},
            {"nome": "Glicemia jejum", "data": "2026-03-10", "status": "normal"},
        ],
        "imunizacoes": ["dTpa", "Influenza 2026"],
    },
}


# ============================================================
# Tool spec (formato Anthropic — conversor para OpenAI fica em llm_provider.py)
# ============================================================

TOOL_SPEC = {
    "name": "consultar_historico_paciente",
    "description": (
        "Consulta o histórico clínico de um beneficiário Care Plus por ID "
        "pseudonimizado (BNF-XXXXX). Retorna condições crônicas, alergias, "
        "medicamentos em uso, última consulta e exames recentes. SEMPRE chame "
        "esta tool antes de fazer sugestões de prescrição ou avaliar interações."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID pseudonimizado no formato BNF seguido de 4-5 dígitos (ex: BNF-04821).",
            },
            "campos": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "idade", "sexo", "condicoes_cronicas", "alergias",
                        "medicamentos_em_uso", "ultima_consulta", "exames_recentes",
                        "imunizacoes", "gestacao",
                    ],
                },
                "description": "Lista opcional de campos a retornar. Se omitido, retorna o histórico completo.",
            },
        },
        "required": ["paciente_id"],
    },
}


# ============================================================
# Implementação
# ============================================================

def consultar_historico_paciente(
    paciente_id: str,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Consulta histórico do paciente. Validação flexível do ID.

    Returns:
        {
          "status": "success" | "not_found" | "invalid_id",
          "paciente_id": str,
          "data": {...} (se success),
          "mensagem": str (se erro)
        }
    """
    # Normalização e validação flexível (lição da Sprint 1)
    if not paciente_id:
        return {
            "status": "invalid_id",
            "paciente_id": paciente_id,
            "mensagem": "ID do paciente é obrigatório.",
        }

    pid = paciente_id.strip().upper()

    # Aceita "BNF-04821", "BNF04821", "04821" — sempre normaliza para BNF-XXXXX
    if pid.startswith("BNF-"):
        normalized = pid
    elif pid.startswith("BNF"):
        normalized = f"BNF-{pid[3:]}"
    elif pid.isdigit():
        normalized = f"BNF-{pid}"
    else:
        return {
            "status": "invalid_id",
            "paciente_id": paciente_id,
            "mensagem": "Formato inválido. Use BNF-XXXXX (ex: BNF-04821).",
        }

    if normalized not in _PACIENTES:
        return {
            "status": "not_found",
            "paciente_id": normalized,
            "mensagem": f"Paciente {normalized} não encontrado na base. IDs disponíveis para teste: BNF-04821, BNF-09732, BNF-15604.",
        }

    paciente = _PACIENTES[normalized]

    # Filtro de campos
    if campos:
        data = {k: paciente.get(k) for k in campos if k in paciente}
        # Sempre incluir identificação
        data["paciente_id"] = paciente["paciente_id"]
        data["nome_apelido"] = paciente.get("nome_apelido", "")
    else:
        data = paciente

    return {
        "status": "success",
        "paciente_id": normalized,
        "data": data,
    }
