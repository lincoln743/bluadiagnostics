"""
Agente de Escalada Humana — DETERMINÍSTICO (zero LLM).

POR QUE ZERO LLM AQUI?
Em emergência clínica, previsibilidade > criatividade. Risco de o LLM
"inventar" uma orientação errada num momento crítico é inaceitável.
Template parametrizado por categoria de red flag cobre 100% dos casos
com mensagens revisadas, sem alucinação possível.

PRINCÍPIOS DE TOM:
- Acolhedor mas DIRETO (sem "vamos respirar fundo", sem floreios)
- Instrução acionável IMEDIATA na primeira frase
- Personalização pelo nome do paciente quando disponível
- Sem disclaimer "informação preliminar" — é emergência, não é hora disso
- Sem perguntas adicionais — meta é tirar a pessoa do app e levar pra ajuda
"""
from __future__ import annotations

from typing import Any

from src.graph.state import BluaState


# ============================================================
# Templates por categoria de red flag
# ============================================================
# Cada template tem 3 partes:
#   1. Primeira frase: instrução imediata (SAMU 192 ou CVV 188)
#   2. Reforço acionável (companhia, transporte)
#   3. Frase de acolhimento curta no final

TEMPLATES_BASE = {
    # Categorias clínicas → SAMU 192
    "cardiovascular": (
        "{saudacao}pelo que você descreveu — {gatilho} — é IMPORTANTE buscar atendimento médico AGORA.\n\n"
        "**Por favor, ligue para o SAMU (192) ou vá ao pronto-socorro mais próximo imediatamente.**\n\n"
        "Se houver alguém com você, peça ajuda para chegar lá. Não dirija sozinho(a) — peça uma ambulância. "
        "Mantenha-se sentado(a) ou deitado(a) até a ajuda chegar.\n\n"
        "Estou aqui se precisar de mais alguma orientação enquanto aguarda."
    ),
    "neurologica": (
        "{saudacao}o que você descreveu — {gatilho} — pode ser um sinal de emergência neurológica. **Cada minuto importa.**\n\n"
        "**Ligue para o SAMU (192) AGORA ou peça que alguém ligue por você.**\n\n"
        "Se possível, anote o horário em que os sintomas começaram — essa informação é crítica para o atendimento. "
        "Não tome aspirina nem outros medicamentos sem orientação médica neste momento."
    ),
    "respiratoria": (
        "{saudacao}falta de ar súbita ou intensa exige avaliação imediata.\n\n"
        "**Ligue para o SAMU (192) ou vá ao pronto-socorro mais próximo agora.**\n\n"
        "Enquanto aguarda: sente-se com o tronco ligeiramente inclinado para frente, mantenha a calma e respire pausadamente. "
        "Se tiver inalador de uso conhecido, pode utilizá-lo conforme orientação prévia do seu médico."
    ),
    "anafilaxia": (
        "{saudacao}o que você descreveu sugere uma reação alérgica grave. **Isso é uma emergência.**\n\n"
        "**Ligue para o SAMU (192) IMEDIATAMENTE.**\n\n"
        "Se você tiver adrenalina autoinjetável (EpiPen) prescrita, use-a agora conforme as instruções. "
        "Tente identificar o que pode ter desencadeado (alimento, medicamento, picada) para informar à equipe médica."
    ),
    "abdominal": (
        "{saudacao}dor abdominal súbita e intensa exige avaliação médica urgente.\n\n"
        "**Procure o pronto-socorro mais próximo agora ou ligue para o SAMU (192).**\n\n"
        "Não tome analgésicos por conta própria — eles podem mascarar sinais importantes para o diagnóstico. "
        "Não coma nem beba nada até a avaliação médica."
    ),
    "gestacional": (
        "{saudacao}qualquer sinal de alerta durante a gestação merece avaliação imediata, pela sua segurança e do bebê.\n\n"
        "**Vá ao pronto-socorro obstétrico mais próximo agora ou ligue para o SAMU (192).**\n\n"
        "Leve consigo a carteira de gestante e a lista de medicações em uso, se possível. "
        "Se houver alguém com você, peça acompanhamento."
    ),
    "pediatrica": (
        "{saudacao}sinais de alerta em crianças pequenas exigem avaliação médica imediata.\n\n"
        "**Leve a criança ao pronto-socorro pediátrico mais próximo agora, ou ligue para o SAMU (192).**\n\n"
        "Mantenha a criança hidratada se ela conseguir beber. Se estiver com febre, pode ofertar antitérmico conforme dose prescrita anteriormente. "
        "Anote o horário em que os sinais começaram."
    ),

    # Saúde mental → CVV 188 (não SAMU)
    "mental_grave": (
        "{saudacao}o que você está sentindo é sério e merece atenção imediata. **Você não está sozinho(a).**\n\n"
        "**Por favor, ligue para o CVV (Centro de Valorização da Vida) no 188 agora. É gratuito, 24 horas, e o atendimento é totalmente sigiloso.**\n\n"
        "Se preferir, você também pode conversar pelo chat em cvv.org.br. "
        "Se houver alguém de confiança por perto, peça para essa pessoa ficar com você neste momento."
    ),

    # Fallback genérico (categoria desconhecida)
    "desconhecida": (
        "{saudacao}pelo que você descreveu, é importante buscar avaliação médica urgente.\n\n"
        "**Ligue para o SAMU (192) ou vá ao pronto-socorro mais próximo.**\n\n"
        "Se for crise psicológica ou ideação de autoagressão, ligue para o CVV no 188."
    ),
}


