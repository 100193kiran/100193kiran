from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievalQAConfig:
    max_contexts: int = 8


class RetrievalQABot:
    def __init__(self, tables: Dict[str, pd.DataFrame], config: Optional[RetrievalQAConfig] = None) -> None:
        self.config = config or RetrievalQAConfig()
        self.tables = tables
        self.documents: List[str] = []
        self.doc_meta: List[Dict[str, Any]] = []
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = None
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
            return
        self._matrix = self._vectorizer.fit_transform(docs)

    def answer(self, question: str) -> Dict[str, Any]:
        if self._matrix is None or not self.documents:
            return {"answer": "No knowledge loaded.", "contexts": []}
        q_vec = self._vectorizer.transform([question])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sims.argsort()[::-1][: self.config.max_contexts]
        contexts = [self.doc_meta[i] | {"text": self.documents[i], "score": float(sims[i])} for i in ranked]

        # Simple template-based synthesis
        best = contexts[0] if contexts else None
        if best and best.get("table") == "fights":
            row = best["row"]
            winner = row.get("winner_bot_name") or row.get("winner_bot_id")
            blue = row.get("blue_bot_name")
            red = row.get("red_bot_name")
            method = row.get("method")
            summary = f"{winner} defeated {blue if winner!=blue else red} via {method}." if winner else "Match result unknown."
        else:
            summary = best["text"] if best else "No relevant context found."

        return {"answer": summary, "contexts": contexts}
