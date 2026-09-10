import asyncio
import json
import os
from pathlib import Path

from build_rag import build_rag
from metrics import snapshot_graph

CORPUS_PATH = Path(os.environ.get("FOOTBALL_CORPUS_PATH", "data/corpus.json"))
WORKING_DIR = os.environ.get("FOOTBALL_WORKING_DIR", "./football_storage")


def load_corpus(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    docs = data["documents"]
    if len(docs) < 10:
        raise ValueError(f"Expected a sizeable corpus, got only {len(docs)} documents")
    seen_ids = set()
    for doc in docs:
        if doc["id"] in seen_ids:
            raise ValueError(f"Duplicate document id: {doc['id']}")
        seen_ids.add(doc["id"])
    return docs


async def main() -> None:
    docs = load_corpus(CORPUS_PATH)
    rag = await build_rag(WORKING_DIR)

    before = await snapshot_graph(rag, "before_insert")
    print(f"Inserting {len(docs)} base corpus document(s) (already-PROCESSED ones are skipped)")

    for doc in docs:
        await rag.ainsert(doc["text"])

    after = await snapshot_graph(rag, "after_insert")
    await rag.finalize_storages()

    print(f"Clean graph built at {WORKING_DIR}")
    print(f"Nodes: {before.node_count} -> {after.node_count}")
    print(f"Edges: {before.edge_count} -> {after.edge_count}")


if __name__ == "__main__":
    asyncio.run(main())