def _formatar_saudacao(nome_apelido: str | None) -> str:
    """Personaliza com nome quando disponível."""
    if nome_apelido and nome_apelido.strip():
        return f"{nome_apelido.strip()}, "
    return ""


def _formatar_gatilho(frase_gatilho: str) -> str:
    """Sanitiza a frase gatilho para inclusão na mensagem (evita repetição feia)."""
    if not frase_gatilho:
        return "o que você relatou"
    return f'"{frase_gatilho.strip()}"'


def gerar_mensagem_escalada(
    categoria: str,
    nome_apelido: str | None = None,
    frase_gatilho: str = "",
) -> str:
    """
    Gera mensagem de escalada determinística para a categoria.

    Args:
        categoria: chave de TEMPLATES_BASE (cardiovascular, neurologica, ...)
        nome_apelido: nome do paciente para personalização
        frase_gatilho: trecho que disparou a red flag

    Returns:
        Mensagem formatada em markdown leve.
    """
    template = TEMPLATES_BASE.get(categoria, TEMPLATES_BASE["desconhecida"])

    return template.format(
        saudacao=_formatar_saudacao(nome_apelido),
        gatilho=_formatar_gatilho(frase_gatilho),
    )


# ============================================================
# Nó do grafo
# ============================================================

def escalada_node(state: BluaState) -> dict[str, Any]:
    """
    Nó do LangGraph. Lê red flags detectadas no estado e gera resposta
    de orientação de emergência. FINALIZA a conversa (conversa_finalizada=True).

    Returns:
        Update do estado:
            - mensagens: append da resposta do assistente
            - agentes_acionados: ["escalada"]
            - conversa_finalizada: True
    """
    red_flags = state.get("red_flags_detectadas", [])

    if red_flags:
        # Pega a primeira red flag detectada (a mais grave/principal)
        rf = red_flags[-1]  # última adicionada (acabou de ser detectada)
        categoria = rf.get("categoria", "desconhecida")
        frase_gatilho = rf.get("frase_gatilho", "")
    else:
        # Não deveria acontecer (escalada só é acionada com red flag),
        # mas é um caminho defensivo: o user pediu humano explicitamente
        categoria = "desconhecida"
        frase_gatilho = ""

    nome = state.get("paciente", {}).get("nome_apelido")

    mensagem_texto = gerar_mensagem_escalada(
        categoria=categoria,
        nome_apelido=nome,
        frase_gatilho=frase_gatilho,
    )

    nova_mensagem = {
        "role": "assistant",
        "content": mensagem_texto,
    }

    return {
        "mensagens": [nova_mensagem],
        "agentes_acionados": ["escalada"],
        "conversa_finalizada": True,
        "requer_escalada_humana": True,
    }
