"""
BluaDiagnostics — Streamlit UI (Dia 8).

Layout em 3 colunas:
    [Sidebar]      |    [Chat principal]      |    [Painel observabilidade]
    - Paciente     |    - Histórico mensagens |    - Trajetória atual
    - Provider     |    - Input chat          |    - Tools chamadas
    - Botões       |                          |    - Docs RAG
                   |                          |    - Red flags

Eventos são registrados via Tracer (logs/traces/{thread_id}.jsonl).

Uso:
    streamlit run src/ui/app.py
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime

import streamlit as st

# Importa lazy (Streamlit cacheia builds)
from src.graph.builder import build_graph, invoke_with_message
from src.observability.tracer import Tracer
from src.providers.llm_provider import reset_provider_cache


# ============================================================
# Configuração da página
# ============================================================

st.set_page_config(
    page_title="BluaDiagnostics — Care Plus",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Pacientes disponíveis (mock — em produção viria de um cadastro)
# ============================================================

PACIENTES = {
    "BNF-04821": {
        "nome": "Maria",
        "descricao": "34a · Hipertensa · Losartana 50mg · Alérgica a Dipirona",
        "emoji": "👩",
    },
    "BNF-09732": {
        "nome": "João",
        "descricao": "62a · Diabetes tipo 2 · Metformina",
        "emoji": "👨",
    },
    "BNF-15604": {
        "nome": "Ana",
        "descricao": "28a · Gestante 22 semanas",
        "emoji": "🤰",
    },
}


# ============================================================
# Sessão Streamlit
# ============================================================

def _init_session_state():
    """Inicializa variáveis de sessão. Idempotente."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"ui-{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "paciente_id" not in st.session_state:
        st.session_state.paciente_id = "BNF-04821"  # Maria default
    if "provider_name" not in st.session_state:
        st.session_state.provider_name = "groq"
    if "tracer" not in st.session_state:
        st.session_state.tracer = Tracer(thread_id=st.session_state.thread_id)
    if "graph" not in st.session_state:
        st.session_state.graph = build_graph()
    if "ultimo_estado" not in st.session_state:
        st.session_state.ultimo_estado = None
    if "ultimo_duracao_s" not in st.session_state:
        st.session_state.ultimo_duracao_s = 0.0


def _resetar_conversa():
    """Limpa histórico e cria novo thread_id."""
    st.session_state.thread_id = f"ui-{uuid.uuid4().hex[:8]}"
    st.session_state.messages = []
    st.session_state.tracer = Tracer(thread_id=st.session_state.thread_id)
    st.session_state.ultimo_estado = None
    st.session_state.ultimo_duracao_s = 0.0
    # Força grafo a recompilar para zerar checkpointer
    st.session_state.graph = build_graph()


# ============================================================
# Sidebar — configuração
# ============================================================

def _render_sidebar():
    with st.sidebar:
        st.markdown("## 🩺 BluaDiagnostics")
        st.caption("Care Plus · Assistente Virtual de Saúde")
        st.divider()

        # --- Paciente ---
        st.markdown("### 👤 Paciente em sessão")
        opcoes_pacientes = {
            f"{p['emoji']} {p['nome']} ({pid})": pid
            for pid, p in PACIENTES.items()
        }
        label_selecionada = st.radio(
            "Escolha o perfil",
            list(opcoes_pacientes.keys()),
            index=list(opcoes_pacientes.values()).index(st.session_state.paciente_id),
            label_visibility="collapsed",
        )
        novo_paciente = opcoes_pacientes[label_selecionada]
        if novo_paciente != st.session_state.paciente_id:
            st.session_state.paciente_id = novo_paciente
            _resetar_conversa()
            st.rerun()

        # Descrição do paciente atual
        pac_info = PACIENTES[st.session_state.paciente_id]
        st.info(f"**{pac_info['nome']}**\n\n{pac_info['descricao']}")

        st.divider()

        # --- Provider ---
        st.markdown("### ⚙️ Provider de IA")
        provider_escolhido = st.radio(
            "Backend LLM",
            options=["groq", "ollama"],
            format_func=lambda x: {
                "groq": "⚡ Groq Cloud (Llama 3.1 8B)",
                "ollama": "🦙 Ollama Local (Llama 3.2 3B) · LGPD",
            }[x],
            index=0 if st.session_state.provider_name == "groq" else 1,
            label_visibility="collapsed",
        )
        if provider_escolhido != st.session_state.provider_name:
            antigo = st.session_state.provider_name
            st.session_state.provider_name = provider_escolhido
            # Atualiza env var para que get_provider() pegue
            import os
            os.environ["LLM_PROVIDER"] = provider_escolhido
            reset_provider_cache()
            st.session_state.tracer.log_provider_changed(antigo, provider_escolhido)
            st.rerun()

        if provider_escolhido == "ollama":
            st.warning(
                "⏱️ **Ollama local** roda em CPU. Resposta pode levar 30-90s.\n\n"
                "Garante LGPD: dados nunca saem do dispositivo."
            )

        st.divider()

        # --- Ações ---
        if st.button("🔄 Nova conversa", use_container_width=True):
            _resetar_conversa()
            st.rerun()

        st.divider()
        st.caption(f"**Thread**: `{st.session_state.thread_id}`")
        st.caption(f"**Turno atual**: {st.session_state.tracer.turno_atual}")
        st.caption(f"**Log file**: `{st.session_state.tracer.log_file.name}`")


# ============================================================
# Chat principal
# ============================================================

def _render_chat():
    st.markdown("### 💬 Conversa")

    pac = PACIENTES[st.session_state.paciente_id]
    st.caption(
        f"Você está conversando como **{pac['emoji']} {pac['nome']}** · "
        f"Provider: **{st.session_state.provider_name.upper()}**"
    )

    # Histórico de mensagens
    chat_container = st.container(height=520, border=True)
    with chat_container:
        if not st.session_state.messages:
            st.info(
                f"👋 Olá {pac['nome']}! Sou o BluaDiagnostics. "
                "Pode me contar o que está sentindo, perguntar sobre suas "
                "medicações ou pedir orientação. Como posso ajudar?"
            )
        for msg in st.session_state.messages:
            role = msg.get("role", "assistant")
            avatar = pac["emoji"] if role == "user" else "🩺"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg.get("content", ""))

    # Input
    if prompt := st.chat_input("Digite sua mensagem..."):
        _processar_mensagem(prompt)
        st.rerun()


