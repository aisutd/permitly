
import csv
import json
import sys
from pathlib import Path

# Import the existing RAG model
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent))

from core import ROOT, MODEL_NAME, retrieve, ask
import chromadb
from sentence_transformers import SentenceTransformer


def main():
    # Connect to the existing statute database
    db = chromadb.PersistentClient(
        path=str(ROOT / ".chroma")
    )
    collection = db.get_collection("statutes")

    # Load the embedding model
    model = SentenceTransformer(
        MODEL_NAME, local_files_only=True
    )

    # Load the evaluation questions
    with open(
        EVAL_DIR / "questions.csv",
        encoding="utf-8-sig"
    ) as file:
        questions = list(csv.DictReader(file))

    # Collect known citations from the database
    metadata = collection.get(
        include=["metadatas"]
    )["metadatas"]

    valid_sources = {
        (m["state"], m["section"], m["url"])
        for m in metadata
    }

    results = []
    hits = 0
    first_hits = 0
    valid_citations = 0

    for row in questions:
        question = row["question"]
        state = row["state"]
        expected = row["expected_section"]

        passages, message = retrieve(
            collection, question, state, model, 4
        )

        retrieved = [meta for _, meta in passages]

        sections = [
            meta["section"] for meta in retrieved
        ]

        hit = any(
            meta["state"] == state
            and meta["section"] == expected
            for meta in retrieved
        )

        first_hit = bool(retrieved) and (
            retrieved[0]["state"] == state
            and retrieved[0]["section"] == expected
        )

        answer = ask(question, state=state, k=4)

        citations = bool(retrieved) and all(
            (
                meta["state"],
                meta["section"],
                meta["url"]
            ) in valid_sources
            and f'{meta["name"]} — {meta["section"]}' in answer
            and f'Source: {meta["url"]}' in answer
            for meta in retrieved
        )

        hits += int(hit)
        first_hits += int(first_hit)
        valid_citations += int(citations)

        results.append({
            "id": row["id"],
            "question": question,
            "state": state,
            "expected_section": expected,
            "retrieved_sections": sections,
            "retrieval_hit": hit,
            "hit_at_1": first_hit,
            "valid_citations": citations,
            "answer": answer
        })

        status = "PASS" if hit else "FAIL"
        print(f'{row["id"]}: {status}')

    total = len(questions)

    summary = {
        "total_questions": total,
        "retrieval_hit_rate": round(hits / total * 100, 2),
        "hit_at_1": round(first_hits / total * 100, 2),
        "valid_citation_rate": round(
            valid_citations / total * 100, 2
        )
    }

    print("\nEVALUATION RESULTS")
    print(json.dumps(summary, indent=2))

    with open(
        EVAL_DIR / "results.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {"summary": summary, "results": results},
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nResults saved to results.json")


if __name__ == "__main__":
    main()
