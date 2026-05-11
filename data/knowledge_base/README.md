# Knowledge Base

Esta pasta deve conter os 5 documentos curados da Sprint 1:

- `kb01_protocolo_manchester.md` — Protocolo Manchester de classificação de urgência
- `kb02_bulas_resumidas.md` — Bulas resumidas dos 20 medicamentos top Care Plus
- `kb03_politica_telemedicina.md` — CFM 2.314/2022 + LGPD aplicada à telemedicina
- `kb04_cartilha_beneficiario.md` — Quando procurar PS vs teleconsulta
- `kb05_red_flags.md` — Lista de sintomas críticos por sistema

## Como popular esta pasta

Copie os arquivos do repositório da Sprint 1:

```bash
cp ../../bluadiagnostics-sprint1/kb/*.md ./
```

Ou, se você está no mesmo repo (recomendado), eles já estão em `kb/` da raiz.
Neste caso, o `src/rag/ingest.py` aponta para esta pasta — você pode:

**Opção A**: copiar:
```bash
cp ../../kb/*.md ./
```

**Opção B**: criar symlinks (mais limpo, sem duplicar arquivos):
```bash
cd data/knowledge_base
ln -s ../../kb/*.md .
```

Depois rode:
```bash
blua-ingest
```