def _processar_mensagem(user_text: str) -> None:
    """Adiciona mensagem do usuário + invoca o grafo + registra trace."""
    tracer = st.session_state.tracer
    pac = PACIENTES[st.session_state.paciente_id]

    # 1. Append à conversa
    st.session_state.messages.append({"role": "user", "content": user_text})
    tracer.log_user_message(user_text, paciente_id=st.session_state.paciente_id)

    # 2. Spinner durante invocação
    with st.spinner(f"🩺 Processando com {st.session_state.provider_name.upper()}..."):
        inicio = time.time()
        try:
            historico_anterior = [
                m for m in st.session_state.messages[:-1]
                if m.get("role") in ("user", "assistant")
            ]
            estado_final = invoke_with_message(
                graph=st.session_state.graph,
                user_message=user_text,
                paciente_id=st.session_state.paciente_id,
                nome_apelido=pac["nome"],
                thread_id=st.session_state.thread_id,
                historico_anterior=historico_anterior,
            )
            duracao = time.time() - inicio
            st.session_state.ultimo_duracao_s = duracao
            st.session_state.ultimo_estado = estado_final

            # 3. Logging detalhado dos eventos do turno
            _registrar_eventos_estado(tracer, estado_final)

            # 4. Append resposta do assistente
            ultima_msg = next(
                (m for m in reversed(estado_final.get("mensagens", []))
                 if m.get("role") == "assistant"),
                None,
            )
            if ultima_msg:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ultima_msg.get("content", ""),
                })
                tracer.log_response(
                    content=ultima_msg.get("content", ""),
                    agente=(estado_final.get("agentes_acionados") or ["desconhecido"])[-1],
                    provider=st.session_state.provider_name,
                )
        except Exception as exc:
            duracao = time.time() - inicio
            tracer.log_error("processar_mensagem", str(exc))
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"❌ Erro ao processar sua mensagem: `{type(exc).__name__}`. "
                    "Tente novamente ou troque o provider."
                ),
            })


