import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_parser import Section


def clean_markdown(text: str) -> str:
    """Strip raw markdown syntax, keeping Discord-compatible formatting intact."""
    # Remove horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    # Convert h1 headings to bold
    text = re.sub(r"^#\s+(.+)$", r"**\1**", text, flags=re.MULTILINE)
    # Convert h2+ headings to bold with colon
    text = re.sub(r"^#{2,}\s+(.+)$", r"**\1:**", text, flags=re.MULTILINE)
    # Remove code block fences
    text = re.sub(r"```[a-z]*\n?", "", text)
    # Remove blockquote markers
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_ability(section) -> dict:
    """Parse a Section object into structured parts."""
    lines = section.content.splitlines()

    meta: dict[str, str] = {}
    description_parts: list[str] = []
    subsections: dict[str, str] = {}
    current_sub: str | None = None
    current_lines: list[str] = []
    past_meta = False

    for line in lines[1:]:  # skip the leading # heading line
        if line.startswith("## "):
            past_meta = True
            if current_sub is not None:
                subsections[current_sub] = "\n".join(current_lines).strip()
            current_sub = line.lstrip("# ").strip()
            current_lines = []
        elif current_sub is not None:
            current_lines.append(line)
        else:
            m = re.match(r"^-\s+(.+?):\s+(.+)$", line)
            if m and not past_meta:
                meta[m.group(1).strip()] = m.group(2).strip()
            elif line.strip():
                past_meta = True
                description_parts.append(line)
            elif past_meta:
                description_parts.append(line)

    if current_sub is not None:
        subsections[current_sub] = "\n".join(current_lines).strip()

    return {
        "title": section.name,
        "meta": meta,
        "description": "\n".join(description_parts).strip(),
        "subsections": subsections,
    }


def _meta_line(meta: dict) -> str:
    """Build a compact metadata summary from ability metadata."""
    header_parts = []
    if "Classe" in meta:
        header_parts.append(meta["Classe"])
    if "Tipo" in meta:
        header_parts.append(meta["Tipo"])

    cost_parts = []
    if "Custo" in meta:
        cost_parts.append(meta["Custo"])
    if "Custo de Energia" in meta:
        cost_parts.append(meta["Custo de Energia"])
    if "Requisito" in meta:
        cost_parts.append(f"Req: {meta['Requisito']}")
    if "Categoria" in meta:
        cost_parts.append(meta["Categoria"])

    lines = []
    if header_parts:
        lines.append(" · ".join(header_parts))
    if cost_parts:
        lines.append(" · ".join(cost_parts))
    return "\n".join(lines)


def format_habilidade(section) -> str:
    """Format a single ability section for Discord."""
    parsed = _parse_ability(section)
    parts = [f"**{parsed['title']}**"]

    meta_text = _meta_line(parsed["meta"])
    if meta_text:
        parts.append(meta_text)

    if parsed["description"]:
        parts.append("")
        parts.append(parsed["description"])

    for sub_name, sub_content in parsed["subsections"].items():
        parts.append("")
        parts.append(f"**{sub_name}:**")
        if sub_content:
            parts.append(sub_content)

    return "\n".join(parts)


def format_ambiguous(results: list, query: str) -> str:
    """Format a disambiguation listing when multiple abilities match."""
    lines = [f'Encontrei várias habilidades para **"{query}"**:\n']
    for s in results[:5]:
        lines.append(f"- **{s.name}** ({s.source_file})")
    lines.append("\nSeja mais específico para ver os detalhes.")
    return "\n".join(lines)


def format_categoria(results: list, nome: str = "") -> str:
    """Format a full category listing for !categoria."""
    if not results:
        return f'Nenhuma habilidade encontrada na categoria **"{nome}"**.'

    source = results[0].source_file.title()
    header = f"**{source}** — {len(results)} habilidades\n"

    items = []
    for s in results:
        entry = f"- **{s.name}**"
        if s.ability_type:
            entry += f" ({s.ability_type})"
        items.append(entry)

    return header + "\n".join(items)


def format_busca(results: list, termo: str) -> str:
    """Format keyword search results for !buscar."""
    if not results:
        return f'Nenhum resultado encontrado para **"{termo}"** nas regras.'

    count = len(results)
    lines = [f'Encontrei **{count} resultado{"s" if count > 1 else ""}** para "{termo}":\n']
    for s in results:
        entry = f"- **{s.name}** ({s.source_file.title()})"
        if s.ability_type:
            entry += f" — {s.ability_type}"
        lines.append(entry)
    lines.append("\nUse `!habilidade [nome]` para ver os detalhes completos.")
    return "\n".join(lines)


def format_duvida(response: str) -> str:
    """Clean and format a response for !duvida (online or offline mode)."""
    return clean_markdown(response)
