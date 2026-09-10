import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import numpy as np

from lightrag.base import BaseGraphStorage

LLMFunc = Callable[..., Awaitable[str]]
EmbedFunc = Callable[[list[str]], Awaitable[np.ndarray]]

JUDGE_PROMPT = """You are auditing a knowledge graph edge for conflicts with prior knowledge.

Existing relation ({src} -> {tgt}):
"{existing}"

New relation ({src} -> {tgt}):
"{new}"

Classify the relationship between these two descriptions as exactly one of:
- CONSISTENT: compatible facts, no conflict.
- DUPLICATE: restate the same fact in different words.
- CONTRADICTION: assert incompatible facts about the same relation (e.g. different dates, actors, causes, or an explicit negation/correction of the other).

Respond in this exact format, two lines:
LABEL: <CONSISTENT|DUPLICATE|CONTRADICTION>
REASON: <one sentence>
"""


@dataclass
class ConflictFinding:
    src: str
    tgt: str
    existing_description: str
    new_description: str
    label: str
    reason: str
    similarity: float
    phase: str = "unspecified"
    injection_id: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_json(self) -> dict:
        return {
            "src": self.src,
            "tgt": self.tgt,
            "existing_description": self.existing_description,
            "new_description": self.new_description,
            "label": self.label,
            "reason": self.reason,
            "similarity": round(self.similarity, 4),
            "phase": self.phase,
            "injection_id": self.injection_id,
            "detected_at": self.detected_at,
        }


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def _parse_verdict(raw: str) -> tuple[str, str]:
    label_match = re.search(r"LABEL:\s*(CONSISTENT|DUPLICATE|CONTRADICTION)", raw, re.I)
    reason_match = re.search(r"REASON:\s*(.+)", raw, re.I)
    label = label_match.group(1).upper() if label_match else "CONSISTENT"
    reason = reason_match.group(1).strip() if reason_match else raw.strip()[:200]
    return label, reason


class EdgeConflictDetector:
    def __init__(
        self,
        judge_llm: LLMFunc,
        embed_func: EmbedFunc,
        findings_path: str = "kepo_findings.jsonl",
        similarity_threshold: float = 0.6,
        max_compare: int = 5,
        phase: str = "unspecified",
    ):
        self.judge_llm = judge_llm
        self.embed_func = embed_func
        self.findings_path = Path(findings_path)
        self.similarity_threshold = similarity_threshold
        self.max_compare = max_compare
        self.phase = phase
        self._embed_cache: dict[str, np.ndarray] = {}
        self._lock = asyncio.Lock()
        self.current_injection_id: str = ""
        self._last_run_findings: list[ConflictFinding] = []

    async def attach(self, graph_storage: BaseGraphStorage) -> None:
        original_upsert_edge = graph_storage.upsert_edge

        async def patched_upsert_edge(source_node_id, target_node_id, edge_data):
            new_description = str(edge_data.get("description", "")).strip()
            if new_description:
                try:
                    await self._check_edge(
                        graph_storage, source_node_id, target_node_id, new_description
                    )
                except Exception as exc:
                    print(f"[kepo_defense] conflict check failed: {exc}")
            return await original_upsert_edge(source_node_id, target_node_id, edge_data)

        graph_storage.upsert_edge = patched_upsert_edge

    async def _embed(self, text: str) -> np.ndarray:
        if text not in self._embed_cache:
            vec = await self.embed_func([text])
            self._embed_cache[text] = np.asarray(vec[0])
        return self._embed_cache[text]

    async def _check_edge(
        self,
        graph_storage: BaseGraphStorage,
        src: str,
        tgt: str,
        new_description: str,
    ) -> None:
        prior_descriptions = await self._collect_prior_descriptions(graph_storage, src, tgt)
        if not prior_descriptions:
            return

        new_vec = await self._embed(new_description)
        scored = []
        for desc in prior_descriptions:
            if desc == new_description:
                continue
            existing_vec = await self._embed(desc)
            scored.append((_cosine_sim(new_vec, existing_vec), desc))
        scored.sort(key=lambda pair: pair[0], reverse=True)

        for similarity, existing_description in scored[: self.max_compare]:
            if similarity < self.similarity_threshold:
                continue
            label, reason = await self._judge(src, tgt, existing_description, new_description)
            if label in ("DUPLICATE", "CONTRADICTION"):
                await self._record(
                    ConflictFinding(
                        src=src,
                        tgt=tgt,
                        existing_description=existing_description,
                        new_description=new_description,
                        label=label,
                        reason=reason,
                        similarity=similarity,
                        phase=self.phase,
                    )
                )

    async def _collect_prior_descriptions(
        self, graph_storage: BaseGraphStorage, src: str, tgt: str
    ) -> list[str]:
        descriptions: list[str] = []
        for a, b in ((src, tgt), (tgt, src)):
            edge = await graph_storage.get_edge(a, b)
            if edge and edge.get("description"):
                descriptions.append(str(edge["description"]).strip())
        return descriptions

    async def _judge(
        self, src: str, tgt: str, existing: str, new: str
    ) -> tuple[str, str]:
        prompt = JUDGE_PROMPT.format(src=src, tgt=tgt, existing=existing, new=new)
        raw = await self.judge_llm(prompt)
        return _parse_verdict(raw)

    async def _record(self, finding: ConflictFinding) -> None:
        finding.injection_id = self.current_injection_id
        self._last_run_findings.append(finding)
        async with self._lock:
            with self.findings_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(finding.to_json(), ensure_ascii=False) + "\n")
        print(
            f"[kepo_defense] {finding.label} on ({finding.src} -> {finding.tgt}) "
            f"sim={finding.similarity:.2f}: {finding.reason}"
        )

    def begin_injection(self, injection_id: str) -> None:
        """Call before inserting a document to attribute any resulting
        findings to it; read back via pop_injection_findings()."""
        self.current_injection_id = injection_id
        self._last_run_findings = []

    def pop_injection_findings(self) -> list[ConflictFinding]:
        findings = self._last_run_findings
        self._last_run_findings = []
        self.current_injection_id = ""
        return findings


async def attach_conflict_detector(
    rag,
    judge_llm: LLMFunc,
    findings_path: str = "kepo_findings.jsonl",
    similarity_threshold: float = 0.6,
    phase: str = "unspecified",
) -> EdgeConflictDetector:
    detector = EdgeConflictDetector(
        judge_llm=judge_llm,
        embed_func=rag.embedding_func,
        findings_path=findings_path,
        similarity_threshold=similarity_threshold,
        phase=phase,
    )
    await detector.attach(rag.chunk_entity_relation_graph)
    return detector