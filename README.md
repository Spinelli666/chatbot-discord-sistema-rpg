## Descrição do Projeto

O **chatbot-discord-sistema-rpg** é um bot para Discord projetado para consulta e interpretação de regras de um sistema de RPG baseado em arquivos Markdown (`.md`). O projeto utiliza uma abordagem estruturada de indexação, embeddings e busca para transformar documentos estáticos em uma base de conhecimento interativa.

A aplicação funciona, por padrão, em modo **offline**, sem necessidade de APIs externas, realizando parsing dos arquivos `.md`, indexando seu conteúdo com ChromaDB e embeddings para permitir buscas semânticas rápidas e eficientes. O sistema suporta busca por nome, termos, categorias e perguntas em linguagem natural com contexto recuperado via RAG.

A arquitetura foi construída de forma modular, incluindo uma camada de abstração de provedores de linguagem (LLM), permitindo que o bot opere tanto em modo offline quanto com integração a modelos como Claude (Anthropic) ou GPT-4 (OpenAI), sem necessidade de refatoração.

---

## Principais Funcionalidades

- 📚 Indexação automática de regras a partir de arquivos `.md` com embeddings
- 🧠 Busca semântica com ChromaDB e embeddings
- 🔎 Busca fuzzy (tolerante a variações de escrita)
- 🧩 Organização por categorias (classes, habilidades, etc.)
- 💬 Comandos interativos no Discord:
  - `!teste` — verifica se o bot está respondendo em threads
  - `!habilidade [nome]` — exibe detalhes de uma habilidade específica
  - `!categoria [nome]` — lista todas as habilidades de uma classe/categoria
  - `!buscar [termo]` — busca por um termo ou trecho nas regras
  - `!duvida [pergunta]` — responde perguntas em linguagem natural com contexto
- 💬 Conversas contínuas — mensagens simples após `!duvida` continuam a dúvida por 2 minutos
- 🧠 Sistema de fallback offline baseado em contexto
- 🔌 Suporte a LLM (Claude Anthropic ou GPT-4 OpenAI) via variável de ambiente
- 🎨 Formatação automática de respostas para Discord (sem cabeçalhos brutos, sem blocos de código verbosos)

---

## Arquitetura

O projeto é dividido em cinco componentes principais:

- **markdown_parser.py**  
  Responsável por ler e transformar arquivos `.md` em estruturas indexadas. Fornece buscas por nome exato, termo e categoria com normalização de texto para tratamento de acentos e variações de escrita.

- **rag.py**  
  Sistema de recuperação aumentada por geração (RAG) que utiliza ChromaDB com embeddings para buscas semânticas sobre as regras. Divide documentos em chunks e permite recuperar contexto relevante para responder perguntas em linguagem natural.

- **llm_provider.py**  
  Camada de abstração que define o comportamento do sistema em modo offline ou online. Suporta Anthropic (Claude Opus 4.7) com cache de embeddings e OpenAI (GPT-4o-mini). Implementa fallback automático quando contexto é insuficiente.

- **formatter.py**  
  Responsável por converter Markdown bruto em respostas formatadas para Discord, preservando negrito e listas, mas removendo cabeçalhos verbosos e blocos de código. Estrutura habilidades em cards compactos com metadados (Classe, Tipo, Custo, etc.).

- **bot.py**  
  Interface principal do bot no Discord, responsável por interpretar comandos e retornar respostas. Gerencia contexto de dúvidas com timeout de 120 segundos, permitindo seguimentos em mensagens simples.

---

## Objetivo

O objetivo do projeto é servir como uma base flexível para sistemas de RPG digitais, permitindo:

- consulta rápida de regras
- expansão contínua via arquivos `.md`
- integração opcional com inteligência artificial
- baixo custo operacional (ou zero custo em modo offline)

---

## Instalação e Configuração

### Pré-requisitos

- Python 3.10+
- pip ou gerenciador de pacotes similar

### Setup Rápido

```bash
# 1. Clonar o repositório
git clone <seu-repositório>
cd chatbot-discord-sistema-rpg

# 2. Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar arquivo .env
cat > .env << EOF
DISCORD_TOKEN=seu_token_aqui
AI_PROVIDER=offline  # ou: anthropic, openai
ANTHROPIC_API_KEY=sua_chave_aqui  # se usar Anthropic
OPENAI_API_KEY=sua_chave_aqui  # se usar OpenAI
EOF

# 5. Executar o bot
python bot.py
```

### Variáveis de Ambiente

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `DISCORD_TOKEN` | ✅ Sim | Token do bot Discord (obtenha em [Discord Developer Portal](https://discord.com/developers)) |
| `AI_PROVIDER` | ❌ Não | `offline` (padrão), `anthropic` ou `openai` |
| `ANTHROPIC_API_KEY` | ❌ Não | Chave de API da Anthropic (necessária se `AI_PROVIDER=anthropic`) |
| `OPENAI_API_KEY` | ❌ Não | Chave de API da OpenAI (necessária se `AI_PROVIDER=openai`) |

---

## Como Usar

### No Discord

```
!teste                          → Verifica se o bot responde em threads
!habilidade Ataque Rápido       → Exibe detalhes da habilidade
!categoria Guerreiro            → Lista todas as habilidades da classe
!buscar custo mana              → Busca regras por termo
!duvida Quanto de dano faz X?   → Pergunta sobre regras (suporta linguagem natural)
  mensagem simples após !duvida → Continua a dúvida (válida por 2 minutos)
```

### Adicionando Novas Regras

1. Adicione um arquivo `.md` na pasta `data/regras/`
2. O arquivo deve começar com headings nível 1 (`# Nome da Habilidade`)
3. Metadata opcional em formato de lista: `- Classe: Guerreiro`
4. Subseções com `## Subtítulo`
5. Reinicie o bot para indexar automaticamente

**Exemplo:**
```markdown
# Ataque Rápido
- Classe: Guerreiro
- Tipo: Ataque
- Custo: 2 Energia

Descrição da habilidade...

## Efeitos Especiais
Detalhes dos efeitos...
```

---