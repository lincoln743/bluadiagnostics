# 📅 Plano de Execução — Sprint 2 (14 dias)

> Cronograma realista para entregar TODOS os 5 bônus em 2 semanas.
> Data início: 10/05/2026 · Data entrega estimada: 24/05/2026

## Visão geral

| Semana | Foco | Dias |
|---|---|---|
| **1** | Núcleo funcional (RAG + agentes + tools + guardrails + Ollama + testes) | 1-7 |
| **2** | Qualidade + entregáveis (UI + obs + evals + vídeo + relatório + PDF) | 8-14 |

---

## Semana 1 — Núcleo funcional

### Dia 1 (segunda) — Fundação
- [ ] Criar branch `sprint2` no repo
- [ ] Extrair scaffold ZIP
- [ ] Copiar 5 docs da KB para `data/knowledge_base/`
- [ ] `bash scripts/setup_local.sh`
- [ ] Validar: `python -c "from src.config import settings; settings.validate()"`
- [ ] Primeiro commit do scaffold

**Entregável**: repo Sprint 2 com estrutura completa, ambiente funcional.

### Dia 2 — RAG (parte 1)
- [ ] Implementar `src/rag/ingest.py`
- [ ] Implementar `src/rag/retriever.py`
- [ ] Implementar tool `src/tools/buscar_conhecimento.py`
- [ ] Notebook `notebooks/rag_validation.ipynb`: validar retrieval em 5 queries de sanity check

**Entregável**: ChromaDB populado, queries retornando chunks corretos.

### Dia 3 — Multi-agente (parte 1)
- [ ] Implementar `src/graph/state.py` (TypedDict BluaState)
- [ ] Implementar `src/agents/supervisor.py`
- [ ] Implementar `src/prompts/system_prompts.py` (versão inicial)
- [ ] Testar roteamento isolado (sem grafo ainda)

**Entregável**: classificação de intent funcionando em testes isolados.

### Dia 4 — Multi-agente (parte 2)
- [ ] Implementar `src/agents/triagem.py`
- [ ] Implementar `src/agents/prescricao.py` (com interrupt_before)
- [ ] Implementar `src/agents/escalada.py`
- [ ] Implementar `src/graph/builder.py` (junta tudo)
- [ ] Notebook `notebooks/sprint2_demo.ipynb`: smoke test end-to-end

**Entregável**: grafo completo rodando, 4 agentes orquestrados.

### Dia 5 — Tools + Guardrails
- [ ] Implementar 3 tools clássicas: `consultar_historico`, `verificar_interacoes`, `agendar_teleconsulta`
- [ ] Implementar tool BÔNUS: `consultar_wearables` + `data/mock_wearables.json`
- [ ] Implementar `src/guardrails/red_flags.py`
- [ ] Implementar `src/guardrails/scope.py`
- [ ] Implementar `src/guardrails/moderation.py`
- [ ] Integrar guardrails no supervisor

**Entregável**: 5 tools + 3 guardrails operacionais.

### Dia 6 — Ollama (BÔNUS LGPD)
- [ ] Implementar `src/providers/llm_provider.py` (abstração Groq/Ollama)
- [ ] Refatorar agentes para usar o factory
- [ ] Instalar Ollama no T430u
- [ ] `ollama pull llama3.2:3b`
- [ ] Validar fluxo completo com `LLM_PROVIDER=ollama`

**Entregável**: sistema funcional em modo 100% local.

### Dia 7 — Testes unitários (BÔNUS)
- [ ] `tests/test_tools.py` — cobrir todas as 5 tools
- [ ] `tests/test_guardrails.py` — red flags, scope, moderation
- [ ] `tests/test_prompts.py` — testes de regressão (LLM-based)
- [ ] Atingir cobertura ≥ 70% em `src/tools/` e `src/guardrails/`
- [ ] CI básico (opcional, `.github/workflows/tests.yml`)

**Entregável**: suite de testes rodando, cobertura documentada.

---

## Semana 2 — Qualidade + entregáveis

### Dia 8 — Streamlit + Observabilidade (parte 1)
- [ ] Implementar `app/streamlit_app.py`
- [ ] Painel lateral: trajetória de agentes + docs RAG + tools
- [ ] Botão reset, seletor de paciente
- [ ] Implementar `src/observability/tracing.py` (logs JSONL)

**Entregável**: app rodando localmente em `localhost:8501`.

