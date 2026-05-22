from pathlib import Path

import duckdb

from src.core.llm import LLMClient

CHUNK_SIZE = 1000
OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_documents(directory: str, pattern: str = "*.md") -> dict[str, str]:
    docs = {}
    for fpath in sorted(Path(directory).rglob(pattern)):
        if ".venv" in str(fpath) or "__pycache__" in str(fpath):
            continue
        try:
            docs[str(fpath)] = fpath.read_text(errors="replace")
        except Exception:
            pass
    return docs


def ingest_directory(
    directory: str, db_path: str = "data/rag.duckdb", llm: LLMClient | None = None
) -> dict:
    llm = llm or LLMClient()
    con = duckdb.connect(db_path)

    con.execute("INSTALL vss; LOAD vss;")
    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS chunk_seq START 1
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id INTEGER PRIMARY KEY,
            source TEXT,
            content TEXT,
            embedding FLOAT[1536]
        )
    """)

    docs = load_documents(directory)
    total_chunks = 0
    for source, text in docs.items():
        chunks = chunk_text(text)
        for chunk in chunks:
            emb = llm.embed(chunk)
            if emb is None:
                continue
            seq = con.execute("SELECT nextval('chunk_seq')").fetchone()[0]
            con.execute(
                "INSERT INTO doc_chunks (id, source, content, embedding) VALUES (?, ?, ?, ?)",
                [seq, source, chunk, emb],
            )
            total_chunks += 1

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_hnsw_docs
        ON doc_chunks USING HNSW (embedding)
        WITH (metric = 'cosine')
    """)

    con.close()
    return {"files": len(docs), "chunks": total_chunks, "db": db_path}
