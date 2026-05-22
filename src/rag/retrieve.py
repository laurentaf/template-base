import duckdb

from src.core.llm import LLMClient


def search(
    query: str,
    db_path: str = "data/rag.duckdb",
    top_k: int = 5,
    llm: LLMClient | None = None,
) -> list[dict]:
    llm = llm or LLMClient()
    query_emb = llm.embed(query)
    if query_emb is None:
        return []

    con = duckdb.connect(db_path)
    con.execute("INSTALL vss; LOAD vss;")

    rows = con.execute(
        """
        SELECT source, content, array_cosine_similarity(embedding, ?) AS score
        FROM doc_chunks
        ORDER BY score DESC
        LIMIT ?
        """,
        [query_emb, top_k],
    ).fetchall()

    con.close()
    return [{"source": r[0], "content": r[1], "score": round(r[2], 4)} for r in rows]
