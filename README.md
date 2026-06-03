# 🩺 BluaDiagnostics — Sprint 2

> Assistente de IA multi-agente para Check-up Digital e Prescrição Remota — Care Plus / Bupa.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange)](https://langchain-ai.github.io/langgraph/)
[![Sprint 2](https://img.shields.io/badge/Sprint%202-conclu%C3%ADda-success)]()

> ⚠️ Protótipo acadêmico (FIAP — Prompt Engineering and AI). Não substitui consulta médica. Toda prescrição passa por validação humana obrigatória (HITL).

---

## Sumário

1. [O que é](#o-que-é)
2. [Arquitetura](#arquitetura)
3. [Como executar](#como-executar)
4. [Estrutura do repositório](#estrutura-do-repositório)
5. [Bônus implementados](#bônus-implementados)
6. [Resultados dos evals](#resultados-dos-evals)
7. [Iterações de prompt](#iterações-de-prompt)
8. [Trade-offs e limitações](#trade-offs-e-limitações)
9. [Equipe](#equipe)

---

## O que é

Assistente de saúde para a operadora fictícia Care Plus, com duas capacidades:

- **Check-up Digital** — triagem clínica conversacional com sugestão de próximo passo (autocuidado, teleconsulta, urgência).
- **Prescrição Remota** — sugestão de prescrição estruturada para validação por médico humano.

### Princípios inegociáveis

| Princípio | Como é garantido |
|---|---|
| **HITL obrigatório** | Agente de prescrição sempre marca `requer_escalada_humana=True` e emite bloco JSON `<sugestao>` para revisão médica |
| **Pseudonimização** | IDs `BNF-XXXXX` — nenhum dado pessoal direto |
| **LGPD-by-design** | Opção de rodar com Ollama local (zero saída de dados do dispositivo) |
| **Red flag = escalada imediata** | Detecção rule-based curto-circuita o supervisor para SAMU 192 / CVV 188 |
| **Defesa em profundidade** | Guardrails em 3 camadas: moderação anti-jailbreak → red flags → escopo |

---

## Arquitetura

Sistema multi-agente em LangGraph com 5 agentes especializados.

```
                          START
                            │
                            ▼
              ┌──────────────────────────┐
              │       SUPERVISOR          │
              │  1. Moderação (jailbreak) │
              │  2. Red flag (rule + LLM) │
              │  3. Escopo (rule + LLM)   │
              │  4. Regras de intent      │
              │  5. LLM classifier        │
              └──────────────────────────┘
                            │
              (conditional edge: route)
                            │
        ┌──────────┬────────┴────────┬──────────────┐
        ▼          ▼                 ▼              ▼
   ┌─────────┐ ┌──────────┐  ┌─────────────┐ ┌──────────────┐
   │ TRIAGEM │ │PRESCRIÇÃO│  │   ESCALADA  │ │ FORA-ESCOPO  │
   │tool loop│ │tool loop │  │ template    │ │ template     │
   │  + RAG  │ │+ HITL    │  │determinístico│ │determinístico│
   └─────────┘ └──────────┘  └─────────────┘ └──────────────┘
```

Diagrama detalhado e narrativa em [`docs/relatorio_final.pdf`](docs/relatorio_final.pdf).

### Stack

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Orquestração | LangGraph + MemorySaver | Grafo auditável, suporte multi-turno |
| LLM nuvem | Groq Llama 3.1 8B Instant | Latência baixa, tier gratuito generoso |
| LLM local | Ollama + Llama 3.2 3B | Conformidade LGPD (on-premise) |
| RAG | ChromaDB + sentence-transformers | Vetorização local, embeddings multilíngues PT-BR |
| Testes | pytest | 92 testes determinísticos em 4s |
| Observabilidade | LangSmith + tracer JSONL próprio | SaaS + local em camadas |
| Interface | Streamlit | Demo com painel de observabilidade |

---

## Como executar

### Pré-requisitos

- Python 3.11+
- Conta Groq com API key ([console.groq.com/keys](https://console.groq.com/keys))
- Opcional: Ollama instalado ([ollama.com](https://ollama.com)) para modo LGPD

### Instalação

```bash
git clone https://github.com/lincoln743/bluadiagnostics.git
cd bluadiagnostics
git checkout sprint2

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt

cp .env.example .env
# Edite .env e cole sua GROQ_API_KEY real
```

### 1. Popular o vector store (RAG)

```bash
python -m src.rag.ingest
```

Lê `data/knowledge_base/*.md` e persiste em `data/chroma_db/` (82 chunks, 5 KBs).

> 💡 **Primeira execução demora ~30-60s** — o módulo baixa o modelo de embeddings `paraphrase-multilingual-MiniLM-L12-v2` (~118 MB) na primeira vez. Execuções seguintes são instantâneas (modelo cacheado em `~/.cache/huggingface/`).

### 2. Rodar a interface Streamlit

```bash
bash scripts/launch_ui.sh
```

Ou diretamente:

```bash
streamlit run src/ui/app.py
```

Abre em `http://localhost:8501`. Para parar: `Ctrl+C`.

### 3. Rodar os testes

```bash
pytest tests/                  # 92 testes
pytest --cov=src tests/        # com cobertura
```

### 4. Rodar a suite de evals

```bash
bash scripts/run_evals.sh              # ambos (Sprint 1 + Sprint 2 + comparativo)
bash scripts/run_evals.sh --sprint2    # só Sprint 2 (mais rápido, ~3 min)
bash scripts/run_evals.sh --sprint1    # só Sprint 1 (LLM-as-judge, ~5-8 min)
```

Resultados oficiais preservados em `evals/results_oficiais/`.

### 5. (Opcional) Modo Ollama local — conformidade LGPD

Em outro terminal:

```bash
ollama serve
ollama pull llama3.2:3b
```

No `.env`, ative:

```bash
LLM_PROVIDER=ollama
```

E reinicie o Streamlit. O sistema passa a rodar 100% local — dados nunca saem do dispositivo.

### 6. (Opcional) Ativar observabilidade LangSmith

No `.env`, adicione:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<sua_key>
LANGCHAIN_PROJECT=bluadiagnostics-sprint2
```

Crie a key gratuita em [smith.langchain.com](https://smith.langchain.com). Quota: 5k traces/mês.

---

## Estrutura do repositório

```
bluadiagnostics/
├── README.md
├── requirements.txt
├── pytest.ini
├── .env.example
├── entrega_sprint2.txt              # documento de entrega
├── src/
│   ├── config.py                    # leitura de env vars (load_dotenv)
│   ├── agents/
│   │   ├── supervisor.py            # classificação híbrida em 5 etapas
│   │   ├── triagem.py               # tool loop + detector de tool leak
│   │   ├── prescricao.py            # tool loop + saída JSON estruturada
│   │   ├── escalada.py              # template determinístico (SAMU/CVV)
│   │   └── fora_escopo.py           # template determinístico
│   ├── tools/                       # 5 tools com function calling
│   │   ├── consultar_historico.py
│   │   ├── verificar_interacoes.py
│   │   ├── agendar_teleconsulta.py
│   │   ├── consultar_wearables.py   # BÔNUS Apple HealthKit
│   │   ├── buscar_conhecimento.py   # RAG como tool
│   │   └── __init__.py              # registry + dispatch
│   ├── guardrails/
│   │   ├── moderation.py            # anti-jailbreak (6 categorias)
│   │   ├── red_flags.py             # rule + LLM (8 categorias)
│   │   └── scope.py                 # rule + LLM
│   ├── rag/
│   │   ├── ingest.py
│   │   └── retriever.py
│   ├── graph/
│   │   ├── state.py                 # BluaState TypedDict
│   │   └── builder.py               # StateGraph + invoke_with_message
│   ├── prompts/
│   │   └── system_prompts.py        # versionados como código
│   ├── providers/
│   │   └── llm_provider.py          # GroqProvider + OllamaProvider + factory
│   ├── observability/
│   │   ├── tracer.py                # JSONL local (11 event types)
│   │   └── langsmith_config.py      # SaaS via env vars
│   └── ui/
│       └── app.py                   # Streamlit
├── data/
│   ├── knowledge_base/              # 5 documentos clínicos
│   └── chroma_db/                   # vector store (gerado)
├── evals/
│   ├── sprint1_eval_set.json        # 12 casos (rubrica qualitativa)
│   ├── sprint2_eval_set.json        # 8 casos (checks programáticos)
│   ├── runner.py                    # runner unificado (2 modos)
│   └── results_oficiais/            # resultados finais preservados
├── tests/                           # 92 testes pytest
├── scripts/
│   ├── launch_ui.sh
│   ├── run_evals.sh
│   ├── run_tests.sh
│   └── test_langsmith.py
└── docs/
    ├── relatorio_final.pdf          # 18 páginas, ABNT (capa + folha de rosto)
    ├── relatorio_final.md           # fonte markdown
    ├── relatorio_corpo.md           # corpo sem cabeçalho (regeração PDF)
    ├── template_abnt.tex            # template LaTeX
    ├── roteiro_video.md             # roteiro de demonstração
    ├── observabilidade.md
    ├── ollama_lgpd.md
    ├── evals_methodology.md
    └── evals_iteracoes.md           # log de auditoria das iterações
```

---

## Bônus implementados

Todos os 5 bônus do briefing implementados e validados.

| Bônus | Status | Como verificar |
|---|---|---|
| **3+ agentes especializados** | ✅ 5 agentes | `src/agents/` + diagrama acima |
| **Wearables (Apple HealthKit)** | ✅ | `src/tools/consultar_wearables.py` |
| **Ollama local — LGPD** | ✅ | `LLM_PROVIDER=ollama` no `.env` + `docs/ollama_lgpd.md` |
| **Testes unitários pytest** | ✅ 92 testes | `pytest tests/` (4s, cobertura 52%) |
| **Observabilidade LangSmith** | ✅ | `LANGCHAIN_TRACING_V2=true` + `docs/observabilidade.md` |

---

## Resultados dos evals

Sistema avaliado em duas camadas: **rubrica qualitativa** (Sprint 1, LLM-as-judge com fallback determinístico para conteúdo sensível) e **checks programáticos** (Sprint 2, assertions sobre estado final do grafo).

### Acurácia global

| Suite | Modo | Acertos | Acurácia |
|---|---|---|---|
| Sprint 1 | Rubrica + fallback red flag | 11 / 12 | **91,7%** |
| Sprint 2 | Programático | 6 / 8 | **75,0%** |

### Sprint 1 — por categoria

| Categoria | Aprovados | Acurácia |
|---|---|---|
| **red_flag** (IAM, AVC, ideação suicida) | 3 / 3 | **100%** |
| **jailbreak** | 3 / 3 | **100%** |
| **out_of_scope** | 2 / 2 | **100%** |
| happy_path | 3 / 4 | 75% |

### Sprint 2 — por categoria

| Categoria | Aprovados | Acurácia |
|---|---|---|
| bonus_wearables | 1 / 1 | 100% |
| hitl | 1 / 1 | 100% |
| routing_correto | 2 / 3 | 67% |
| rag_recall | 2 / 3 | 67% |

**Destaque**: 100% de acurácia nos critérios de segurança crítica (red flags, jailbreaks, fora-de-escopo). Os fails residuais concentram-se em RAG recall e invocação proativa de tools — limitações reconhecidas e documentadas em `docs/evals_iteracoes.md`, não falhas de segurança.

JSONs completos em [`evals/results_oficiais/`](evals/results_oficiais/).

---

## Iterações de prompt

| Versão | Mudança | Motivação |
|---|---|---|
| v1.0 | Baseline Sprint 1 (system prompt monolítico) | Ponto de partida |
| v1.1 | Bloqueio anti-vazamento de tool syntax + instrução de query reformulation no RAG | Llama 3.1 8B vazava `nome_tool{...}</function>` como texto |
| v1.2 | Detector regex de vazamento + retry com aviso explícito + sanitizer | Defesa em profundidade |
| v1.3 | Scope ampliado com sintomas constitucionais (cansaço, fadiga, ansiedade, estresse) | Bug descoberto em eval: "cansada" classificado como fora-de-escopo |

Log completo de iterações do eval set em [`docs/evals_iteracoes.md`](docs/evals_iteracoes.md) — cada ajuste com justificativa clínica/técnica.

---

## Trade-offs e limitações

Discutidos em profundidade no [`docs/relatorio_final.pdf`](docs/relatorio_final.pdf). Resumo:

- **Tamanho do eval set (20 casos)**: insuficiente para inferência estatística rigorosa. Próximo passo é expandir para 100+ casos.
- **Viés do LLM-as-judge**: usar o mesmo modelo como juiz e como sistema introduz viés. Trabalho futuro deve usar modelo distinto (ex: GPT-4o) como juiz.
- **RAG recall (67%)**: estratégia de RAG-como-ferramenta deixa a recuperação dependente da query formulada pelo LLM. Mantida visível nos resultados em vez de mascarada.
- **Latência do Ollama local**: 30-118x mais lento que Groq em CPU. Inviável como padrão; requer GPU para produção.
- **Function calling em modelo 8B**: o Llama 3.1 8B não invoca tools com a confiabilidade de modelos maiores. Mitigado com detector de vazamento + retry + sanitizer.

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

Mantenedor: [@lincoln743](https://github.com/lincoln743) · lincoln743@gmail.com

---

## Licença

Projeto acadêmico — uso educacional. Care Plus, Bupa e marcas associadas pertencem a seus respectivos titulares.
