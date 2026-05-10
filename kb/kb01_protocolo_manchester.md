# KB01 — Protocolo de Triagem de Manchester (Simplificado)

> **Fonte adaptada:** MACKWAY-JONES, K.; MARSDEN, J.; WINDLE, J. *Sistema Manchester de Classificação de Risco*. 3. ed. Belo Horizonte: GBCR, 2018.
> **Uso:** triagem preliminar do BluaDiagnostics. Não substitui avaliação clínica.

## Visão Geral

O Protocolo de Manchester classifica pacientes em 5 níveis de prioridade conforme a gravidade clínica, baseado em discriminadores e tempo máximo recomendado para atendimento.

## Os 5 Níveis

| Cor | Nível | Tempo máx. atendimento | Significado |
|---|---|---|---|
| 🔴 Vermelho | Emergência | Imediato (0 min) | Risco iminente de morte |
| 🟠 Laranja | Muito urgente | 10 min | Risco significativo |
| 🟡 Amarelo | Urgente | 60 min | Pode aguardar com monitoramento |
| 🟢 Verde | Pouco urgente | 120 min | Estado estável |
| 🔵 Azul | Não urgente | 240 min | Sintoma leve, eletivo |

## Discriminadores Gerais (resumo)

### Vermelho — encaminhar imediatamente para PS / 192

- Via aérea comprometida (sufocamento, anafilaxia)
- Respiração inadequada (apneia, dispneia grave com cianose)
- Choque (hipotensão grave, palidez, sudorese, alteração de consciência)
- Hemorragia exsanguinante (não controlada com pressão)
- Convulsão ativa
- Dor torácica cardíaca (ver KB05)
- Sinais de AVC com início < 4h30 (janela de trombólise)
- Glasgow ≤ 8

### Laranja — encaminhar para PS em até 10 min

- Dor severa (8-10/10)
- Hipoglicemia sintomática
- Sangramento moderado a grave não controlado
- Febre alta com sinais de toxemia
- Trauma com mecanismo de alta energia
- Alteração súbita de comportamento

### Amarelo — teleconsulta urgência=imediata ou hoje

- Dor moderada (4-7/10)
- Vômitos persistentes
- História recente de inconsciência (já recuperado)
- Febre ≥ 38,5°C sem sinais de toxemia
- Dor abdominal sem sinais de abdome agudo

### Verde — teleconsulta em até 24-48h

- Sintomas leves a moderados estáveis
- Cefaleia leve a moderada
- Tosse / coriza sem dispneia
- Lesões superficiais

### Azul — agendamento de rotina

- Renovação de receita controlada
- Dúvidas administrativas
- Resultados de exames de rotina

## Aplicação no BluaDiagnostics

| Manchester | nivel_urgencia BluaDiagnostics | Ação |
|---|---|---|
| Vermelho | `critico` | 192/SAMU + escalada_humana=true |
| Laranja | `alto` | Teleconsulta urgência=imediata |
| Amarelo | `moderado` | Teleconsulta urgência=hoje ou 24h |
| Verde | `baixo` | Teleconsulta urgência=24h ou rotina |
| Azul | `baixo` | Agendamento rotina ou autoatendimento |

## Limitações

- Triagem por sintomas relatados, sem exame físico nem exames complementares.
- Em caso de dúvida, **sempre** subir o nível de urgência (princípio da prudência).
- Nunca dispensar atendimento humano apenas com base nesta classificação.
