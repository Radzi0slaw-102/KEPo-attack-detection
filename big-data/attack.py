import asyncio
import os

from kepo_attack import build_rag, run_multi_target_attack, fabricator_complete
from attack_targets import ATTACK_TARGETS
from detect import attach_conflict_detector
from metrics import RunMetrics, snapshot_graph, count_findings, print_summary, save_summary

FINDINGS_PATH = os.environ.get("KEPO_FINDINGS_ATTACK_PATH", "kepo_findings_attack.jsonl")
METRICS_PATH = os.environ.get("KEPO_METRICS_ATTACK_PATH", "kepo_metrics_attack.json")


async def main() -> None:
    rag = await build_rag()
    metrics = RunMetrics(phase="attack")

    await attach_conflict_detector(
        rag,
        judge_llm=fabricator_complete,
        findings_path=FINDINGS_PATH,
        phase="attack",
    )

    metrics.graph_before = await snapshot_graph(rag, "before_attack")

    metrics.attack_results = await run_multi_target_attack(rag, ATTACK_TARGETS)

    metrics.graph_after = await snapshot_graph(rag, "after_attack")
    metrics.conflicts_detected = count_findings(FINDINGS_PATH)

    await rag.finalize_storages()

    print(f"-- Finished attack phase, findings in {FINDINGS_PATH} --")
    print_summary(metrics)
    save_summary(metrics, METRICS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
