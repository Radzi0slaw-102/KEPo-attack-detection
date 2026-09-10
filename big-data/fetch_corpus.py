import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

GRAPHRAG_BENCH_RAW = (
    "https://raw.githubusercontent.com/GraphRAG-Bench/GraphRAG-Benchmark/main/Datasets/Corpus"
)
MUSIQUE_HF_DATASET = "dgslibisey/MuSiQue"
MUSIQUE_PARAGRAPH_LIMIT = 2000


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def _write_doc(corpus_dir: Path, name: str, text: str) -> None:
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    (corpus_dir / f"{safe_name}.txt").write_text(text, encoding="utf-8")


def fetch_graphrag_bench(variant_key: str, corpus_dir: Path) -> None:
    raw = _download(f"{GRAPHRAG_BENCH_RAW}/{variant_key}.json")
    data = json.loads(raw)
    docs = data if isinstance(data, list) else [data]
    for doc in docs:
        _write_doc(corpus_dir, doc["corpus_name"], doc["context"])
    print(f"Saved {len(docs)} document(s) to {corpus_dir}")


def fetch_musique(corpus_dir: Path, limit: int = MUSIQUE_PARAGRAPH_LIMIT) -> None:
    from datasets import load_dataset

    ds = load_dataset(MUSIQUE_HF_DATASET, split="validation")
    seen_titles: set[str] = set()
    count = 0
    for row in ds:
        for para in row["paragraphs"]:
            title = para["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            _write_doc(corpus_dir, title, para["paragraph_text"])
            count += 1
            if count >= limit:
                print(f"Saved {count} unique paragraphs to {corpus_dir}")
                return
    print(f"Saved {count} unique paragraphs to {corpus_dir} (dataset exhausted)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=["Graph-Story", "Graph-Medical", "MuSiQue"])
    parser.add_argument("dataset_dir")
    args = parser.parse_args()

    corpus_dir = Path(args.dataset_dir) / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    if any(corpus_dir.iterdir()):
        print(f"Corpus already present in {corpus_dir}, skipping download.")
        return

    if args.variant == "Graph-Story":
        fetch_graphrag_bench("novel", corpus_dir)
    elif args.variant == "Graph-Medical":
        fetch_graphrag_bench("medical", corpus_dir)
    elif args.variant == "MuSiQue":
        fetch_musique(corpus_dir)


if __name__ == "__main__":
    main()
