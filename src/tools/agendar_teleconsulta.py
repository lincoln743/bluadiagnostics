"""
Tool: agendar_teleconsulta

Mock realista de agendamento de teleconsulta nas 8 especialidades Care Plus.
Gera ID de agendamento, horário disponível plausível e link de videochamada.

Especialidades (vindas de kb03_politica_telemedicina.md):
- clinica_medica
- cardiologia
- ginecologia (e obstetrícia)
- pediatria
- dermatologia
- psiquiatria
- nutricao
- ortopedia

Política de urgência:
- urgente: próximas 2h (com sobretaxa, sob aviso)
- prioridade: próximas 24h
- rotina: próximos 7 dias
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any


# ============================================================
# Configuração
# ============================================================

ESPECIALIDADES_VALIDAS = [
    "clinica_medica",
    "cardiologia",
    "ginecologia",
    "pediatria",
    "dermatologia",
    "psiquiatria",
    "nutricao",
    "ortopedia",
]

URGENCIAS_VALIDAS = ["rotina", "prioridade", "urgente"]

# Profissionais mock por especialidade
_PROFISSIONAIS: dict[str, list[str]] = {
    "clinica_medica": ["Dr. João Almeida", "Dra. Beatriz Lima", "Dr. Carlos Mendes"],
    "cardiologia": ["Dra. Patricia Santos", "Dr. Eduardo Ribeiro"],
    "ginecologia": ["Dra. Mariana Souza", "Dra. Fernanda Costa"],
    "pediatria": ["Dr. Rafael Oliveira", "Dra. Luiza Pereira"],
    "dermatologia": ["Dra. Camila Fernandes", "Dr. Bruno Martins"],
    "psiquiatria": ["Dra. Helena Ferreira", "Dr. Gustavo Rocha"],
    "nutricao": ["Dra. Marina Tavares (Nutricionista)"],
    "ortopedia": ["Dr. André Carvalho", "Dr. Felipe Nunes"],
}


# ============================================================
# Tool spec
# ============================================================

TOOL_SPEC = {
    "name": "agendar_teleconsulta",
    "description": (
        "Agenda uma teleconsulta para o beneficiário em uma das 8 especialidades "
        "cobertas pela Care Plus. Retorna ID do agendamento, profissional designado, "
        "horário, link da videochamada e instruções preparatórias."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID do beneficiário no formato BNF-XXXXX.",
            },
            "especialidade": {
                "type": "string",
                "description": "Especialidade desejada.",
                "enum": ESPECIALIDADES_VALIDAS,
            },
            "urgencia": {
                "type": "string",
                "description": "rotina (7 dias), prioridade (24h) ou urgente (2h).",
                "enum": URGENCIAS_VALIDAS,
            },
            "motivo_resumido": {
                "type": "string",
                "description": "Resumo do motivo da consulta (1-2 frases). Não inclua dados pessoais.",
            },
            "janela_preferencial": {
                "type": "string",
                "description": "Opcional. Janela preferencial em texto livre (ex: 'manhã', 'após 18h').",
            },
        },
        "required": ["paciente_id", "especialidade", "urgencia", "motivo_resumido"],
    },
}


# ============================================================
# Implementação
# ============================================================

def _gerar_agendamento_id() -> str:
    """Gera ID do agendamento no formato CP-ABC123."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CP-{suffix}"


