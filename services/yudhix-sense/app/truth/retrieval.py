"""Retrieval over the tenant's brand knowledge base (the RAG "ground truth").

BM25 over title + category + official statement. Small knowledge bases (tens to a few
thousand clauses) don't need a vector store; pgvector + bge-m3 embeddings is the planned
upgrade once tenants upload large document sets.
"""
import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from app.core.text import tokens


@dataclass
class Hit:
    doc: Dict
    score: float
    overlap: float  # share of the claim's terms found in the doc, 0..1


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

    def search(self, query: str, k: int = 3) -> List[Hit]:
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
        return hits[:k]
