"""BluaDiagnostics — Wrapper HTTP (FastAPI). Embrulha o pipeline existente."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.graph.builder import build_graph, invoke_with_message
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Construindo o grafo BluaDiagnostics...")
    app.state.graph = build_graph(use_checkpointer=True)
    logger.info("Grafo pronto. Wrapper HTTP no ar.")
    yield
    logger.info("Encerrando wrapper HTTP.")


app = FastAPI(title="BluaDiagnostics API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    grafo_ok = getattr(app.state, "graph", None) is not None
    return {"status": "ok" if grafo_ok else "starting"}


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


def _parece_cpf(valor: str) -> bool:
    so_digitos = "".join(c for c in valor if c.isdigit())
    return len(so_digitos) == 11 and not valor.upper().startswith("BNF")
