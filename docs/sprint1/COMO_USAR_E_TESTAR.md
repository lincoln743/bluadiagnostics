# 📋 GUIA — Subir ao GitHub e Testar a PoC

> **Para:** Lincoln Simão Pereira ([@lincoln743](https://github.com/lincoln743))
> **Repositório destino:** https://github.com/lincoln743/bluadiagnostics

---

## 🎯 Parte 1 — Subir ao GitHub

### 1.1 Criar o repositório no GitHub (se ainda não existir)

1. Acesse https://github.com/new
2. **Repository name:** `bluadiagnostics`
3. **Description:** "Plataforma de cuidado remoto proativo para Care Plus / Blua — Sprint 1"
4. **Public** (para o professor acessar sem permissões)
5. **NÃO marque** "Initialize with README" (já temos um)
6. Clique em **Create repository**

### 1.2 Extrair o ZIP no seu computador

Baixe e descompacte `bluadiagnostics_sprint1.zip` em uma pasta de sua escolha. Por exemplo:

- **Windows:** `C:\Users\Lincoln\Documentos\bluadiagnostics`
- **Mac/Linux:** `~/projetos/bluadiagnostics`

### 1.3 Abrir terminal na pasta extraída

**Windows (PowerShell):**
```powershell
cd C:\Users\Lincoln\Documentos\bluadiagnostics
```

**Mac/Linux:**
```bash
cd ~/projetos/bluadiagnostics
```

### 1.4 Configurar Git (apenas se for a primeira vez no computador)

```bash
git config --global user.name "Lincoln Simão Pereira"
git config --global user.email "lincoln743@gmail.com"
```

### 1.5 Fazer o primeiro commit e push

Cole **bloco por bloco** no terminal:

```bash
# Inicializar repositório local
git init

# Definir branch principal como 'main'
git branch -M main

# Adicionar todos os arquivos (o .gitignore já protege segredos)
git add .

# Conferir o que será commitado (IMPORTANTE — verifique que .env NÃO aparece)
git status
```

⚠️ **Pare e confira a saída de `git status`.** Se aparecer `.env` na lista, **NÃO continue** — algo está errado. Deve aparecer apenas:

```
new file:   .env.example
new file:   .gitignore
new file:   README.md
new file:   docs/arquitetura.svg
... (e os outros arquivos do projeto, sem .env)
```

Se estiver tudo certo, continue:

```bash
# Fazer o commit
git commit -m "Sprint 1: arquitetura, system prompt, tools, eval set e PoC do BluaDiagnostics"

# Conectar ao GitHub
git remote add origin https://github.com/lincoln743/bluadiagnostics.git

# Subir!
git push -u origin main
```

### 1.6 Autenticação no push

Quando você rodar `git push`, o GitHub pedirá autenticação. **Senha de conta não funciona mais** — você precisa de um **Personal Access Token (PAT)**:

1. Acesse https://github.com/settings/tokens
2. **Generate new token (classic)**
3. **Note:** "BluaDiagnostics push"
4. **Expiration:** 30 dias (ou o que preferir)
5. **Scopes:** marque **`repo`** (todas as sub-opções)
6. **Generate token**
7. **Copie o token** (algo como `ghp_xxxxxxxxxxxx`) — só será exibido uma vez!
8. No terminal, ao pedir senha, **cole o token** (não a senha do GitHub)

> 💡 Para não digitar toda vez, use o **Git Credential Manager** (já vem com Git for Windows, ou instale via `brew install git-credential-manager` no Mac).

### 1.7 Verificar o push

Acesse https://github.com/lincoln743/bluadiagnostics — todos os arquivos devem aparecer, e o README renderizado bonito na home do repo.

---

## 🧪 Parte 2 — Testar a PoC

Você tem **duas opções** para testar. Recomendo a **A** (Colab).

### 🌐 Opção A — Google Colab (mais fácil)

#### Passo 1 — Obter sua API key da Anthropic

1. Acesse https://console.anthropic.com
2. Faça login (ou crie conta — ganha US$ 5 de crédito grátis)
3. Vá em **Settings → API Keys**
4. **Create Key**
5. Copie o valor (algo como `sk-ant-api03-xxxxxxxx...`) — guarde, só aparece uma vez!

#### Passo 2 — Abrir o notebook no Colab

**Forma 1 — Via GitHub direto:**

1. Acesse https://colab.research.google.com
2. **File → Open notebook → GitHub**
3. Cole: `lincoln743/bluadiagnostics`
4. Selecione `notebooks/sprint1_poc.ipynb`

**Forma 2 — Via upload:**

1. Acesse https://colab.research.google.com
2. **File → Upload notebook**
3. Selecione o arquivo `notebooks/sprint1_poc.ipynb` da sua pasta

#### Passo 3 — Configurar a chave (Secrets)

1. Na barra lateral esquerda do Colab, clique no ícone 🔑 **(Secrets)**
2. **+ Add new secret**
3. **Name:** `ANTHROPIC_API_KEY`
4. **Value:** cole sua chave (sem aspas, sem espaços)
5. Ative o toggle **"Notebook access"** ao lado

#### Passo 4 — Executar

- **Runtime → Run all** (ou `Ctrl+F9` / `⌘+F9`)
- Aguarde cada célula executar (a primeira instalação demora ~30s)

#### Passo 5 — O que você deve ver

- **Seção 5** (4 turnos coerentes): a beneficiária BNF-04821 conversa com o agente, que consulta histórico, verifica interações com dipirona, e agenda teleconsulta
- **Seção 7** (red flag): agente detecta sintomas de IAM e orienta SAMU 192 imediatamente
- **Seção 8** (jailbreak): agente recusa diagnóstico definitivo de forma cortês

### 💻 Opção B — Local (no seu computador)

#### Pré-requisitos

- **Python 3.11+** instalado: https://www.python.org/downloads/
- Verifique no terminal: `python --version`

#### Passo a passo

```bash
# 1. Entrar na pasta do projeto
cd ~/projetos/bluadiagnostics    # ou onde você extraiu

# 2. Criar ambiente virtual
python -m venv .venv

# 3. Ativar o ambiente
source .venv/bin/activate         # Linux/Mac
# .venv\Scripts\activate          # Windows PowerShell

# 4. Instalar dependências
pip install -r requirements.txt

# 5. Configurar a chave
cp .env.example .env              # Linux/Mac
# copy .env.example .env          # Windows

# Edite o arquivo .env (use Notepad/VS Code/nano) e cole sua chave:
# ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxx...

# 6. Iniciar Jupyter
jupyter notebook notebooks/sprint1_poc.ipynb
```

O navegador abrirá automaticamente. Clique em **Cell → Run All** para executar todo o notebook.

---

## ✅ Checklist Final Antes da Entrega

Antes de submeter o `entrega_sprint1.txt` no portal da FIAP, confirme:

- [ ] Repositório `https://github.com/lincoln743/bluadiagnostics` está **público**
- [ ] README aparece bonito na home do repo
- [ ] Pasta `docs/arquitetura.svg` é visualizável diretamente no GitHub
- [ ] Notebook `notebooks/sprint1_poc.ipynb` foi **executado pelo menos uma vez** com sucesso (não precisa commitar a versão executada, mas deve rodar)
- [ ] `git log` mostra o commit (rode no terminal)
- [ ] **`.env` NÃO está no repositório** (confira em https://github.com/lincoln743/bluadiagnostics — não deve ter esse arquivo)
- [ ] `entrega_sprint1.txt` baixado para enviar no portal

### 🚨 Em caso de exposição acidental de chave

Se você commitou um `.env` por engano:

```bash
# Remover do índice (mantém o arquivo local)
git rm --cached .env

# Commit da remoção
git commit -m "Remove .env exposto"
git push

# IMEDIATAMENTE: revogue a chave em console.anthropic.com → API Keys → Delete
# Crie uma nova e atualize seu .env local
```

> ⚠️ Lembre que o histórico do Git mantém versões antigas. Para apagar de verdade da história, é preciso `git filter-repo` — mas o mais importante é **revogar a chave imediatamente**, pois ela já está comprometida.

---

## 📞 Suporte

Se algo der errado, me chame de volta com:

- O comando que você rodou
- A mensagem de erro completa
- Em qual passo você travou

Boa sorte! 🚀
