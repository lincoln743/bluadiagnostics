# KB05 — Red Flags Clínicas

> **Lista de sinais de alerta que exigem atendimento presencial imediato (PS) ou acionamento do SAMU (192).**
> **Documento de uso interno do BluaDiagnostics.** Em qualquer ocorrência destes sintomas, o agente DEVE marcar `nivel_urgencia=critico`, `escalada_humana=true` e orientar emergência antes de qualquer agendamento.

---

## 1. Cardiovasculares

### Síndrome Coronariana Aguda (Suspeita de IAM)

- Dor torácica intensa, opressiva, em aperto
- Irradiação para braço esquerdo, mandíbula, dorso ou epigástrio
- Duração > 20 min ou em repouso
- Acompanhada de: sudorese fria, náusea, falta de ar, mal-estar súbito
- **Maior risco em:** > 45 anos (homens) / > 55 anos (mulheres), hipertensos, diabéticos, dislipidêmicos, fumantes

**Conduta:** 192 imediatamente. Não dirigir sozinho. Não automedicar (NÃO orientar AAS por conta própria).

### Crise Hipertensiva Sintomática

- PA muito elevada (≥ 180×120 mmHg) com sintomas como dor de cabeça intensa, alterações visuais, dor torácica, dispneia ou alteração neurológica.

**Conduta:** PA / 192.

### Arritmia com sintomas

- Palpitação intensa associada a tontura, síncope, dor torácica ou dispneia.

## 2. Neurológicas

### AVC — Acidente Vascular Cerebral (mnemônico SAMU)

- **S**orriso assimétrico (desvio de comissura labial)
- **A**braço fraco (fraqueza em um lado do corpo, especialmente braço)
- **M**úsica/fala alterada (dificuldade súbita para falar ou entender)
- **U**rgência — ligar 192 imediatamente

**Janela terapêutica:** trombólise eficaz em até 4h30 do início dos sintomas; trombectomia mecânica em casos selecionados até 24h. **Tempo é cérebro.**

**Conduta crítica:** anotar **horário exato** de início; não dar comida/bebida; chamar 192.

### Convulsão

- Episódio convulsivo, especialmente o **primeiro** evento ou convulsão prolongada (>5 min) ou convulsões em série sem recuperação entre elas (estado de mal epiléptico).

### Cefaleia em Trovoada (Thunderclap)

- Dor de cabeça súbita, intensíssima ("a pior dor da vida"), atingindo pico em segundos.
- Pode indicar hemorragia subaracnoidea.

### Trauma Craniano

- Perda de consciência, mesmo breve
- Vômitos repetidos
- Confusão, sonolência, alteração comportamental
- Convulsão pós-trauma
- Sangramento por nariz/ouvidos

## 3. Respiratórias

### Dispneia Grave

- Falta de ar em repouso ou com esforço mínimo
- Cianose (lábios/dedos roxos)
- Esforço respiratório evidente, batimento de asas nasais (criança)
- SpO₂ < 92% (se medido)

### Anafilaxia

- Inchaço súbito de face, lábios, língua, garganta
- Urticária generalizada com falta de ar ou tontura
- Após exposição a alérgeno conhecido (alimento, medicamento, picada)

**Conduta:** 192. Se autoinjetor de epinefrina disponível, usar conforme prescrição prévia.

### Crise Asmática Grave

- Falta de ar que não melhora com broncodilatador habitual
- Dificuldade para falar frases completas
- Cianose, sonolência

## 4. Gastrointestinais e Abdominais

### Abdome Agudo

- Dor abdominal súbita, intensa, contínua
- Rigidez abdominal ("barriga em tábua")
- Vômitos persistentes, parada de eliminação de gases/fezes
- Sinais de choque

### Hemorragia Digestiva

- Vômito com sangue vivo ou em "borra de café"
- Fezes pretas (melena) ou com sangue vivo (hematoquezia) em volume significativo

## 5. Endócrino-metabólicas

### Hipoglicemia Grave

- Glicemia < 50-60 mg/dL com confusão, agitação, perda de consciência ou convulsão
- Comum em diabéticos em uso de insulina ou sulfonilureia

**Conduta:** se consciente, glicose oral; se inconsciente, **192**.

### Cetoacidose Diabética / Estado Hiperosmolar

- Diabético com hiperglicemia importante, vômitos, dor abdominal, hálito cetônico, sonolência.

## 6. Saúde Mental

### Ideação Suicida com Plano ou Risco Iminente

- Verbalização de planos concretos
- Acesso a meios (medicamentos, armas)
- Histórico de tentativa prévia recente
- Isolamento, despedidas, "deixar tudo em ordem"

**Conduta:**
1. Acolher com empatia, sem julgamento.
2. Não deixar a pessoa sozinha (se com cuidador presente).
3. Orientar **CVV — 188** (24h, gratuito).
4. **Risco iminente:** PS psiquiátrico ou 192.
5. Acionar `agendar_teleconsulta(especialidade=psiquiatria, urgencia=imediata)`.

### Surto Psicótico Agudo

- Alucinações, delírios, agitação, comportamento muito desorganizado
- Risco para si ou para terceiros

**Conduta:** PS / serviço psiquiátrico de urgência.

## 7. Obstétricas / Ginecológicas

### Sangramento Vaginal Importante

- Especialmente em gestante: pode indicar descolamento, ruptura, abortamento.

### Eclâmpsia / Pré-eclâmpsia Grave

- Gestante com cefaleia intensa, dor epigástrica, alterações visuais, edema súbito, convulsão.

## 8. Pediátricas (atenção redobrada)

### Sinais em Crianças

- Febre alta (> 39°C) em < 3 meses
- Recusa alimentar prolongada, sonolência excessiva, irritabilidade extrema
- Petéquias (manchas vermelhas que não desaparecem à pressão)
- Convulsão febril prolongada ou repetida
- Desidratação (boca seca, ausência de urina por > 8h, fontanela deprimida)
- Dificuldade respiratória, gemência, batimento de asa nasal

## 9. Síntese — Quando NÃO esperar

Se **qualquer** dos sinais abaixo estiver presente, oriente **192/SAMU** ou **PS** **antes** de qualquer agendamento ou autoavaliação adicional:

| Sistema | Sinal de alerta |
|---|---|
| Cardiovascular | Dor torácica anginosa, síncope, choque |
| Neurológico | Sinais de AVC, convulsão, trauma craniano com alteração |
| Respiratório | Dispneia grave, cianose, anafilaxia |
| GI | Abdome agudo, hemorragia importante |
| Metabólico | Hipoglicemia grave, cetoacidose |
| Psiquiátrico | Ideação suicida com plano, surto |
| Obstétrico | Sangramento na gestação, sinais de eclâmpsia |
| Pediátrico | Petéquias, febre + sonolência, desidratação |

## 10. Aplicação no BluaDiagnostics

Em código (pseudocódigo):

```python
if any_red_flag_detectada(sintomas):
    return {
        "nivel_urgencia": "critico",
        "red_flags_detectadas": [...],
        "escalada_humana": True,
        "acoes_recomendadas": [
            "Ligar 192 (SAMU) AGORA",
            "Não dirigir sozinho",
            "Anotar horário de início dos sintomas"
        ],
        "tool_a_chamar": "agendar_teleconsulta",  # urgencia=imediata como backup
    }
```

> **Princípio:** na dúvida, **escale**. Falsos positivos custam um deslocamento; falsos negativos podem custar uma vida.
