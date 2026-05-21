# 📊 Metodologia de Avaliação Automatizada

> Documento técnico de apoio para o relatório final (Dia 12).

## Visão geral

O BluaDiagnostics implementa um sistema de **avaliação automatizada em dois modos complementares**, refletindo a natureza híbrida do produto (lógica determinística + agentes LLM).

```
┌──────────────────────────────────────────────────────────────┐
│  Eval Suite                                                  │
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  Sprint 1 (12)      │    │  Sprint 2 (8)               │ │
│  │  Modo: rubrica      │    │  Modo: programático         │ │
│  │  Judge: LLM         │    │  Judge: assertions          │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                              │
│  ► evals/runner.py — runner unificado                        │
│  ► evals/results/ — JSON com timestamp por run               │
└──────────────────────────────────────────────────────────────┘
```

## Modo 1 — Avaliação Programática (Sprint 2)

**Filosofia**: cada caso tem `expected` com checks **determinísticos** que podem ser verificados sem necessidade de julgamento humano ou LLM.

**Checks suportados**:

| Check | Valida |
|---|---|
| `agente_final` | Intent classificada corresponde ao agente correto |
| `deve_recuperar_kb` | RAG recuperou chunks da KB específica |
| `deve_chamar_tool` | Tool específica foi acionada |
| `deve_detectar_red_flag` | Red flag foi detectada (qualquer categoria) |
| `deve_mencionar` | Termos-chave presentes na resposta final |
| `requer_hitl` | Flag de escalada humana ativada |

**Score**: `(checks_aprovados / checks_total)`. Caso passa se score ≥ 0.8.

**Vantagens**:
- 100% reproduzível (zero variabilidade)
- Rápido (~5s por caso)
- Sem custo de LLM (exceto pelo grafo em si)
- Auditável linha por linha

**Limitações**:
- Não avalia qualidade conversacional (tom acolhedor, clareza)
- Não detecta hallucinations sutis
- Requer expected explícito (custo de manutenção)

## Modo 2 — Avaliação por Rubrica (Sprint 1) — LLM-as-Judge

**Filosofia**: alguns critérios são **qualitativos** ("tom acolhedor", "sem diagnóstico definitivo") e não podem ser checados com regex. Para esses, usamos um LLM separado como juiz.

**Processo**:
1. Roda o grafo → captura resposta final
2. Envia para um LLM em modo "judge" com:
   - Descrição do caso
   - Entrada do usuário
   - Resposta a avaliar
   - Lista de `criterios_avaliacao` (strings em português)
3. LLM retorna JSON com `{criterio, atendido: true|false, justificativa}` para cada critério
4. Score = `(criterios_atendidos / total_criterios)`

**Sobre o juiz**:
- Usa o mesmo provider configurado (Groq por default)
- Temperature 0.0 para reprodutibilidade
- Prompt instrui rigor mas justiça (não penaliza por vacuosidade)

**Vantagens**:
- Captura qualidade subjetiva
- Suporta critérios em linguagem natural (fácil expansão)
- Compatível com rubrica humana já existente

**Limitações conhecidas e mitigadas**:
- ⚠️ LLM-as-judge tem viés (modelo julgando saída do mesmo modelo)
  - Mitigação: temperatura 0 + prompt rigoroso + amostragem manual para spot-check
- ⚠️ Variabilidade entre execuções
  - Mitigação: rodar 3x e usar mediana para resultados oficiais

## Métricas computadas

Por cada eval run:

| Métrica | Tipo |
|---|---|
| `accuracy_global` | % de casos com score ≥ 0.8 |
| `por_categoria` | Accuracy + score médio segmentado |
| `latencia_p50_s` | Mediana de tempo por caso |
| `latencia_p95_s` | Cauda alta (95 percentil) |
| `duracao_total_s` | Tempo total da execução |

Resultados salvos em `evals/results/sprint{N}_results_{timestamp}.json`. Múltiplas execuções permitem **análise temporal** (regressões entre commits).

## Comparativo Sprint 1 vs Sprint 2

O runner suporta `--all` para rodar ambos os sets e produzir tabela comparativa lado a lado, evidenciando:

- **Evolução da accuracy** entre sprints
- **Diferença em latência** (Sprint 2 tem mais agentes + RAG)
- **Cobertura por categoria** (Sprint 1 = critérios qualitativos / Sprint 2 = checks específicos)

Esse comparativo é a evidência empírica central do relatório final: demonstrar que a Sprint 2 não regrediu nos casos antigos enquanto adicionou capacidades novas (RAG, multi-agente, HITL).

## Gestão de rate limit

Casos Sprint 1 + 2 totalizam ~20 mensagens, cada uma podendo gerar 2-5 chamadas LLM:
- ~40-100 chamadas LLM totais
- ~25.000 tokens consumidos por run completo

O tier free Groq tem limite de **6.000 tokens/minuto**. Para evitar erro 429:
- **Pausa de 3s entre casos** (configurável via `PAUSA_ENTRE_CASOS_S`)
- **Retry exponencial** já implementado no `GroqProvider` (Dia 4b)
- Modo `--rapido` para desenvolvimento (sem pausa, risco de rate limit)

## Reprodutibilidade

```bash
# Roda ambos os sets + comparativo
bash scripts/run_evals.sh

# Só Sprint 2 (rápido, ~3 min)
bash scripts/run_evals.sh --sprint2

# Sem pausa (desenvolvimento)
bash scripts/run_evals.sh --sprint2 --rapido
```

Todo resultado salvo em `evals/results/` com timestamp UTC, permitindo:
- Comparar runs ao longo do tempo
- Anexar JSONs específicos no relatório como evidência
- Integrar com CI (futuro: bloquear merge se accuracy cair)

## Limitações honestas

Toda metodologia tem limites — vale documentá-los:

1. **N pequeno (20 casos)**: estatística não-significativa para diferenças <10pp. Para inferência rigorosa, expandir para ~100 casos.
2. **Viés do LLM-judge**: usar modelo diferente do que gera resposta (ex: judge em GPT-4o, sistema em Llama 3.1) eliminaria o viés inter-modelo.
3. **Sem A/B test**: não rodamos versões antigas do prompt em paralelo. Comparações de "iteração de prompt" são longitudinais (commits antigos no git history).
4. **Dataset é o próprio designer**: casos foram escritos pela equipe — risco de underestimar edge cases reais (mitigado parcialmente por incluir 3 jailbreak + 2 fora-escopo).

## Próximos passos (pós-Sprint 2)

- Expandir para 50-100 casos cobrindo PT-BR regional, idioma misto, abreviações
- Integrar com LangSmith Datasets API para evals nativos do SaaS
- A/B test entre versões de prompt na mesma run
- Eval de tool-call F1 (precision/recall de invocação de tools)
