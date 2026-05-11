"""
Configuração centralizada do BluaDiagnostics.

ÚNICO ponto de leitura de variáveis de ambiente em todo o projeto.
Outros módulos importam `settings` daqui em vez de chamar os.getenv direto.

Vantagens:
- Validação na inicialização (falha rápido se env var crítica faltar)
- Fácil de mockar em testes
- Documentação viva das variáveis
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Carrega .env do diretório raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Configuração imutável do sistema."""

    # ---- LLM Provider ----
    llm_provider: Literal["groq", "ollama"] = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "groq")  # type: ignore
    )

    # Groq
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model_principal: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL_PRINCIPAL", "llama-3.1-8b-instant")
    )
    groq_model_premium: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL_PREMIUM", "llama-3.3-70b-versatile")
    )

    # Ollama
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )

    # ---- Embeddings ----
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        )
    )

    # ---- Vector Store ----
    chroma_persist_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
    )
    chroma_collection_name: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION_NAME", "blua_kb")
    )

    # ---- Observabilidade ----
    langsmith_api_key: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "")
    )
    langsmith_tracing: bool = field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    )
    langsmith_project: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "bluadiagnostics-sprint2")
    )

    # ---- Parâmetros do agente ----
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.2")))
    top_p: float = field(default_factory=lambda: float(os.getenv("TOP_P", "0.9")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "1024")))

    # ---- Logging ----
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Path = field(
        default_factory=lambda: PROJECT_ROOT / os.getenv("LOG_FILE", "logs/blua.log")
    )

    # ---- Paths derivados ----
    knowledge_base_dir: Path = field(default=PROJECT_ROOT / "data" / "knowledge_base")

    def validate(self) -> None:
        """Valida configuração crítica. Chamar no startup do app."""
        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY não definida no .env. "
                "Obtenha em https://console.groq.com/keys"
            )
        if self.llm_provider == "ollama":
            # Não validamos conexão aqui — deixamos para o provider tentar e falhar com mensagem clara.
            pass
        if not self.knowledge_base_dir.exists():
            raise FileNotFoundError(
                f"Diretório da KB não encontrado: {self.knowledge_base_dir}"
            )


# Instância singleton — importar `settings` nos outros módulos
settings = Settings()
