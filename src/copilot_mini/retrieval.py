"""Lokale, autarke Retrieval-Schicht über den mitgelieferten Nextcloud-Doku-Index.

Dieselbe Embedding-Technik wie der SIMOSphere-Haufe-Retriever (multilingual-e5-large, 1024-dim,
FAISS Inner-Product über normalisierte Vektoren = Cosine), aber bewusst self-contained und schlank:
reines Dense-Retrieval, kein zweiter Sparse-Zweig und kein Cross-Encoder. Ein BM25/Reranker-Hybrid
lohnt hier nicht — in Tests gegen genau diese Doku liefert Dense allein die besseren Treffer, ohne
ein zweites bzw. drittes Modell ins Image zu ziehen. (Ein Reranker-Hybrid bleibt eine Option für
eine spätere Version, wenn Messungen ihn rechtfertigen.)

Das Embedding-Modell wird lazy und offline geladen (erst bei der ersten Frage), damit der Container
schnell startet und ohne Netz auskommt.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

#: Passend zum gebauten Index (build mit passage:-Prefix, query mit query:-Prefix).
_MODEL = "intfloat/multilingual-e5-large"
_EXPECTED_DIM = 1024


@dataclass(frozen=True)
class Hit:
    """Ein Suchtreffer mit allem, was eine belegte Antwort braucht."""

    doc_id: str
    title: str
    text: str
    source_url: str
    score: float


class Retriever:
    """Kapselt Index, Metadaten und (lazy) das Embedding-Modell."""

    def __init__(self, data_dir: str | Path) -> None:
        data = Path(data_dir)
        self._index = faiss.read_index(str(data / "nextcloud.faiss"))
        if self._index.d != _EXPECTED_DIM:
            raise ValueError(f"Index-Dimension {self._index.d} != erwartet {_EXPECTED_DIM}")
        with (data / "nextcloud_meta.jsonl").open(encoding="utf-8") as f:
            self._meta: list[dict] = [json.loads(line) for line in f if line.strip()]
        if len(self._meta) != self._index.ntotal:
            raise ValueError(f"Meta ({len(self._meta)}) und Index ({self._index.ntotal}) passen nicht")
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(_MODEL, device="cpu")
        return self._model

    def search(self, query: str, k: int = 5) -> list[Hit]:
        """Liefert die ``k`` relevantesten Doku-Stellen zur Frage (Dense-Cosine, absteigend)."""
        query = (query or "").strip()
        if not query:
            return []
        model = self._ensure_model()
        vec = np.asarray(model.encode([f"query: {query}"], normalize_embeddings=True), dtype="float32")
        scores, ids = self._index.search(vec, k)
        hits: list[Hit] = []
        for idx, score in zip(ids[0], scores[0], strict=False):
            if idx < 0:
                continue
            m = self._meta[int(idx)]
            hits.append(
                Hit(
                    doc_id=m.get("doc_id", ""),
                    title=m.get("title", ""),
                    text=m.get("text", ""),
                    source_url=m.get("source_url", ""),
                    score=round(float(score), 4),
                )
            )
        return hits
