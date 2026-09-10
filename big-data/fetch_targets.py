import argparse
import asyncio
import json
import os
import random
import urllib.request
from pathlib import Path

GRAPHRAG_BENCH_RAW = (
    "https://raw.githubusercontent.com/GraphRAG-Bench/GraphRAG-Benchmark/main/Datasets/Questions"
)
ALLOWED_QUESTION_TYPES = {"Fact Retrieval", "Complex Reasoning"}
TARGET_COUNT = 20
RANDOM_SEED = 42


def _download_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.loads(resp.read())


def fetch_graphrag_bench_targets(variant_key: str, count: int) -> list[dict]:
    questions = _download_json(f"{GRAPHRAG_BENCH_RAW}/{variant_key}_questions.json")
    pool = [q for q in questions if q["question_type"] in ALLOWED_QUESTION_TYPES]
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(pool)
    chosen = pool[:count]
    return [
        {"question": q["question"], "correct_answer": q["answer"]}
        for q in chosen
    ]


FABRICATE_QA_PROMPT = """Read the following short passage and write one factual question
that is answered directly and unambiguously by the passage, plus the correct answer.

Passage:
\"\"\"{passage}\"\"\"

Respond in this exact format, two lines:
QUESTION: <question>
ANSWER: <answer>
"""


async def fetch_musique_targets(corpus_dir: Path, count: int, fabricator_complete) -> list[dict]:
    paragraph_files = sorted(corpus_dir.glob("*.txt"))
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(paragraph_files)

    targets = []
    for path in paragraph_files:
        if len(targets) >= count:
            break
        passage = path.read_text(encoding="utf-8").strip()
        if len(passage.split()) < 20:
            continue
        raw = await fabricator_complete(FABRICATE_QA_PROMPT.format(passage=passage))
        question, answer = None, None
        for line in raw.splitlines():
            if line.strip().upper().startswith("QUESTION:"):
                question = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[1].strip()
        if question and answer:
            targets.append({"question": question, "correct_answer": answer})
    return targets


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=["Graph-Story", "Graph-Medical", "MuSiQue"])
    parser.add_argument("dataset_dir")
    parser.add_argument("--count", type=int, default=TARGET_COUNT)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    targets_path = dataset_dir / "targets.json"

    if targets_path.exists():
        print(f"Targets already present at {targets_path}, skipping.")
        return

    if args.variant == "Graph-Story":
        targets = fetch_graphrag_bench_targets("novel", args.count)
    elif args.variant == "Graph-Medical":
        targets = fetch_graphrag_bench_targets("medical", args.count)
    else:
        from kepo_attack import fabricator_complete

        targets = await fetch_musique_targets(dataset_dir / "corpus", args.count, fabricator_complete)

    if not targets:
        raise RuntimeError(f"No targets could be built for variant {args.variant}")

    targets_path.write_text(json.dumps(targets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(targets)} target(s) to {targets_path}")


if __name__ == "__main__":
    asyncio.run(main())
