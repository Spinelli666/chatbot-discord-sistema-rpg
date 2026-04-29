import os
import sys
import time
import discord
from discord.ext import commands
from dotenv import load_dotenv
import markdown_parser as parser
import llm_provider
import formatter

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    sys.exit("Erro: DISCORD_TOKEN não encontrado. Verifique seu arquivo .env.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
provider = llm_provider.get_provider()

_DUVIDA_TIMEOUT = 120  # seconds a user stays in duvida context after last interaction
_duvida_context: dict[int, float] = {}  # user_id -> monotonic timestamp of last duvida


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


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    content = message.content.strip()
    uid = message.author.id
    now = time.monotonic()

    if content.startswith("!"):
        # Any command other than !duvida resets the context
        if not content.lower().startswith("!duvida"):
            _duvida_context.pop(uid, None)
    elif content:
        # Plain message — route to duvida if the user has an active context
        active_since = _duvida_context.get(uid)
        if active_since is not None and (now - active_since) < _DUVIDA_TIMEOUT:
            _duvida_context[uid] = now  # renew on each follow-up
            ctx = await bot.get_context(message)
            await duvida(ctx, pergunta=content)
            return
        else:
            _duvida_context.pop(uid, None)

    await bot.process_commands(message)


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

    if _normalize_match(results[0].name, nome):
        # Exact top-level name match — format the full ability card
        await _send_chunks(ctx, formatter.format_habilidade(results[0]))
        return

    # Name doesn't match exactly — try to extract the term as a subsection or bold item
    specific = await bot.loop.run_in_executor(None, parser.find_in_section, nome, results)
    if specific:
        await _send_chunks(ctx, specific)
    elif len(results) == 1:
        await _send_chunks(ctx, formatter.format_habilidade(results[0]))
    else:
        await ctx.reply(formatter.format_ambiguous(results, nome))


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

    await _send_chunks(ctx, formatter.format_categoria(sections, nome))


@bot.command(name="buscar")
async def buscar(ctx, *, termo: str = None):
    """Busca nas regras por um termo ou trecho de texto."""
    if ctx.author.bot:
        return
    if not termo:
        await ctx.reply("Use: `!buscar [termo ou trecho]`")
        return

    results = await bot.loop.run_in_executor(None, parser.search_by_term, termo)

    # If the term maps to an exact subsection or bold item, show just that
    specific = await bot.loop.run_in_executor(None, parser.find_in_section, termo, results)
    if specific:
        await _send_chunks(ctx, specific)
    else:
        await ctx.reply(formatter.format_busca(results, termo))


@bot.command(name="duvida")
async def duvida(ctx, *, pergunta: str = None):
    """Responde perguntas sobre as regras do Cardigan."""
    if ctx.author.bot:
        return
    if not pergunta:
        await ctx.reply("Use: `!duvida [sua pergunta sobre o Cardigan]`")
        return

    _duvida_context[ctx.author.id] = time.monotonic()

    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
    else:
        thread = await ctx.message.create_thread(name=f"Dúvida: {pergunta[:80]}")

    async with thread.typing():
        try:
            sections = await bot.loop.run_in_executor(
                None, parser.search_question, pergunta
            )
            specific = await bot.loop.run_in_executor(
                None, parser.find_specific_content, sections, pergunta
            )
            context = specific if specific else await bot.loop.run_in_executor(
                None, parser.build_context, sections
            )
            response = await bot.loop.run_in_executor(
                None, provider.generate_response, context, pergunta
            )
            await _send_chunks(thread, formatter.format_duvida(response))
        except Exception as e:
            await thread.send(f"Erro ao processar sua pergunta: {e}")


def _normalize_match(a: str, b: str) -> bool:
    import unicodedata
    def n(s):
        return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return n(a) == n(b)


bot.run(TOKEN)
