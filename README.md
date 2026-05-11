# 🩺 BluaDiagnostics — Sprint 2

> Assistente de IA conversacional para Check-up Digital e Prescrição Remota Inteligente — pacientes Care Plus / Bupa.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange)](https://langchain-ai.github.io/langgraph/)
[![Status: Em desenvolvimento](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)]()
[![Sprint 1](https://img.shields.io/badge/Sprint%201-concluída-success)](https://github.com/lincoln743/bluadiagnostics)

> ⚠️ **Aviso**: protótipo acadêmico (FIAP – Prompt Engineering and AI). Não substitui consulta médica. Toda recomendação clínica é HITL (Human-in-the-Loop) — validada por médico antes de qualquer prescrição.

---

## 📑 Índice

1. [Contexto](#contexto)
2. [Arquitetura](#arquitetura)
3. [Como executar](#como-executar)
4. [Estrutura do repositório](#estrutura-do-repositório)
5. [Bônus implementados](#bônus-implementados)
6. [Iterações de prompt](#iterações-de-prompt)
7. [Resultados dos evals](#resultados-dos-evals)
8. [Trade-offs e limitações](#trade-offs-e-limitações)
9. [Equipe](#equipe)

---

## Contexto

**Cliente fictício**: Care Plus — operadora de saúde premium do grupo Bupa, 600k+ beneficiários, 30+ anos no Brasil.
**Produto**: BluaDiagnostics — transforma o app Blua de reativo (agendamento) em proativo (cuidado contínuo).
**Persona**: beneficiário em autoavaliação clínica preliminar, tom acolhedor, conservador, sem jargão.

### Princípios inegociáveis

| Princípio | Implementação |
|---|---|
| **HITL obrigatório** | Agente de prescrição interrompe o grafo antes de finalizar (`interrupt_before`) |
| **Pseudonimização** | IDs no formato `BNF-XXXXX` — nenhum dado pessoal direto |
| **LGPD-by-design** | Opção Ollama local para zero saída de dados do device |
| **Red flag = escalada** | Detector dispara antes do supervisor, curto-circuita para SAMU 192 / CVV 188 |
| **Refusal robusto** | Guardrail de moderação + casos no eval set |

---

## Arquitetura

Sistema multi-agente orquestrado por LangGraph com 4 agentes especializados:

```
        ┌─────────────────────────────┐
        │   Interface (Streamlit)     │
        └──────────────┬──────────────┘
                       │
              ┌────────▼────────┐
              │   Supervisor    │  ← classifica intent
              │   (LangGraph)   │  ← detecta red flag (curto-circuito)
              └────┬────┬───┬───┘
                   │    │   │
        ┌──────────▼┐ ┌─▼─┐ ▼──────────┐
        │ Triagem   │ │ Pres-          │  Escalada
        │ Agent     │ │ crição         │  Humana
        └─────┬─────┘ └──┬─────────────┘  └────┬───┘
              │          │                     │
              └────┬─────┘                     │
                   ▼                           │
        ┌────────────────────────┐             │
        │   Tools compartilhadas │             │
        │  • consultar_historico │             │
        │  • verificar_interacoes│             │
        │  • agendar_teleconsulta│             │
        │  • buscar_conhecimento │ ← RAG       │
        │  • consultar_wearables │ ← BÔNUS     │
        └───────────┬────────────┘             │
                    ▼                          ▼
        ┌────────────────────────┐    ┌─────────────────┐
        │   RAG (ChromaDB)       │    │   Logs JSONL    │
        │   5 docs da KB         │    │   + LangSmith   │
        └────────────────────────┘    └─────────────────┘
```

Diagrama detalhado renderizado em [`docs/arquitetura_sprint2.svg`](docs/arquitetura_sprint2.svg) (gerado no Dia 4).

### Stack

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Orquestração | **LangGraph** 0.2+ | Exigência do briefing; suporta interrupt + checkpointer |
| LLM principal | **Groq Llama 3.1 8B / 3.3 70B** | Free tier 500k tokens/dia; latência LPU ~200ms |
| LLM local (BÔNUS) | **Ollama Llama 3.2 3B** | Justificativa LGPD: dados de saúde nunca saem do device |
| Embeddings | **sentence-transformers** (multilingual MiniLM-L12) | Multilíngue PT-BR, 118MB, sem custo |
| Vector store | **ChromaDB** | Open source, persistência local, integração nativa LangChain |
| Interface | **Streamlit** | Demo visual, painel lateral mostrando trajetória + RAG |
| Observabilidade (BÔNUS) | **LangSmith** + logs JSONL | Traces visuais + auditoria estruturada |
| Testes (BÔNUS) | **pytest** + cobertura | Tools e guardrails |

---

## Como executar

### 1. Pré-requisitos

- Python 3.11+
- Conta Groq (chave em https://console.groq.com/keys)
- Opcional: Ollama instalado (https://ollama.com)

### 2. Instalação

```bash
# Clonar e entrar
git clone https://github.com/lincoln743/bluadiagnostics.git
cd bluadiagnostics
git checkout sprint2

# Ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Dependências
pip install -e ".[dev]"

# Configuração
cp .env.example .env
# Editar .env e colar sua chave Groq real
```

### 3. Popular o vector store (RAG)

```bash
blua-ingest
# ou: python -m src.rag.ingest
```

Isso lê `data/knowledge_base/*.md` e persiste em `data/chroma_db/`.

### 4. Rodar a interface

```bash
streamlit run app/streamlit_app.py
```

Abre em `http://localhost:8501`.

### 5. (Opcional) Rodar com Ollama local

```bash
# Em outro terminal
ollama serve
ollama pull llama3.2:3b

# No .env, mudar:
LLM_PROVIDER=ollama
```

### 6. Rodar a suite de evals

```bash
blua-eval
# Gera evals/sprint2_results.json + gráficos em docs/img/
```

### 7. Rodar testes (bônus)

```bash
pytest tests/ -v
pytest --cov=src tests/  # com cobertura
```

---

## Estrutura do repositório

```
bluadiagnostics/
├── README.md
├── pyproject.toml             # dependências + scripts CLI
├── requirements.txt
├── .env.example               # placeholders OBVIAMENTE fake
├── .gitignore                 # blindado contra vazamento de chaves
├── src/
│   ├── config.py              # único ponto de leitura de env vars
│   ├── agents/
│   │   ├── supervisor.py      # roteador central
│   │   ├── triagem.py         # check-up digital
│   │   ├── prescricao.py      # prescrição com HITL
│   │   └── escalada.py        # escalada humana imediata
│   ├── tools/
│   │   ├── consultar_historico.py
│   │   ├── verificar_interacoes.py
│   │   ├── agendar_teleconsulta.py
│   │   ├── buscar_conhecimento.py     # RAG como tool
│   │   └── consultar_wearables.py     # BÔNUS
│   ├── rag/
│   │   ├── ingest.py          # chunking + embeddings + persist
│   │   └── retriever.py       # interface de consulta
│   ├── graph/
│   │   ├── state.py           # TypedDict BluaState
│   │   └── builder.py         # monta StateGraph
│   ├── guardrails/
│   │   ├── red_flags.py
│   │   ├── scope.py
│   │   └── moderation.py
│   ├── prompts/
│   │   ├── system_prompts.py  # versionado como código
│   │   └── few_shots.py
│   ├── providers/
│   │   └── llm_provider.py    # Groq ↔ Ollama
│   └── observability/
│       └── tracing.py         # logs JSONL + LangSmith
├── data/
│   └── knowledge_base/        # 5 docs da Sprint 1
├── evals/
│   ├── sprint1_eval_set.json  # reusado da Sprint 1
│   ├── sprint2_eval_set.json  # +8 casos novos (RAG, routing)
│   ├── runner.py
│   └── sprint2_results.json   # output do eval (commitado)
├── app/
│   └── streamlit_app.py
├── notebooks/
│   ├── sprint2_demo.ipynb
│   └── rag_validation.ipynb
├── tests/
│   ├── test_tools.py
│   ├── test_guardrails.py
│   └── test_prompts.py
└── docs/
    ├── arquitetura_sprint2.svg
    ├── relatorio_final.md
    └── relatorio_final.pdf    # ABNT LaTeX
```

---

## Bônus implementados

| Bônus | Status | Como verificar |
|---|---|---|
| **3+ agentes especializados** | ✅ 4 agentes | Diagrama acima + `src/agents/` |
| **Ollama local (LGPD)** | 🚧 Dia 6-7 | `LLM_PROVIDER=ollama` no `.env` |
| **Observabilidade** | 🚧 Dia 8-9 | LangSmith traces no vídeo + `logs/trajectories.jsonl` |
| **Wearables mockados** | 🚧 Dia 5-6 | Tool `consultar_wearables` em `src/tools/` |
| **Prompting avançado** | 🚧 Dia 3-10 | Few-shot + chain-of-thought em `src/prompts/` |
| **Testes unitários** | 🚧 Dia 6-7 | `pytest tests/ --cov=src` |

> 🚧 = em desenvolvimento. Atualizar para ✅ conforme as fases forem completadas.

---

## Iterações de prompt

> **Critério explícito do briefing**: documentar iterações feitas e ganho de performance em cada uma.

| Iteração | Mudança | Score eval set | Observação |
|---|---|---|---|
| v1.0 | Baseline Sprint 1 | _(a medir)_ | System prompt monolítico |
| v1.1 | Few-shot supervisor | _(a medir)_ | +6 exemplos cobrindo as 4 intents |
| v1.2 | Chain-of-thought triagem | _(a medir)_ | "Pense passo a passo" antes de responder |
| v1.3 | Disclaimer estruturado | _(a medir)_ | Bloco fixo no final de toda resposta clínica |
| v1.4 | _A definir após primeira rodada de evals_ | | |

---

## Resultados dos evals

> 🚧 Será preenchido no Dia 10 da Sprint 2. Output completo em [`evals/sprint2_results.json`](evals/sprint2_results.json).

### Acurácia por categoria (placeholder)

| Categoria | N casos | Acertos | Acurácia |
|---|---|---|---|
| happy_path | 4 | – | – |
| red_flag | 3 | – | – |
| jailbreak | 3 | – | – |
| out_of_scope | 2 | – | – |
| rag_recall | 3 | – | – |
| routing_correto | 3 | – | – |

### Métricas agregadas (placeholder)

- Taxa de escalada correta: _(a medir)_
- Tempo médio de resposta: _(a medir)_
- Custo estimado por conversa: _(a medir)_

---

## Trade-offs e limitações

Documentado em [`docs/relatorio_final.md`](docs/relatorio_final.md). Resumo:

- **Llama 3.1 8B vs 3.3 70B**: 8B é mais barato e rápido mas perde precisão em casos clínicos sutis. Estratégia adotada: 8B no roteamento, 70B nas decisões críticas.
- **ChromaDB local**: simples e gratuito, mas não escala para milhões de docs. Para produção, considerar Qdrant ou Pinecone.
- **Mocks de tools**: tudo é simulado. Integração real com sistemas Care Plus está no roadmap pós-Sprint 2.
- **Ollama no T430u**: limitado a modelos ≤4B params. Suficiente para PoC mas não para produção.

---

## Equipe

**Grupo NextGen — FIAP**
Curso: Prompt Engineering and Artificial Intelligence
Professor: Jorge Luiz Gomes

| Nome | RM |
|---|---|
| Gustavo Franzoti Gonçalves | 566983 |
| Lincoln Simão Pereira | 567284 |
| Maykon Santana Fonseca | 567041 |
| Nicolas Sakaue Nishimura | 567752 |

**Mantenedor do repositório**: [@lincoln743](https://github.com/lincoln743) · lincoln743@gmail.com

---

## Licença

Projeto acadêmico — uso educacional. Care Plus, Bupa, e marcas associadas pertencem a seus respectivos titulares.
