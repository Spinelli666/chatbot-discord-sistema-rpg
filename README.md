## Descrição do Projeto

O **chatbot-discord-sistema-rpg** é um bot para Discord projetado para consulta e interpretação de regras de um sistema de RPG baseado em arquivos Markdown (`.md`). O projeto utiliza uma abordagem estruturada de indexação e busca para transformar documentos estáticos em uma base de conhecimento interativa.

A aplicação funciona, por padrão, em modo **offline**, sem necessidade de APIs externas, realizando parsing dos arquivos `.md` e indexando seu conteúdo em memória para permitir buscas rápidas e eficientes. O sistema suporta busca por nome, termos e categorias, além de consultas mais amplas utilizando recuperação de contexto (RAG simplificado).

A arquitetura foi construída de forma modular, incluindo uma camada de abstração de provedores de linguagem (LLM), permitindo que o bot opere tanto sem custo quanto com integração futura a modelos como OpenAI ou Anthropic, sem necessidade de refatoração.

---

## Principais Funcionalidades

- 📚 Indexação automática de regras a partir de arquivos `.md`
- 🔎 Busca fuzzy (tolerante a variações de escrita)
- 🧩 Organização por categorias (classes, habilidades, etc.)
- 💬 Comandos interativos no Discord:
  - `!habilidade [nome]`
  - `!categoria [nome]`
  - `!buscar [termo]`
  - `!duvida [pergunta]`
- 🧠 Sistema de fallback offline baseado em contexto
- 🔌 Suporte opcional a LLM (OpenAI / Anthropic) via variável de ambiente

---

## Arquitetura

O projeto é dividido em três componentes principais:

- **markdown_parser.py**  
  Responsável por ler e transformar arquivos `.md` em estruturas indexadas para busca.

- **llm_provider.py**  
  Camada de abstração que define o comportamento do sistema com ou sem uso de IA.

- **bot.py**  
  Interface principal do bot no Discord, responsável por interpretar comandos e retornar respostas.

---

## Objetivo

O objetivo do projeto é servir como uma base flexível para sistemas de RPG digitais, permitindo:

- consulta rápida de regras
- expansão contínua via arquivos `.md`
- integração opcional com inteligência artificial
- baixo custo operacional (ou zero custo em modo offline)