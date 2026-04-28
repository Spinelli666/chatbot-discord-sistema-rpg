import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import markdown_parser as parser
import llm_provider

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    sys.exit("Erro: DISCORD_TOKEN não encontrado. Verifique seu arquivo .env.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
provider = llm_provider.get_provider()


def _split_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


async def _send_chunks(destination, text: str) -> None:
    for chunk in _split_message(text):
        await destination.send(chunk)


@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")
    await bot.loop.run_in_executor(None, parser.build_index)
    mode = "LLM online" if isinstance(provider, llm_provider.OnlineProvider) else "offline"
    print(f"Índice carregado — modo {mode}. Pronto.")


@bot.command(name="teste")
async def teste(ctx):
    if ctx.author.bot:
        return
    thread = await ctx.message.create_thread(name="Teste do Bot")
    await thread.send("Bot funcionando dentro do tópico!")


@bot.command(name="habilidade")
async def habilidade(ctx, *, nome: str = None):
    """Exibe a descrição de uma habilidade pelo nome."""
    if ctx.author.bot:
        return
    if not nome:
        await ctx.reply("Use: `!habilidade [nome da habilidade]`")
        return

    results = await bot.loop.run_in_executor(None, parser.search_by_name, nome)

    if not results:
        await ctx.reply(f'Nenhuma habilidade encontrada para **"{nome}"**.')
        return

    if len(results) == 1 or _normalize_match(results[0].name, nome):
        await _send_chunks(ctx, parser.format_section(results[0]))
    else:
        listing = "\n".join(
            f"• **{s.name}** ({s.source_file})" for s in results[:5]
        )
        await ctx.reply(
            f'Encontrei várias habilidades para **"{nome}"**:\n{listing}\n\n'
            "Seja mais específico para ver os detalhes."
        )


@bot.command(name="categoria")
async def categoria(ctx, *, nome: str = None):
    """Lista todas as habilidades de uma classe ou categoria."""
    if ctx.author.bot:
        return
    if not nome:
        cats = await bot.loop.run_in_executor(None, parser.available_categories)
        await ctx.reply(
            "Use: `!categoria [nome]`\n"
            f"Categorias disponíveis: {', '.join(f'`{c}`' for c in cats)}"
        )
        return

    sections = await bot.loop.run_in_executor(None, parser.list_by_category, nome)

    if not sections:
        cats = await bot.loop.run_in_executor(None, parser.available_categories)
        await ctx.reply(
            f'Categoria **"{nome}"** não encontrada.\n'
            f"Disponíveis: {', '.join(f'`{c}`' for c in cats)}"
        )
        return

    lines = [f"**{s.name}**" + (f" — {s.ability_type}" if s.ability_type else "")
             for s in sections]
    header = f"**Categoria: {sections[0].source_file.title()}** ({len(sections)} entradas)\n"
    await _send_chunks(ctx, header + "\n".join(lines))


@bot.command(name="buscar")
async def buscar(ctx, *, termo: str = None):
    """Busca nas regras por um termo ou trecho de texto."""
    if ctx.author.bot:
        return
    if not termo:
        await ctx.reply("Use: `!buscar [termo ou trecho]`")
        return

    results = await bot.loop.run_in_executor(None, parser.search_by_term, termo)

    if not results:
        await ctx.reply(f'Nenhum resultado para **"{termo}"** nas regras.')
        return

    listing = "\n".join(
        f"• **{s.name}** (`{s.source_file}`)" for s in results
    )
    await ctx.reply(f'Resultados para **"{termo}"**:\n{listing}')


@bot.command(name="duvida")
async def duvida(ctx, *, pergunta: str = None):
    """Responde perguntas sobre as regras do Cardigan."""
    if ctx.author.bot:
        return
    if not pergunta:
        await ctx.reply("Use: `!duvida [sua pergunta sobre o Cardigan]`")
        return

    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
    else:
        thread = await ctx.message.create_thread(name=f"Dúvida: {pergunta[:80]}")

    async with thread.typing():
        try:
            sections = await bot.loop.run_in_executor(
                None, parser.search_question, pergunta
            )
            context = await bot.loop.run_in_executor(
                None, parser.build_context, sections
            )
            response = await bot.loop.run_in_executor(
                None, provider.generate_response, context, pergunta
            )
            await _send_chunks(thread, response)
        except Exception as e:
            await thread.send(f"Erro ao processar sua pergunta: {e}")


def _normalize_match(a: str, b: str) -> bool:
    import unicodedata
    def n(s):
        return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return n(a) == n(b)


bot.run(TOKEN)
