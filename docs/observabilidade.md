# 🔭 Observabilidade do BluaDiagnostics

> Documento técnico de apoio para o relatório final (Dia 12).

## Arquitetura em duas camadas

O BluaDiagnostics implementa observabilidade em **camadas complementares**, cada uma adequada a um caso de uso:

```
┌──────────────────────────────────────────────────────────────┐
│  LangSmith (SaaS)         ←  Dashboard, alertas, eval suites │
│  Tracing automático       ←  Tokens, latência, custo agregado│
│  https://smith.langchain.com                                 │
├──────────────────────────────────────────────────────────────┤
│  Tracer JSONL (local)     ←  Debug, replay, evals offline    │
│  src/observability/tracer.py                                 │
│  logs/traces/{thread_id}_{date}.jsonl                        │
├──────────────────────────────────────────────────────────────┤
│  LangGraph + Agentes      ←  Lógica de negócio               │
└──────────────────────────────────────────────────────────────┘
```

## Camada 1 — Tracer JSONL local (Dia 8)

**Implementação**: `src/observability/tracer.py`.

**Características**:
- **Zero dependência externa** (apenas stdlib)
- **Append-only JSONL** — 1 evento = 1 linha
- **Thread-safe** com lock interno
- **Auto-flush** para disco (sobrevive a crash)
- **Consumível pela UI** em tempo real

**Eventos registrados (11 tipos)**:

| Event type | Origem | Uso |
|---|---|---|
| `conversation_started` | criação do tracer | header do arquivo |
| `user_message` | usuário envia | indexa conversa |
| `supervisor_decision` | classificação | analisa precisão do supervisor |
| `moderation_blocked` | jailbreak | métricas de segurança |
| `red_flag_detected` | red flag rule/LLM | métricas clínicas críticas |
| `agent_invoked` | nó do grafo executa | trajetória |
| `tool_called` | function call | uso de ferramentas |
| `rag_retrieved` | RAG retorna chunks | qualidade do retrieval |
| `response_generated` | resposta final | latência E2E, tamanho |
| `provider_changed` | toggle Groq/Ollama | rastreabilidade LGPD |
| `error` | exceção capturada | diagnóstico |

**Formato**:
```json
{"timestamp":"2026-05-18T22:01:01.234Z","thread_id":"ui-abc123","turno":1,"event_type":"tool_called","data":{"tool":"consultar_historico_paciente","args":{"paciente_id":"BNF-04821"},"result_status":"success","result_summary":"ok — Maria"}}
```

**Vantagens**:
- Sem custo, sem rate limit
- Funciona offline (importante para Ollama LGPD on-premise)
- Análise rápida com `jq` ou `grep` na CLI
- Base para evals do Dia 10

## Camada 2 — LangSmith SaaS (Dia 9)

**Implementação**: `src/observability/langsmith_config.py`.

**Ativação**: configurar 3 env vars em `.env`:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=bluadiagnostics-sprint2
```

**Como funciona**: LangChain e LangGraph têm **instrumentação automática**. Cada `graph.invoke()` envia spans para o endpoint do LangSmith sem alterações no código de negócio.

**Trace tree típico de um turno**:
```
graph.invoke (root span)                          5.2s
├── supervisor_node                               0.8s
│   ├── moderation.moderar                        <0.01s
│   ├── red_flags.detectar (rule)                 <0.01s
│   ├── scope.validar_escopo (rule)               <0.01s
│   └── ChatGroq (classificação intent)           0.7s · 91 tok
├── triagem_node                                  4.3s
│   ├── ChatGroq (turno 1 — pede tools)           1.1s · 380 tok
│   ├── consultar_historico_paciente              <0.01s
│   ├── ChatGroq (turno 2 — resposta final)       3.0s · 520 tok
│   └── _detectar_vazamento                       <0.01s
└── END
```

**Vantagens**:
- Visualização de árvore navegável
- Custo estimado em USD por trace
- Filtro por intent, agente, latência
- Exporta datasets para evals oficiais LangSmith
- Compartilhável com avaliadores via URL pública

**Trade-off**:
- Requer conexão internet
- Dados trafegam para US (incompatível com LGPD strict)
- Quota gratuita: 5k traces/mês (suficiente para Sprint 2 + demo)

## Quando usar cada camada

| Cenário | JSONL local | LangSmith |
|---|---|---|
| Demo / desenvolvimento local | ✅ | ✅ |
| Debug de bug específico | ✅ replay direto | ⚠️ dependência rede |
| Análise de tendência semanal | ⚠️ grep manual | ✅ dashboards |
| Auditoria LGPD on-prem | ✅ | ❌ não compliant |
| Eval automatizado batch (Dia 10) | ✅ parser direto | ✅ datasets nativos |
| Compartilhamento com avaliador | ⚠️ arquivos crus | ✅ link público |

A **arquitetura em camadas** é o argumento técnico forte para o relatório:
> "Observabilidade local atende auditoria LGPD; LangSmith complementa para análise agregada e compartilhamento. Ambas são alimentadas pelo mesmo modelo de eventos — JSONL é fonte de verdade exportável."

## Smoke test de validação

`scripts/test_langsmith.py` envia 3 cenários determinísticos pelo grafo e instrui o usuário a verificar no dashboard. Cenários cobrem:

1. **Escalada cardiovascular** (rule-based, sem LLM) — valida que rule-based também gera trace
2. **Fora de escopo** (rule-based) — valida moderação/scope no LangSmith
3. **Triagem com tool loop** (LLM + tools) — valida trace completo

Após rodar, abrir o dashboard `https://smith.langchain.com/o/-/projects/p/bluadiagnostics-sprint2` para inspecionar os 3 traces gerados.

## Próximos passos (Dia 10 — Evals)

Os mesmos traces serão a base para o sistema de evals:
- Carregar conjunto de N casos pré-definidos
- Rodar via grafo gerando traces JSONL + LangSmith
- Cálculo de métricas agregadas: accuracy de intent, F1 de red flag, latência p50/p95, custo médio
