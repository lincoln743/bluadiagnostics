"""BluaDiagnostics — Wrapper HTTP (FastAPI). Embrulha o pipeline existente."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.graph.builder import build_graph, invoke_with_message
from src.config import settings
from app.api.translator import traduzir_estado_para_contrato

logger = logging.getLogger("blua.api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class ChatRequest(BaseModel):
    paciente_id: str = Field(...)
    mensagem: str = Field(..., min_length=1)
    thread_id: str = Field(default="default")
    perfil: Literal["paciente", "medico"] = Field(default="paciente")
    nome_apelido: str | None = Field(default=None)


class ChatResponse(BaseModel):
    resposta: str
    intent: str | None
    requer_escalada_humana: bool
    red_flags: list[dict[str, Any]]
    sugestao_prescricao: dict[str, Any] | None
    tools_usadas: list[str]
    docs_consultados: list[str]
    thread_id: str


class EmbedRequest(BaseModel):
    textos: list[str] = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int
    modelo: str


class RagAnswerRequest(BaseModel):
    pergunta: str = Field(..., min_length=1)
    contexto: str = Field(..., min_length=1)


class RagAnswerResponse(BaseModel):
    resposta: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Construindo o grafo BluaDiagnostics...")
    app.state.graph = build_graph(use_checkpointer=True)
    logger.info("Grafo pronto.")
    logger.info("Carregando modelo de embeddings (%s)...", settings.embedding_model)
    from langchain_community.embeddings import SentenceTransformerEmbeddings
    app.state.embedder = SentenceTransformerEmbeddings(model_name=settings.embedding_model)
    logger.info("Embedder pronto.")
    logger.info("Wrapper HTTP no ar.")
    yield
    logger.info("Encerrando wrapper HTTP.")


app = FastAPI(title="BluaDiagnostics API", version="1.2.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    ok = all(getattr(app.state, a, None) is not None for a in ("graph", "embedder"))
    return {"status": "ok" if ok else "starting"}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if _parece_cpf(req.paciente_id):
        raise HTTPException(status_code=400, detail="paciente_id parece CPF. Envie BNF-XXXXX.")
    try:
        estado_final = invoke_with_message(
            graph=app.state.graph,
            user_message=req.mensagem,
            paciente_id=req.paciente_id,
            nome_apelido=req.nome_apelido or "Paciente",
            thread_id=req.thread_id,
        )
    except Exception as exc:
        logger.exception("Falha ao invocar o pipeline da IA")
        raise HTTPException(status_code=502, detail="Erro no servico de IA.") from exc
    contrato = traduzir_estado_para_contrato(estado_final, thread_id=req.thread_id)
    return ChatResponse(**contrato)


@app.post("/api/v1/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest) -> EmbedResponse:
    """Gera embeddings dos textos usando o mesmo modelo da KB (384 dims)."""
    try:
        vetores = app.state.embedder.embed_documents(req.textos)
        dim = len(vetores[0]) if vetores else 0
        return EmbedResponse(embeddings=vetores, dim=dim, modelo=settings.embedding_model)
    except Exception as exc:
        logger.exception("Erro ao gerar embeddings")
        raise HTTPException(status_code=500, detail=f"Erro de embedding: {exc}") from exc


@app.post("/api/v1/rag-answer", response_model=RagAnswerResponse)
async def rag_answer(req: RagAnswerRequest) -> RagAnswerResponse:
    """
    Responde uma pergunta do MEDICO com base em trechos de documentos curados.
    NAO passa pelo grafo de triagem — e uma consulta a base de conhecimento,
    nao um atendimento de paciente. Sem red flags, sem encaminhamento.
    """
    system = (
        "Você é um assistente de conhecimento médico. Sua tarefa é responder à "
        "pergunta do MÉDICO usando APENAS os trechos de documentos fornecidos. "
        "IMPORTANTE: isto NÃO é um atendimento de paciente. NÃO faça triagem, NÃO "
        "presuma que há um paciente em risco, NÃO sugira procurar pronto-socorro. "
        "Apenas resuma e explique o que os documentos dizem, de forma objetiva e "
        "técnica, citando as fontes pelo número (ex: Fonte 1). Se a informação não "
        "estiver nos trechos, diga que os documentos não cobrem isso."
    )
    user = f"PERGUNTA DO MÉDICO:\n{req.pergunta}\n\nTRECHOS DOS DOCUMENTOS:\n{req.contexto}"
    try:
        # Reusa o provider Groq da Blua (mesmo cliente/modelo), sem o grafo de triagem.
        from src.providers.llm_provider import get_provider
        provider = get_provider()
        resp = provider.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        # LLMResponse: tenta varios atributos comuns para extrair o texto.
        texto = (
            getattr(resp, "texto", None)
            or getattr(resp, "conteudo", None)
            or getattr(resp, "content", None)
            or getattr(resp, "text", None)
            or str(resp)
        )
        return RagAnswerResponse(resposta=str(texto).strip())
    except Exception as exc:
        logger.exception("Erro no rag-answer")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {exc}") from exc


def _parece_cpf(valor: str) -> bool:
    so_digitos = "".join(c for c in valor if c.isdigit())
    return len(so_digitos) == 11 and not valor.upper().startswith("BNF")