### Dia 9 — Observabilidade (parte 2 — BÔNUS)
- [ ] Criar conta LangSmith (free tier)
- [ ] Configurar env vars
- [ ] Validar traces aparecendo no dashboard
- [ ] Polir Streamlit (CSS, ícones, badges coloridos por agente)

**Entregável**: traces no LangSmith capturáveis para o vídeo.

### Dia 10 — Evals
- [ ] Implementar `evals/runner.py`
- [ ] Rodar suite completa (12 casos Sprint 1 + 8 novos = 20)
- [ ] Gerar `evals/sprint2_results.json`
- [ ] Gerar gráficos matplotlib (acurácia por categoria, tempo, etc.)
- [ ] Análise crítica: quais casos falharam e por quê
- [ ] Iterar prompts 1-2 vezes baseado nos achados

**Entregável**: relatório de evals com gráficos + iterações documentadas no README.

### Dia 11 — Vídeo de demonstração
- [ ] Roteiro de 5 min cobrindo TODOS os requisitos do briefing:
  - Check-up digital completo (Maria com sintoma leve)
  - RAG retornando docs (mostrar painel lateral)
  - ≥ 2 tools sendo chamadas
  - Red flag com escalada (dor torácica → SAMU)
  - Jailbreak bloqueado
  - LangSmith trace (bônus)
  - Modo Ollama local (bônus)
- [ ] Gravar com OBS Studio
- [ ] Editar (cortes, zoom, legendas)
- [ ] Upload YouTube **não listado**

**Entregável**: link YouTube não listado.

### Dia 12 — Relatório técnico
- [ ] Escrever `docs/relatorio_final.md`:
  - Introdução (problema + contexto Care Plus)
  - Arquitetura final
  - Decisões técnicas e trade-offs
  - Resultados dos evals (com gráficos)
  - Bônus implementados
  - Limitações conhecidas
  - Roadmap para produção
- [ ] Revisão por pelo menos 1 integrante do grupo

**Entregável**: relatório markdown completo.

### Dia 13 — PDF ABNT
- [ ] Reusar template LaTeX da Sprint 1
- [ ] Converter `relatorio_final.md` → estrutura ABNT
- [ ] Capa, folha de rosto, resumo, sumário, seções, referências
- [ ] Gerar PDF com `pdflatex`

**Entregável**: `docs/relatorio_final.pdf` em padrão ABNT.

### Dia 14 — Entrega + buffer
- [ ] Última passada: testes, README, links
- [ ] Validar repo público + branch sprint2 acessível
- [ ] Confirmar vídeo "não listado"
- [ ] Confirmar links do relatório (markdown + PDF)
- [ ] Criar arquivo `entrega_sprint2.txt` com:
  - Nome + RM dos 4 integrantes
  - Link repo + branch
  - Link vídeo YouTube
  - Link relatório (markdown + PDF)
- [ ] Submeter no portal FIAP

**Entregável**: `entrega_sprint2.txt` submetido.

---

## Buffers e riscos

| Risco | Mitigação |
|---|---|
| Ollama travar no T430u | Plano B: usar somente Groq, justificativa LGPD ainda válida no relatório |
| Limite de tokens Groq 8B (500k/dia) durante evals | Cache de respostas + rodar em batch noturno |
| Vídeo passar de 5 min | Roteirizar antes de gravar, cronometrar |
| LaTeX dar problema com encoding | Fallback: gerar PDF via pandoc (md → PDF direto) |
| Lincoln viajar / ficar sem tempo | Cada bloco é independente — outro integrante pode pegar |

---

## Checklist de "definition of done" final

Antes de submeter, **TUDO** abaixo deve estar ✅:

- [ ] Repo público, branch `sprint2` acessível
- [ ] README com diagrama, instruções, evals, iterações
- [ ] Sistema roda end-to-end com `streamlit run app/streamlit_app.py`
- [ ] `blua-ingest` popula vector store sem erro
- [ ] `blua-eval` gera `sprint2_results.json`
- [ ] `pytest tests/` passa
- [ ] **NENHUMA API key no histórico git** (verificar com `git log -p | grep -i "gsk_\|sk-\|api.key" | head`)
- [ ] Vídeo YouTube **não listado** (NÃO público, NÃO privado)
- [ ] Vídeo ≤ 5 min
- [ ] Relatório markdown + PDF ABNT
- [ ] `entrega_sprint2.txt` com 4 nomes+RM, link repo, link vídeo, link relatório
- [ ] Professor Jorge tem acesso ao repo (público resolve)
