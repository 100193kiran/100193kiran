from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    from rank_bm25 import BM25Okapi  # lightweight BM25 implementation
except Exception:  # pragma: no cover - optional during import time
    BM25Okapi = None  # type: ignore


@dataclass
class RetrievalQAConfig:
    max_contexts: int = 8
    retriever: str = "tfidf"  # "tfidf" | "bm25"
    # BM25 parameters (used when retriever == "bm25")
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # Generator options (answer synthesis)
    generator: str = "template"  # "template" | "t5"
    t5_model_name: str = "t5-small"  # used if generator == "t5"
    max_answer_tokens: int = 64


class RetrievalQABot:
    def __init__(self, tables: Dict[str, pd.DataFrame], config: Optional[RetrievalQAConfig] = None) -> None:
        self.config = config or RetrievalQAConfig()
        self.tables = tables
        self.documents: List[str] = []
        self.doc_meta: List[Dict[str, Any]] = []
        # TF-IDF state
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None
        # BM25 state
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_tokens: List[List[str]] = []
        self._build_knowledge_base()

    def _build_knowledge_base(self) -> None:
        docs: List[str] = []
        meta: List[Dict[str, Any]] = []

        fights = self.tables.get("fights", pd.DataFrame())
        for _, row in fights.iterrows():
            text = " ".join(
                filter(
                    None,
                    [
                        f"Fight {row.get('fight_id','')}:",
                        row.get("blue_bot_name"),
                        "vs",
                        row.get("red_bot_name"),
                        "- Winner:",
                        row.get("winner_bot_name"),
                        row.get("method"),
                        row.get("notes"),
                        row.get("series"),
                        row.get("season"),
                    ],
                )
            )
            docs.append(text)
            meta.append({"table": "fights", "row": row.to_dict()})

        bots = self.tables.get("bots", pd.DataFrame())
        for _, row in bots.iterrows():
            text = " ".join(
                filter(
                    None,
                    [
                        f"Bot {row.get('name','')}",
                        row.get("team_name"),
                        row.get("primary_weapon"),
                        row.get("drive_type"),
                        row.get("country"),
                        row.get("active_years"),
                        row.get("notes"),
                        ",".join(row.get("aliases") or []) if isinstance(row.get("aliases"), list) else None,
                    ],
                )
            )
            docs.append(text)
            meta.append({"table": "bots", "row": row.to_dict()})

        self.documents = docs
        self.doc_meta = meta
        if not docs:
            self._matrix = None
            self._bm25 = None
            return

        # Build retriever index according to configuration
        if self.config.retriever == "bm25" and BM25Okapi is not None:
            # Simple whitespace tokenization with lower-casing
            self._bm25_tokens = [self._tokenize_for_bm25(text) for text in docs]
            self._bm25 = BM25Okapi(self._bm25_tokens, k1=self.config.bm25_k1, b=self.config.bm25_b)
            self._vectorizer = None
            self._matrix = None
        else:
            # Default to TF-IDF
            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self._vectorizer.fit_transform(docs)
            self._bm25 = None

    def answer(self, question: str) -> Dict[str, Any]:
        if not self.documents:
            return {"answer": "No knowledge loaded.", "contexts": []}

        contexts = self._retrieve(question)
        answer_text = self._generate_answer(question, contexts)
        return {"answer": answer_text, "contexts": contexts}

    # --- Retrieval ---
    def _retrieve(self, question: str) -> List[Dict[str, Any]]:
        if self.config.retriever == "bm25" and self._bm25 is not None:
            query_tokens = self._tokenize_for_bm25(question)
            scores = self._bm25.get_scores(query_tokens)
            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            top = order[: self.config.max_contexts]
            contexts = [
                self.doc_meta[i] | {"text": self.documents[i], "score": float(scores[i])}
                for i in top
            ]
            return contexts

        # TF-IDF fallback
        if self._vectorizer is None or self._matrix is None:
            return []
        q_vec = self._vectorizer.transform([question])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sims.argsort()[::-1][: self.config.max_contexts]
        return [self.doc_meta[i] | {"text": self.documents[i], "score": float(sims[i])} for i in ranked]

    @staticmethod
    def _tokenize_for_bm25(text: str) -> List[str]:
        return [t for t in (text or "").lower().split() if t]

    # --- Generation ---
    def _generate_answer(self, question: str, contexts: List[Dict[str, Any]]) -> str:
        if self.config.generator == "t5":
            generated = self._try_generate_with_t5(question, contexts)
            if generated:
                return generated
        # Fallback to template
        return self._template_answer(contexts)

    def _template_answer(self, contexts: List[Dict[str, Any]]) -> str:
        best = contexts[0] if contexts else None
        if best and best.get("table") == "fights":
            row = best["row"]
            winner = row.get("winner_bot_name") or row.get("winner_bot_id")
            blue = row.get("blue_bot_name")
            red = row.get("red_bot_name")
            method = row.get("method")
            return (
                f"{winner} defeated {blue if winner != blue else red} via {method}."
                if winner
                else "Match result unknown."
            )
        return best["text"] if best else "No relevant context found."

    def _try_generate_with_t5(self, question: str, contexts: List[Dict[str, Any]]) -> Optional[str]:
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        except Exception:
            return None

        if not contexts:
            return None

        # Build a compact prompt from top contexts
        top_ctx_text = "\n".join(ctx["text"] for ctx in contexts[:3])
        prompt = (
            "You are a concise Q&A bot about robot combat matches.\n"
            "Answer the question using the provided context.\n\n"
            f"Context:\n{top_ctx_text}\n\nQuestion: {question}\nAnswer:"
        )

        try:
            tok = AutoTokenizer.from_pretrained(self.config.t5_model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(self.config.t5_model_name)
            input_ids = tok(prompt, return_tensors="pt", truncation=True).input_ids
            out = model.generate(input_ids, max_new_tokens=self.config.max_answer_tokens)
            text = tok.decode(out[0], skip_special_tokens=True)
            return text.strip()
        except Exception:
            # If model loading/generation fails (no internet, missing deps), fallback
            return None
