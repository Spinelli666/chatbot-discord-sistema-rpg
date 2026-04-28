import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "regras"

CATEGORY_ALIASES: dict[str, str] = {
    "mago": "feiticeiro",
    "ladrao": "ladino",
    "ladrão": "ladino",
    "ranger": "andarilho",
    "raca": "racas",
    "raça": "racas",
    "racas": "racas",
    "raças": "racas",
    "guerreiro": "guerreiro",
    "ladino": "ladino",
    "andarilho": "andarilho",
    "feiticeiro": "feiticeiro",
    "sistema": "sistema",
    "equipamento": "equipamentos",
    "equipamentos": "equipamentos",
    "arma": "equipamentos",
    "armas": "equipamentos",
    "armadura": "equipamentos",
}

@dataclass
class Section:
    name: str
    source_file: str
    category: str
    content: str
    class_name: str = ""
    ability_type: str = ""


_index: list[Section] = []


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()


def _parse_file(path: Path) -> list[Section]:
    text = path.read_text(encoding="utf-8")
    category = path.stem.lower()
    sections: list[Section] = []

    # Split on level-1 headings (## is a subsection, # starts a new section)
    parts = re.split(r"(?=^# )", text, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = part.splitlines()
        heading = lines[0].lstrip("# ").strip() if lines else ""
        if not heading:
            continue

        # Extract metadata from the section body
        class_name = ""
        ability_type = ""
        for line in lines[1:10]:
            if line.startswith("- Classe:"):
                class_name = line.split(":", 1)[1].strip()
            elif line.startswith("- Tipo:"):
                ability_type = line.split(":", 1)[1].strip()

        sections.append(Section(
            name=heading,
            source_file=path.stem,
            category=category,
            content=part,
            class_name=class_name,
            ability_type=ability_type,
        ))

    return sections


def build_index() -> None:
    global _index
    _index = []
    if not DATA_DIR.exists():
        return
    for md_file in sorted(DATA_DIR.glob("*.md")):
        _index.extend(_parse_file(md_file))


def _score(section: Section, query_norm: str) -> int:
    name_norm = _normalize(section.name)
    score = 0
    if name_norm == query_norm:
        score += 100
    elif name_norm.startswith(query_norm):
        score += 70
    elif query_norm in name_norm:
        score += 50
    elif any(query_norm in _normalize(w) for w in name_norm.split()):
        score += 30
    elif query_norm in _normalize(section.content):
        score += 10
    return score


def search_by_name(name: str) -> list[Section]:
    if not _index:
        build_index()
    q = _normalize(name.strip())
    scored = [(s, _score(s, q)) for s in _index]
    scored = [(s, sc) for s, sc in scored if sc > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:5]]


def search_by_term(term: str) -> list[Section]:
    if not _index:
        build_index()
    q = _normalize(term.strip())
    results = [s for s in _index if q in _normalize(s.content)]
    return results[:8]


def search_question(question: str) -> list[Section]:
    if not _index:
        build_index()
    q_norm = _normalize(question)
    words = [w for w in q_norm.split() if len(w) > 3]
    scored: dict[int, int] = {}
    for i, section in enumerate(_index):
        content_norm = _normalize(section.content)
        hits = sum(1 for w in words if w in content_norm)
        name_hits = sum(1 for w in words if w in _normalize(section.name))
        total = hits + name_hits * 3
        if total > 0:
            scored[i] = total
    ranking = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [_index[i] for i, _ in ranking[:5]]


def list_by_category(category: str) -> list[Section]:
    if not _index:
        build_index()
    cat = _normalize(category.strip())
    cat = CATEGORY_ALIASES.get(cat, cat)
    return [s for s in _index if s.category == cat]


def available_categories() -> list[str]:
    if not _index:
        build_index()
    return sorted({s.category for s in _index})


def format_section(section: Section, max_chars: int = 1600) -> str:
    content = section.content
    if len(content) > max_chars:
        content = content[:max_chars].rsplit("\n", 1)[0] + "\n*(... conteúdo truncado)*"
    return f"```md\n{content}\n```"


def build_context(sections: list[Section], max_chars: int = 2500) -> str:
    parts: list[str] = []
    total = 0
    for s in sections:
        chunk = s.content
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                chunk = chunk[:remaining].rsplit("\n", 1)[0]
                parts.append(chunk)
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n\n---\n\n".join(parts)
