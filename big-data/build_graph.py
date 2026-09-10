import asyncio
import os
from pathlib import Path

from kepo_attack import build_rag, fabricator_complete
from detect import attach_conflict_detector
from metrics import RunMetrics, snapshot_graph, count_findings, print_summary, save_summary

DATASET_DIR = Path(os.environ["KEPO_DATASET_DIR"])
CORPUS_DIR = DATASET_DIR / "corpus"

FINDINGS_PATH = os.environ.get("KEPO_FINDINGS_CLEAN_PATH", "kepo_findings_clean.jsonl")
METRICS_PATH = os.environ.get("KEPO_METRICS_CLEAN_PATH", "kepo_metrics_clean.json")


async def main() -> None:
    rag = await build_rag()
    metrics = RunMetrics(phase="clean_corpus")

    metrics.graph_before = await snapshot_graph(rag, "before_insert")

    await attach_conflict_detector(
        rag,
        judge_llm=fabricator_complete,
        findings_path=FINDINGS_PATH,
        phase="clean_corpus",
    )

    corpus_files = sorted(CORPUS_DIR.glob("*.txt"))
    if not corpus_files:
        raise FileNotFoundError(f"No corpus files found in {CORPUS_DIR}")

    print(f"Enqueuing {len(corpus_files)} document(s) from {CORPUS_DIR}")
    print("Already-PROCESSED documents from a prior run are skipped automatically.")
    for path in corpus_files:
        await rag.ainsert(path.read_text(encoding="utf-8"))

    metrics.graph_after = await snapshot_graph(rag, "after_insert")
    metrics.conflicts_detected = count_findings(FINDINGS_PATH)

    await rag.finalize_storages()

    print(f"-- Finished building clean graph, findings in {FINDINGS_PATH} --")
    print_summary(metrics)
    save_summary(metrics, METRICS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
