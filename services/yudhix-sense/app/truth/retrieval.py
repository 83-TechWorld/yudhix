"""Retrieval over the workspace's knowledge base (the RAG "ground truth"): hybrid search.

  keyword   BM25 over title + category + clause + official statement (always on)
  meaning   cosine similarity of embeddings, when an embedding model is available: the workspace's
            cloud provider if it has one (OpenAI, Gemini, Mistral), else a local Ollama model
            (nomic-embed-text). Claude has no embeddings API, so with Claude the local model is used.
  fusion    Reciprocal Rank Fusion (score = sum of 1 / (60 + rank) over both rankings), which needs no
            score calibration between the two.

Facts stay in Postgres. Fact vectors are cached in knowledge_embedding per embedding model and
recomputed only when a fact's text changes. Small knowledge bases (up to a few thousand clauses) are
compared in Python; no vector database is needed.
"""
import hashlib
import logging
import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.core.text import tokens

logger = logging.getLogger(__name__)
RRF_K = 60
EMBED_BATCH = 64


@dataclass
class Hit:
    doc: Dict
    score: float
    overlap: float  # share of the claim's terms found in the doc, 0..1
    similarity: float = 0.0  # cosine similarity of meaning (embeddings), 0 when keyword-only


class KnowledgeIndex:
    K1, B = 1.4, 0.75

    def __init__(self, docs: List[Dict]):
        self.docs = docs
        self.doc_tokens = [tokens(" ".join(str(d.get(k) or "") for k in
                                           ("document_title", "category", "official_statement", "clause_ref")))
                           for d in docs]
        self.avg_len = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))
        df: Counter = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self._pos = {id(d): i for i, d in enumerate(docs)}

    # --------------------------------------------------------------- meaning (embeddings)
    vectors: Optional[List[List[float]]] = None
    model: Optional[str] = None

    @classmethod
    def build(cls, tenant_id: str, docs: List[Dict]) -> "KnowledgeIndex":
        """Keyword index plus fact vectors when an embedding model is available."""
        index = cls(docs)
        try:
            index._load_vectors(tenant_id)
        except Exception:
            logger.exception("Meaning-based search unavailable; using keyword search only")
            index.vectors = None
        return index

    def _load_vectors(self, tenant_id: str) -> None:
        from app.core import llm
        from app.core.database import cursor, fetch_all
        if not self.docs or not llm.embedder():
            return
        texts = [_doc_text(d) for d in self.docs]
        hashes = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
        probe = llm.embed([texts[0][:2000]])  # also tells us the model name
        if not probe:
            return
        model = probe[0]
        stored = {(str(r["knowledge_id"]), r["content_hash"]): r["vector"] for r in fetch_all(
            "SELECT knowledge_id, content_hash, vector FROM knowledge_embedding WHERE tenant_id = %s AND model = %s",
            (tenant_id, model))}
        vectors: List[Optional[List[float]]] = [stored.get((str(d["id"]), h)) for d, h in zip(self.docs, hashes)]
        missing = [i for i, v in enumerate(vectors) if v is None]
        for start in range(0, len(missing), EMBED_BATCH):
            chunk = missing[start:start + EMBED_BATCH]
            got = llm.embed([texts[i][:8000] for i in chunk])
            if not got or got[0] != model:
                return  # embedder changed mid-way: stay keyword-only for this check
            with cursor(commit=True) as cur:
                for i, vec in zip(chunk, got[1]):
                    vectors[i] = vec
                    cur.execute(
                        """INSERT INTO knowledge_embedding (knowledge_id, model, tenant_id, content_hash, vector)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (knowledge_id, model) DO UPDATE SET content_hash = EXCLUDED.content_hash,
                               vector = EXCLUDED.vector, created_at = now()""",
                        (self.docs[i]["id"], model, tenant_id, hashes[i], vec))
        self.vectors, self.model = [list(map(float, v)) for v in vectors], model

    def _similarities(self, query: str) -> Optional[List[float]]:
        if not self.vectors:
            return None
        from app.core import llm
        got = llm.embed([query[:2000]])
        if not got or got[0] != self.model:
            return None
        return [cosine(got[1][0], v) for v in self.vectors]

    # --------------------------------------------------------------- search
    def search(self, query: str, k: int = 3) -> List[Hit]:
        """Top k facts by keyword and meaning, fused with Reciprocal Rank Fusion."""
        if not self.docs:
            return []
        bm25 = self._bm25(query)
        sims = self._similarities(query)
        if not sims:
            return bm25[:k]
        q = set(tokens(query))
        fused: Dict[int, float] = Counter()
        for rank, h in enumerate(bm25):
            fused[self._pos[id(h.doc)]] += 1 / (RRF_K + rank + 1)
        by_meaning = sorted(range(len(self.docs)), key=lambda i: -sims[i])
        for rank, i in enumerate(by_meaning[:max(10, 3 * k)]):
            fused[i] += 1 / (RRF_K + rank + 1)
        keyword = {self._pos[id(h.doc)]: h for h in bm25}
        out = []
        for i, score in sorted(fused.items(), key=lambda x: -x[1])[:k]:
            toks = set(self.doc_tokens[i])
            overlap = keyword[i].overlap if i in keyword else (len(q & toks) / len(q) if q else 0.0)
            out.append(Hit(doc=self.docs[i], score=score, overlap=overlap, similarity=max(0.0, sims[i])))
        return out

    def _bm25(self, query: str) -> List[Hit]:
        q = set(tokens(query))
        if not q or not self.docs:
            return []
        hits = []
        for doc, toks in zip(self.docs, self.doc_tokens):
            tf = Counter(toks)
            score = 0.0
            for term in q:
                if term not in tf:
                    continue
                f = tf[term]
                score += self.idf.get(term, 0) * f * (self.K1 + 1) / (
                    f + self.K1 * (1 - self.B + self.B * len(toks) / max(1, self.avg_len)))
            if score > 0:
                hits.append(Hit(doc=doc, score=score, overlap=len(q & set(toks)) / len(q)))
        hits.sort(key=lambda h: -h.score)
        return hits


def _doc_text(d: Dict) -> str:
    return " · ".join(str(d.get(k) or "") for k in ("document_title", "category", "clause_ref", "official_statement")
                      if d.get(k))


def cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
