from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

RULES_DIR = Path("data/regras")
CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "cardigan_rules"

_collection = None


def _chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def build_index() -> None:
    global _collection
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = DefaultEmbeddingFunction()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    _collection = client.create_collection(name=COLLECTION_NAME, embedding_function=ef)

    ids, texts, metadatas = [], [], []
    for md_file in sorted(RULES_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunk_text(content)):
            ids.append(f"{md_file.stem}_{i}")
            texts.append(chunk)
            metadatas.append({"source": md_file.name})

    if texts:
        _collection.add(documents=texts, ids=ids, metadatas=metadatas)

    print(f"Índice RAG construído: {len(texts)} chunks de {len(list(RULES_DIR.glob('*.md')))} arquivos.")


def search(query: str, n_results: int = 4) -> str:
    global _collection
    if _collection is None:
        build_index()

    count = _collection.count()
    if count == 0:
        return "Nenhuma regra encontrada na base de conhecimento."

    results = _collection.query(
        query_texts=[query],
        n_results=min(n_results, count),
    )
    docs = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]

    parts = []
    for doc, src in zip(docs, sources):
        parts.append(f"[{src}]\n{doc}")

    return "\n\n---\n\n".join(parts)
