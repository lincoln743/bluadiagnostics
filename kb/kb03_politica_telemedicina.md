# KB03 — Política Care Plus de Telemedicina e Atendimento Remoto

> **Documento adaptado** das diretrizes Care Plus alinhadas à Resolução CFM 2.314/2022.
> **Versão:** 1.0 (Sprint 1 — simulação para fins acadêmicos).

---

## 1. Marco Regulatório

A telemedicina no Brasil é regulamentada pela **Lei 14.510/2022** e pela **Resolução CFM nº 2.314/2022**, que reconhecem como modalidades válidas:

- **Teleconsulta:** consulta médica realizada à distância.
- **Teleinterconsulta:** discussão de caso entre profissionais.
- **Telediagnóstico:** emissão de laudo à distância.
- **Telemonitoramento:** acompanhamento à distância de paciente em tratamento.
- **Teletriagem:** avaliação preliminar para definir necessidade de atendimento.

O **BluaDiagnostics atua na camada de teletriagem**, sem substituir teleconsulta nem realizar telediagnóstico.

## 2. Especialidades Cobertas pela Care Plus em Telemedicina

São oferecidas 8 especialidades 24/7 ou em horário estendido:

1. **Clínica Geral** — porta de entrada universal
2. **Pediatria** — pacientes 0-18 anos
3. **Ginecologia** — saúde da mulher
4. **Cardiologia** — acompanhamento cardiovascular
5. **Psiquiatria** — saúde mental
6. **Psicologia** — psicoterapia online
7. **Dermatologia** — avaliação de lesões com imagem
8. **Endocrinologia** — diabetes, tireoide, obesidade

Especialidades fora desta lista são encaminhadas para consulta presencial.

## 3. Janelas de Urgência Disponíveis

| Urgência | Tempo de espera máximo | Tipo de fluxo |
|---|---|---|
| `imediata` | 15 min | Sob demanda 24/7 |
| `hoje` | 4 horas | Encaixe no mesmo dia |
| `24h` | 24 horas | Próxima janela de 24h |
| `rotina` | Próximo horário disponível | Agendamento normal |

## 4. Limites Clínicos da Teleconsulta Care Plus

A teleconsulta **NÃO substitui** atendimento presencial nos seguintes casos:

- Emergências com risco iminente de vida (red flags — KB05)
- Procedimentos invasivos ou exame físico essencial
- Trauma significativo
- Sintomas neurológicos agudos (suspeita de AVC)
- Dor torácica de característica anginosa
- Sangramento ativo
- Crise hipertensiva sintomática
- Quadros psiquiátricos com risco iminente (encaminhamento CAPS/PS psiquiátrico)

Nestes casos, o BluaDiagnostics deve orientar **PA presencial** ou **192/SAMU** antes de qualquer agendamento remoto.

## 5. Prescrição via Telemedicina

Conforme CFM 2.314/2022:

- Prescrições por telemedicina têm **mesma validade** das presenciais.
- Devem ser emitidas em formato digital com **assinatura eletrônica qualificada** (ICP-Brasil).
- **Medicamentos sujeitos a controle especial** (Portaria 344/98 — Receitas Azul/Amarela) podem ser prescritos por telemedicina apenas em circunstâncias específicas e com retenção de receita pela farmácia.
- O **médico assume responsabilidade técnica** pela prescrição emitida em teleconsulta.

### Política Care Plus específica:

- Prescrição de antibióticos via telemedicina permitida apenas após avaliação médica em consulta.
- Renovação de receitas crônicas (anti-hipertensivos, antidiabéticos, etc.) permitida via telemedicina com paciente em acompanhamento prévio.
- **Controlados psicotrópicos** apenas com paciente já em acompanhamento na Care Plus, com história prévia documentada.

## 6. Papel do BluaDiagnostics no Fluxo de Prescrição

1. Beneficiário descreve sintomas → BluaDiagnostics realiza triagem.
2. Caso indicação seja de teleconsulta, agenda com a especialidade adequada.
3. **Médico** conduz a teleconsulta, anamnese, exame físico remoto e decide a conduta.
4. Em caso de prescrição, o **médico** emite a receita digital.
5. O BluaDiagnostics pode **validar** interações medicamentosas via tool `verificar_interacoes_medicamentosas` com `aprovado_por_medico=true` antes da emissão final.
6. **Em nenhuma hipótese** o BluaDiagnostics substitui o ato médico.

## 7. Consentimento e Privacidade

- O beneficiário deve **consentir** com a teleconsulta (consentimento registrado no app Blua).
- Dados clínicos são protegidos por LGPD (Art. 5º, II — dados sensíveis).
- O BluaDiagnostics opera com **paciente_id pseudonimizado**; nunca com CPF, nome, e-mail.
- Logs e métricas não armazenam PII.

## 8. Escalada para Atendimento Presencial

Quando o BluaDiagnostics ou o médico em teleconsulta identificarem necessidade de avaliação presencial:

- **Rede credenciada Care Plus**: encaminhar para PS, hospital ou clínica credenciada mais próxima.
- **Emergência absoluta**: 192 (SAMU).
- **Urgência psiquiátrica**: CAPS, hospital psiquiátrico credenciado, ou CVV (188) em ideação suicida.

## 9. Limites de Cobertura

- O plano cobre teleconsultas dentro do escopo contratado.
- Especialidades não previstas em telemedicina exigem consulta presencial (cobertura mantida pela rede credenciada).
- Não há cobertura para procedimentos não autorizados pelo plano.
