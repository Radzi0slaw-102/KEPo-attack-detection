import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GraphSnapshot:
    label: str
    node_count: int
    edge_count: int

    def to_json(self) -> dict:
        return {"label": self.label, "node_count": self.node_count, "edge_count": self.edge_count}


@dataclass
class RunMetrics:
    phase: str
    graph_before: GraphSnapshot | None = None
    graph_after: GraphSnapshot | None = None
    attack_results: list[bool] = field(default_factory=list)
    conflicts_detected: int = 0

    @property
    def attack_success_rate(self) -> float:
        if not self.attack_results:
            return 0.0
        return sum(self.attack_results) / len(self.attack_results)

    def to_json(self) -> dict:
        return {
            "phase": self.phase,
            "graph_before": self.graph_before.to_json() if self.graph_before else None,
            "graph_after": self.graph_after.to_json() if self.graph_after else None,
            "targets_total": len(self.attack_results),
            "targets_succeeded": sum(self.attack_results),
            "attack_success_rate": round(self.attack_success_rate, 4),
            "conflicts_detected": self.conflicts_detected,
        }


async def snapshot_graph(rag, label: str) -> GraphSnapshot:
    graph_storage = rag.chunk_entity_relation_graph
    labels = await graph_storage.get_all_labels()
    edges = await graph_storage.get_all_edges()
    return GraphSnapshot(label=label, node_count=len(labels), edge_count=len(edges))


def count_findings(findings_path: str) -> int:
    path = Path(findings_path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def print_summary(metrics: RunMetrics) -> None:
    print(f"\n=== Metrics summary ({metrics.phase}) ===")
    if metrics.graph_before:
        b = metrics.graph_before
        print(f"Graph before: {b.node_count} nodes, {b.edge_count} edges")
    if metrics.graph_after:
        a = metrics.graph_after
        print(f"Graph after:  {a.node_count} nodes, {a.edge_count} edges")
    if metrics.attack_results:
        print(
            f"Attack success rate: {metrics.attack_success_rate:.1%} "
            f"({sum(metrics.attack_results)}/{len(metrics.attack_results)})"
        )
    print(f"Conflicts detected: {metrics.conflicts_detected}")


def save_summary(metrics: RunMetrics, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_json(), f, ensure_ascii=False, indent=2)