def _calcular_horario(urgencia: str) -> datetime:
    """Calcula horário plausível baseado na urgência."""
    now = datetime.now(timezone.utc)
    if urgencia == "urgente":
        delta = timedelta(hours=random.randint(1, 2))
    elif urgencia == "prioridade":
        delta = timedelta(hours=random.randint(4, 24))
    else:  # rotina
        delta = timedelta(days=random.randint(2, 7), hours=random.randint(0, 8))

    horario = now + delta
    # Arredonda para próximo slot de 30 min e força horário comercial (8h-20h)
    horario = horario.replace(minute=(horario.minute // 30) * 30, second=0, microsecond=0)
    if horario.hour < 8:
        horario = horario.replace(hour=8)
    elif horario.hour >= 20:
        horario = (horario + timedelta(days=1)).replace(hour=9, minute=0)
    return horario


def _instrucoes_por_especialidade(especialidade: str) -> list[str]:
    """Instruções preparatórias específicas por especialidade."""
    base = [
        "Esteja em ambiente silencioso e bem iluminado",
        "Tenha em mãos seus medicamentos em uso",
        "Conecte-se 5 minutos antes do horário",
    ]
    extras = {
        "cardiologia": ["Se possível, tenha aferidor de pressão por perto", "Liste sintomas recentes e quando ocorrem"],
        "dermatologia": ["Tenha boa iluminação natural", "Tire fotos prévias da lesão se quiser compartilhar"],
        "nutricao": ["Anote o que comeu nas últimas 24h", "Tenha balança e medidas atuais se possível"],
        "pediatria": ["Esteja com a criança presente e calma", "Tenha caderneta de vacinação em mãos"],
        "ginecologia": ["Lembre-se da DUM (data da última menstruação)"],
        "psiquiatria": ["Liste medicações psicotrópicas em uso", "Pense em sintomas e gatilhos das últimas semanas"],
        "ortopedia": ["Esteja com roupa que facilite mostrar a região afetada"],
    }
    return base + extras.get(especialidade, [])


def agendar_teleconsulta(
    paciente_id: str,
    especialidade: str,
    urgencia: str,
    motivo_resumido: str,
    janela_preferencial: str | None = None,
) -> dict[str, Any]:
    """
    Agenda uma teleconsulta. Mock realista.

    Returns:
        {
          "status": "success" | "invalid_input",
          "agendamento_id": "CP-XXXXXX",
          "data_hora_iso": "...",
          "data_hora_humano": "...",
          "profissional": "Dr. ...",
          "especialidade": "...",
          "urgencia": "...",
          "link_video": "https://...",
          "instrucoes_preparatorias": [...],
          "observacao_janela": "..." (opcional),
        }
    """
    # Validações
    if not paciente_id or not paciente_id.strip():
        return {"status": "invalid_input", "mensagem": "paciente_id é obrigatório."}

    if especialidade not in ESPECIALIDADES_VALIDAS:
        return {
            "status": "invalid_input",
            "mensagem": f"Especialidade '{especialidade}' não disponível. Opções: {', '.join(ESPECIALIDADES_VALIDAS)}.",
        }

    if urgencia not in URGENCIAS_VALIDAS:
        return {
            "status": "invalid_input",
            "mensagem": f"Urgência '{urgencia}' inválida. Opções: {', '.join(URGENCIAS_VALIDAS)}.",
        }

    if not motivo_resumido or not motivo_resumido.strip():
        return {"status": "invalid_input", "mensagem": "motivo_resumido é obrigatório."}

    # Gera o agendamento
    agendamento_id = _gerar_agendamento_id()
    horario = _calcular_horario(urgencia)
    profissional = random.choice(_PROFISSIONAIS[especialidade])

    resultado: dict[str, Any] = {
        "status": "success",
        "agendamento_id": agendamento_id,
        "paciente_id": paciente_id,
        "especialidade": especialidade,
        "urgencia": urgencia,
        "motivo_resumido": motivo_resumido,
        "data_hora_iso": horario.isoformat(),
        "data_hora_humano": horario.strftime("%d/%m/%Y às %H:%M"),
        "profissional": profissional,
        "link_video": f"https://blua.careplus.com.br/teleconsulta/{agendamento_id.lower()}",
        "instrucoes_preparatorias": _instrucoes_por_especialidade(especialidade),
    }

    if janela_preferencial:
        resultado["observacao_janela"] = (
            f"Sua preferência de janela ('{janela_preferencial}') foi registrada. "
            "Se houver remarcação possível para a janela preferida, você será notificado."
        )

    return resultado
