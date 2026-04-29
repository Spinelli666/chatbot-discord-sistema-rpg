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
    # Use \w+ to strip punctuation (e.g. trailing "?") before filtering
    words = [w for w in re.findall(r"\w+", q_norm) if len(w) > 3]
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


_STOP_WORDS: frozenset[str] = frozenset({
    # artigos e preposições
    "o", "a", "os", "as", "um", "uma",
    "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas",
    "ao", "aos", "pelo", "pela", "pelos", "pelas",
    "por", "para", "sobre", "com", "sem", "entre", "ate",
    # pronomes e demonstrativos
    "me", "se", "lhe", "nos", "vos", "isso", "esse", "este", "essa", "esta",
    # verbos auxiliares e comuns de perguntas
    "e", "sao", "foi", "era", "ser", "estar", "ter", "ha",
    "faz", "funciona", "significa", "serve", "explica", "explique",
    "diga", "diz", "conta", "fala", "voce", "eu",
    # palavras interrogativas
    "que", "qual", "quais", "como", "quando", "onde", "quem", "quanto",
    # termos genéricos do domínio (não são nomes próprios de mecânica)
    "efeito", "habilidade", "regra", "sistema", "mecanica", "classe",
    "propriedade", "tipo", "item", "coisa", "algo",
})


def _extract_query_terms(question: str) -> list[str]:
    """Extract candidate search terms from a question, multi-word first."""
    words = re.findall(r"\b\w+\b", question, re.UNICODE)
    filtered = [w for w in words if _normalize(w) not in _STOP_WORDS and len(w) >= 2]

    candidates: list[str] = []
    for n in (3, 2):
        for i in range(len(filtered) - n + 1):
            candidates.append(" ".join(filtered[i : i + n]))
    candidates.extend(filtered)
    return candidates


def _heading_matches(heading_norm: str, term_norm: str) -> bool:
    """Return True if a heading text matches the search term.

    Single-word terms require an exact heading match to avoid false positives
    (e.g. "Dano" should not match "Dano de Queda"). Multi-word terms check
    that every word of the term appears in the heading words.
    """
    if heading_norm == term_norm:
        return True
    if " " in term_norm:
        heading_words = set(heading_norm.split())
        return all(part in heading_words for part in term_norm.split())
    return False


_BOLD_ITEM_RE = re.compile(r"^(?:[-*]\s*)?\*\*(.+?)\*\*[:\s]?(.*)?$")


def extract_exact_section(term: str, content: str) -> str | None:
    """Return only the block that matches *term* inside *content*.

    Strategy 1 — any-level heading (# ## ###): collects lines until the next
    heading at the same or higher level, or a horizontal rule.

    Strategy 2 — bold list item (**Term**: or - **Term**:): collects the item
    line plus any continuation lines until the next bold item or heading.
    """
    term_norm = _normalize(term)
    lines = content.splitlines()

    # Strategy 1: heading match
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.+)$", line)
        if not m:
            continue
        level = len(m.group(1))
        heading_norm = _normalize(m.group(2).strip())
        if not _heading_matches(heading_norm, term_norm):
            continue
        body: list[str] = []
        for next_line in lines[i + 1:]:
            stop = re.match(r"^(#{1,3})\s+", next_line)
            if stop and len(stop.group(1)) <= level:
                break
            if re.match(r"^-{3,}\s*$", next_line):
                break
            body.append(next_line)
        body_text = "\n".join(body).strip()
        heading_text = m.group(2).strip()
        return f"**{heading_text}**\n\n{body_text}" if body_text else f"**{heading_text}**"

    # Strategy 2: bold item match
    for i, line in enumerate(lines):
        m = _BOLD_ITEM_RE.match(line)
        if not m:
            continue
        if not _heading_matches(_normalize(m.group(1).strip()), term_norm):
            continue
        body = [line]
        for next_line in lines[i + 1:]:
            if _BOLD_ITEM_RE.match(next_line):
                break
            if re.match(r"^#{1,3}\s+", next_line):
                break
            if re.match(r"^-{3,}\s*$", next_line):
                break
            body.append(next_line)
        return "\n".join(body).strip()

    return None


def find_in_section(term: str, sections: list[Section]) -> str | None:
    """Try to extract *term* as a subsection or bold item from each section."""
    for section in sections:
        result = extract_exact_section(term, section.content)
        if result:
            return result
    return None


def find_specific_content(sections: list[Section], question: str) -> str | None:
    """Try to extract only the sub-item the question is asking about.

    First searches within the sections returned by search_question. If nothing
    matches, falls back to scanning the full index — this handles cases where the
    defining section (e.g. "Efeitos Negativos") scored lower than sections that
    merely *mention* the term (e.g. skills that apply "Atordoado").
    """
    if not _index:
        build_index()

    terms = _extract_query_terms(question)

    # Pass 1: within the already-ranked sections (fast path)
    for term in terms:
        for section in sections:
            result = extract_exact_section(term, section.content)
            if result:
                return result

    # Pass 2: full-index scan.
    # Skip terms that are themselves top-level section names — those should be
    # answered via build_context (the full # Section), not a stray sub-heading
    # found inside an unrelated section.
    top_level_names = {_normalize(s.name) for s in _index}
    for term in terms:
        if _normalize(term) in top_level_names:
            continue
        for section in _index:
            result = extract_exact_section(term, section.content)
            if result:
                return result

    return None


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
