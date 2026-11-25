# Permitly

## Description

Permitly is an AI-driven navigator for state-specific U.S. Money Transmitter Licensing requirements. It assesses licensing risk, extracts structured information from statutes, and uses grounded retrieval with citations so users can find relevant requirements without treating the platform as legal advice.

## Planned Technologies

- Python, JavaScript, and SQL
- React or Next.js with D3.js
- FastAPI or Flask with PostgreSQL
- PyTorch, Hugging Face, spaCy, and retrieval-augmented generation

## Docker Setup

Make sure Docker Desktop is installed and running.

```bash
docker compose up -d
docker compose down
docker compose ps
```

This is a generic starter configuration. The team can add project-specific dependencies and startup commands later.

## RAG Statute Re-ingestion

The re-ingestion script updates the statute data used by Permitly's RAG model.

### Install Dependencies

From the project root, run:

```bash
python -m pip install -r requirements.txt
```

### Run Re-ingestion

From the project root, run:

```bash
python ml/RAG_model/main.py ingest
```

The script automatically:

- Fetches the latest statute text from enabled sources in sources.csv.
- Splits the statute text into smaller chunks.
- Generates embeddings for each chunk.
- Updates the ChromaDB vector database.
- Removes outdated chunks from refreshed sources.
- Updates retrieval dates for citations.

### Supported States

- Texas
- Pennsylvania
- New York

### Testing

Re-ingestion was tested by running the ingestion command twice.
Both runs successfully processed 231 chunks, and the database
contained 231 stored chunks after the second run.

The chunk count may change when statutes or source configurations
are updated.