def _registrar_eventos_estado(tracer: Tracer, estado: dict) -> None:
    """Extrai eventos detalhados do estado final do grafo e loga no tracer."""
    # Supervisor
    intent = estado.get("intent")
    motivo = estado.get("motivo_classificacao", "")
    if intent:
        fonte = "rule"
        if "llm" in motivo.lower():
            fonte = "llm"
        elif "moderation" in motivo.lower() or "jailbreak" in motivo.lower():
            fonte = "moderation"
        tracer.log_supervisor_decision(intent=intent, motivo=motivo, fonte=fonte)

    # Moderation
    if "jailbreak" in motivo.lower() or "moderation" in motivo.lower():
        tracer.log_moderation_blocked(
            categoria=motivo[:60],
            trecho="",
        )

    # Red flags
    for rf in estado.get("red_flags_detectadas", []):
        tracer.log_red_flag(
            categoria=rf.get("categoria", ""),
            frase_gatilho=rf.get("frase_gatilho", ""),
            fonte=rf.get("fonte_deteccao", "regra"),
        )

    # Agentes
    for ag in estado.get("agentes_acionados", []):
        if ag != "supervisor":
            tracer.log_agent_invoked(ag)

    # Tools
    for tc in estado.get("tools_chamadas", []):
        tracer.log_tool_called(
            tool_name=tc.get("nome", ""),
            args=tc.get("args", {}),
            result_status="success" if "ok" in tc.get("result_resumo", "") else "other",
            result_summary=tc.get("result_resumo", ""),
        )

    # RAG
    docs = estado.get("docs_recuperados", [])
    if docs:
        tracer.log_rag_retrieved([dict(d) for d in docs])


# ============================================================
# Painel de observabilidade (direita)
# ============================================================

def _render_painel_obs():
    st.markdown("### 🔍 Observabilidade")

    estado = st.session_state.ultimo_estado
    if estado is None:
        st.info("Envie uma mensagem para ver a trajetória de processamento.")
        return

    # --- Métricas do último turno ---
    col1, col2 = st.columns(2)
    duracao = st.session_state.ultimo_duracao_s
    intent = estado.get("intent", "—")
    col1.metric("⏱️ Latência", f"{duracao:.1f}s")
    col2.metric("🎯 Intent", intent)

    st.divider()

    # --- Trajetória de agentes ---
    st.markdown("**🤖 Trajetória de agentes**")
    agentes = estado.get("agentes_acionados", [])
    if agentes:
        trajetoria = " → ".join([f"`{a}`" for a in agentes])
        st.markdown(trajetoria)
    else:
        st.caption("nenhum")

    # --- Motivo da classificação ---
    motivo = estado.get("motivo_classificacao", "")
    if motivo:
        st.caption(f"💡 *{motivo[:200]}*")

    st.divider()

    # --- Red flags ---
    red_flags = estado.get("red_flags_detectadas", [])
    if red_flags:
        st.markdown("**🚨 Red flags detectadas**")
        for rf in red_flags:
            severidade = rf.get("severidade", "alta")
            cor_emoji = "🔴" if severidade == "critica" else "🟡"
            fonte = rf.get("fonte_deteccao", "regra")
            st.markdown(
                f"{cor_emoji} **{rf.get('categoria', '?')}** "
                f"_(via {fonte})_"
            )
            st.caption(f"Gatilho: `{rf.get('frase_gatilho', '')[:80]}`")
        st.divider()

    # --- Tools chamadas ---
    tools = estado.get("tools_chamadas", [])
    if tools:
        st.markdown(f"**🔧 Tools chamadas ({len(tools)})**")
        for t in tools:
            st.markdown(f"- `{t.get('nome', '?')}`")
            resumo = t.get("result_resumo", "")
            if resumo:
                st.caption(f"  → {resumo[:100]}")
        st.divider()

    # --- Docs RAG ---
    docs = estado.get("docs_recuperados", [])
    if docs:
        st.markdown(f"**📚 Docs RAG ({len(docs)})**")
        for d in docs[:5]:
            score = d.get("score", 0.0)
            cor = "🟢" if score > 0.7 else "🟡" if score > 0.5 else "🔴"
            st.markdown(
                f"{cor} `{d.get('source_file', '?')}` "
                f"_(score {score:.2f})_"
            )
            sec = d.get("section", "")
            if sec:
                st.caption(f"  §{sec[:60]}")
        st.divider()

    # --- HITL ---
    if estado.get("requer_escalada_humana"):
        st.warning(
            "👨‍⚕️ **HITL ativo** — esta interação requer validação por médico humano."
        )


# ============================================================
# Main
# ============================================================

def main():
    _init_session_state()
    _render_sidebar()

    col_chat, col_obs = st.columns([3, 2], gap="large")
    with col_chat:
        _render_chat()
    with col_obs:
        _render_painel_obs()


if __name__ == "__main__":
    main()
