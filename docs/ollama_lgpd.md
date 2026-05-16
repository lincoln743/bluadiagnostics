# 🔒 Modelo Local (Ollama) — Justificativa LGPD

> Documento técnico de apoio para o relatório final da Sprint 2.

## Contexto regulatório

A **Lei Geral de Proteção de Dados (LGPD — Lei 13.709/2018)** classifica dados de saúde como **dados pessoais sensíveis** (Art. 5º, II). Para operadoras de saúde como a Care Plus, isso impõe obrigações específicas:

| Princípio LGPD | Implicação técnica |
|---|---|
| **Minimização** (Art. 6º, III) | Só processar o estritamente necessário |
| **Adequação** (Art. 6º, II) | Tratamento compatível com finalidades informadas |
| **Necessidade** (Art. 6º, III) | Limitação ao indispensável |
| **Transparência** (Art. 6º, VI) | Beneficiário deve saber onde os dados trafegam |
| **Segurança** (Art. 6º, VII) | Medidas técnicas contra acesso não autorizado |

Quando o LLM roda em **API de terceiros (cloud)**, dados clínicos pseudonimizados trafegam para infraestrutura externa. Mesmo com TLS e contratos de processamento, há:
- Risco de breach no provider externo
- Dependência de jurisdição estrangeira (provider USA → CLOUD Act)
- Necessidade de DPA (Data Processing Agreement) específico

## Arquitetura híbrida implementada

O BluaDiagnostics suporta **dois providers de LLM** controlados por variável de ambiente `LLM_PROVIDER`:

```
LLM_PROVIDER=groq      # Default — cloud Groq (Llama 3.1 8B)
LLM_PROVIDER=ollama    # On-premise — Ollama (Llama 3.2 3B)
```

### Provider Groq (default)

- **Vantagens**: latência <2s, qualidade alta, function calling robusto, escala
- **Limitações LGPD**: dados pseudonimizados (não dados pessoais diretos) ainda trafegam para servidores Groq (EUA). Em contexto Care Plus, exige consentimento informado conforme Art. 7º, V.

### Provider Ollama (on-premise)

- **Vantagens LGPD**:
  - Dados nunca saem do dispositivo / rede local da operadora
  - Compatibilidade com Wi-Fi hospitalar controlado
  - Zero dependência de jurisdição estrangeira
  - Atende princípio de adequação (Art. 6º, II) para cenários sensíveis
- **Trade-offs técnicos**:
  - Latência 10-30x maior em CPU (testado em ThinkPad T430u: 30-50s/resposta)
  - Modelos 3B têm function calling menos confiável que 8B
  - Requer infraestrutura local de inferência

## Cenários de aplicação real

Em uma implementação produtiva do BluaDiagnostics, o provider seria escolhido **por tenant**:

| Cenário | Provider recomendado | Justificativa |
|---|---|---|
| App Blua público (B2C) | **Groq** | Latência crítica, consentimento explícito no app |
| Plataforma corporate Care Plus B2B | **Híbrido** | Cliente escolhe via contrato |
| Implantação hospitalar | **Ollama on-premise** | Wi-Fi controlado + DPO exige local |
| Auditoria / desenvolvimento | **Ollama** | Sem custo + sem trânsito de dados |

## Implementação

O módulo `src/providers/llm_provider.py` implementa a abstração `LLMProvider` com dois backends:

- `GroqProvider` — SDK oficial Groq + retry exponencial em rate limit
- `OllamaProvider` — SDK OpenAI apontando para `localhost:11434/v1` (Ollama é compatível com Chat Completions API) + retry em timeout

A factory `get_provider()` retorna a instância correta baseada em `settings.llm_provider`. Os agentes (`triagem_node`, `prescricao_node`, etc.) consomem a abstração sem saber qual backend está ativo — princípio de inversão de dependência.

## Validação experimental

Script `scripts/ollama_smoke.py` executa 4 cenários comparativos:
1. Classificação de intent
2. Orientação clínica curta
3. Recusa de off-topic
4. Resposta em PT-BR

Resultados típicos no T430u (i5 3ª geração, 16GB RAM):

| Cenário | Groq Llama 3.1 8B | Ollama Llama 3.2 3B |
|---|---|---|
| Latência média | 1.2s | 38s |
| Qualidade (match esperado) | 4/4 | 3-4/4 |
| Tokens/segundo | ~180 | ~5 |
| Custo por chamada | $0 (free tier) | $0 (CPU local) |

## Conclusão

A arquitetura híbrida permite que o BluaDiagnostics seja **deployable em qualquer contexto regulatório**, do mais permissivo (B2C com consentimento) ao mais restritivo (hospital com dados clínicos completos). A LGPD é tratada **como requisito técnico** da arquitetura — não como item de compliance reativo.
