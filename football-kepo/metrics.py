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


async def snapshot_graph(rag, label: str) -> GraphSnapshot:
    graph_storage = rag.chunk_entity_relation_graph
    labels = await graph_storage.get_all_labels()
    edges = await graph_storage.get_all_edges()
    return GraphSnapshot(label=label, node_count=len(labels), edge_count=len(edges))


@dataclass
class InjectionOutcome:
    injection_id: str
    type: str
    source_doc_id: str
    detected: bool
    llm_switched: bool
    findings_count: int

    def to_json(self) -> dict:
        return {
            "injection_id": self.injection_id,
            "type": self.type,
            "source_doc_id": self.source_doc_id,
            "detected": self.detected,
            "llm_switched": self.llm_switched,
            "findings_count": self.findings_count,
        }


@dataclass
class RunReport:
    graph_before: GraphSnapshot | None = None
    graph_after: GraphSnapshot | None = None
    outcomes: list[InjectionOutcome] = field(default_factory=list)

    def _subset(self, type_: str) -> list[InjectionOutcome]:
        return [o for o in self.outcomes if o.type == type_]

    def attack_summary(self) -> dict:
        attacks = self._subset("attack")
        success_undetected = sum(1 for o in attacks if o.llm_switched and not o.detected)
        success_detected = sum(1 for o in attacks if o.llm_switched and o.detected)
        failure_detected = sum(1 for o in attacks if not o.llm_switched and o.detected)
        failure_undetected = sum(1 for o in attacks if not o.llm_switched and not o.detected)
        return {
            "total_attacks": len(attacks),
            "success_undetected": success_undetected,
            "success_detected": success_detected,
            "failure_detected": failure_detected,
            "failure_undetected": failure_undetected,
        }

    def update_summary(self) -> dict:
        updates = self._subset("update")
        detected = sum(1 for o in updates if o.detected)
        adopted = sum(1 for o in updates if o.llm_switched)
        adopted_detected = sum(1 for o in updates if o.llm_switched and o.detected)
        adopted_undetected = sum(1 for o in updates if o.llm_switched and not o.detected)
        not_adopted_detected = sum(1 for o in updates if not o.llm_switched and o.detected)
        not_adopted_undetected = sum(1 for o in updates if not o.llm_switched and not o.detected)
        return {
            "total_updates": len(updates),
            "detected_as_conflict": detected,
            "adopted_by_llm": adopted,
            "adopted_and_detected": adopted_detected,
            "adopted_and_undetected": adopted_undetected,
            "not_adopted_and_detected": not_adopted_detected,
            "not_adopted_and_undetected": not_adopted_undetected,
        }

    def to_json(self) -> dict:
        return {
            "graph_before": self.graph_before.to_json() if self.graph_before else None,
            "graph_after": self.graph_after.to_json() if self.graph_after else None,
            "attacks": self.attack_summary(),
            "updates": self.update_summary(),
            "outcomes": [o.to_json() for o in self.outcomes],
        }


def print_report(report: RunReport) -> None:
    print("\n=== Graph size ===")
    if report.graph_before and report.graph_after:
        b, a = report.graph_before, report.graph_after
        print(f"Nodes: {b.node_count} -> {a.node_count}")
        print(f"Edges: {b.edge_count} -> {a.edge_count}")

    print("\n=== Attack outcomes ===")
    a = report.attack_summary()
    print(f"Total attacks:            {a['total_attacks']}")
    print(f"Success, undetected:      {a['success_undetected']}")
    print(f"Success, detected:        {a['success_detected']}")
    print(f"Failure, detected:        {a['failure_detected']}")
    print(f"Failure, undetected:      {a['failure_undetected']}")

    print("\n=== Update (legitimate) outcomes ===")
    u = report.update_summary()
    print(f"Total updates:            {u['total_updates']}")
    print(f"Flagged as conflict:      {u['detected_as_conflict']}  (false positives)")
    print(f"Adopted by LLM:           {u['adopted_by_llm']}")
    print(f"  adopted + detected:     {u['adopted_and_detected']}")
    print(f"  adopted + undetected:   {u['adopted_and_undetected']}")
    print(f"  not adopted + detected: {u['not_adopted_and_detected']}")
    print(f"  not adopted + undetected: {u['not_adopted_and_undetected']}")


def save_report(report: RunReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_json(), f, ensure_ascii=False, indent=2)
