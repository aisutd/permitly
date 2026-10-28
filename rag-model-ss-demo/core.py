import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import chromadb
from chromadb.api.types import Metadata
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
ALLOWED = {'statue', 'statute'}  # exact sheet classification, including its typo


def sources(): # Reads sources.csv to decide which websites to use.
    with (ROOT / 'sources.csv').open(newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    return [r for r in rows if r['source_type'].strip().lower() in ALLOWED and r['enabled'].lower() == 'true' and r['url'].strip()]


def extract_html(content): # Removes menus and extracts the page’s main text.
    """Extract document content without menus, preserving heading boundaries."""
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
        tag.decompose()
    for element in soup.select(
        '[role="navigation"], .navbar, .breadcrumb, .sidebar, .menu, .site-header'
    ):
        element.decompose()
    main = (soup.find('main') or soup.find('article')
            or soup.find(id='content') or soup.find('body'))
    if main is None:
        raise ValueError('Could not find statute content')
    body = main.get_text('\n', strip=True)
    body = re.sub(r'[ \t]+', ' ', body)
    return re.sub(r'\n{3,}', '\n\n', body).strip()


def fetch_text(url): # Downloads a page, checks for statute text, and tries the Texas fallback if needed.
    """Validate Texas chapter content and try the legislature's resource host."""
    parsed = urlparse(url)
    chapter = re.fullmatch(
        r'/docs/([a-z]+)/(?:htm|pdf)/([a-z]+)\.(\d+[a-z]*)\.(?:htm|pdf)',
        parsed.path, re.I,
    ) if parsed.hostname == 'statutes.capitol.texas.gov' else None
    candidates = [url]
    if chapter:
        code, _, number = chapter.groups()
        candidates.append(
            f'https://tcss.legis.texas.gov/resources/{code.lower()}/htm/{code.lower()}.{number.lower()}.htm'
        )
    failures = []
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=40, headers={
                'User-Agent': 'PermitlyResearchDemo/0.1 (educational legal research)'})
            response.raise_for_status()
            # A .pdf URL can redirect to an HTML homepage; inspect the bytes.
            if response.content.lstrip().startswith(b'%PDF-'):
                from io import BytesIO
                from pypdf import PdfReader
                body = '\n'.join(page.extract_text() or ''
                                 for page in PdfReader(BytesIO(response.content)).pages)
            else:
                body = extract_html(response.content)
            if len(body) < 500:
                raise ValueError('Too little extracted text')
            if chapter and not re.search(
                rf'\bSec\.\s*{re.escape(chapter[3])}\.\d+', body, re.I
            ):
                raise ValueError('Texas statute sections were not found; refusing to index navigation text')
            return body, response.url
        except (requests.RequestException, ValueError) as exc:
            failures.append(f'{candidate}: {exc}')
    raise RuntimeError('Could not fetch usable statute text. ' + '; '.join(failures))


def chunks(text, limit=1300, overlap=150): # Splits long text into smaller, overlapping pieces.
    if limit <= 0 or not 0 <= overlap < limit:
        raise ValueError('Require limit > 0 and 0 <= overlap < limit')
    # Keep section boundaries when they appear in official legal text.
    parts = re.split(r'(?=\bSec\.\s+\d+[A-Za-z0-9.]*\s)', text, flags=re.I)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        for start in range(0, len(part), limit - overlap):
            piece = part[start:start + limit].strip()
            if len(piece) >= 80:
                match = re.search(r'\bSec\.\s+[\dA-Za-z.]+', part[:150], re.I)
                yield piece, match.group(0) if match else 'Section not identified'
            if start + limit >= len(part):
                break


def ingest(): # Converts those pieces into embeddings and saves them in Chroma.
    entries = sources()
    if not entries:
        raise RuntimeError('No enabled statute URLs in sources.csv')
    db = chromadb.PersistentClient(path=str(ROOT / '.chroma'))
    collection = db.get_or_create_collection('statutes')
    model = SentenceTransformer(MODEL_NAME)
    count = 0
    for entry in entries:
        url = entry['url']
        print(f'Fetching {entry["name"]}: {url}')
        body, fetched_url = fetch_text(url)
        records = list(chunks(body))
        if not records:
            raise RuntimeError(f'No usable chunks from {url}')
        ids: list[str] = []
        texts: list[str] = []
        metadata: list[Metadata] = []
        retrieved = datetime.now(timezone.utc).date().isoformat()
        for idx, (piece, section) in enumerate(records):
            ids.append(hashlib.sha256(f'{url}:{idx}:{piece}'.encode()).hexdigest())
            texts.append(piece)
            metadata.append({'state': entry['state'], 'name': entry['name'], 'url': fetched_url, 'source_url': url, 'section': section, 'source_type': 'statute', 'retrieved': retrieved})
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        previous = collection.get(where={'$or': [{'source_url': url}, {'url': url}]}, include=[])['ids']
        for start in range(0, len(ids), 100):
            stop = start + 100
            collection.upsert(ids=ids[start:stop], documents=texts[start:stop], embeddings=vectors[start:stop], metadatas=metadata[start:stop])
        stale = sorted(set(previous) - set(ids))
        if stale:
            collection.delete(ids=stale)
        count += len(ids)
        print(f'Indexed {len(ids)} chunks')
    print(f'Finished: {count} chunks from {len(entries)} enabled statute sources')


def retrieve(question, state=None, k=4): #Recall Function
    """Return ranked passages with chunk IDs for answering and evaluation."""
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError('k must be a positive integer')
    db = chromadb.PersistentClient(path=str(ROOT / '.chroma'))
    try:
        collection = db.get_collection('statutes')
    except Exception as exc:
        raise RuntimeError('No statute index. Run python main.py ingest from rag-model-ss-demo first.') from exc
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    embedding = model.encode([question], normalize_embeddings=True).tolist()
    where = {'state': state} if state else None
    results = collection.query(query_embeddings=embedding, n_results=k, where=where, include=['documents', 'metadatas'])
    document_groups = results.get('documents')
    metadata_groups = results.get('metadatas')
    if not document_groups or not document_groups[0]:
        return []
    if not metadata_groups or len(metadata_groups[0]) != len(document_groups[0]):
        raise RuntimeError('Index is missing source metadata. Run python -m permitly_rag ingest again.')
    docs = document_groups[0]
    metas = metadata_groups[0]
    return [
        {'id': chunk_id, 'document': doc, 'metadata': meta}
        for chunk_id, doc, meta in zip(results['ids'][0], docs, metas)
    ]


def ask(question, state=None, k=4):
    passages = retrieve(question, state=state, k=k)
    if not passages:
        return 'No matching statute passages were found. Add an official statute source for this state.'
    # Fully offline extractive answer: quote the most relevant retrieved passages.
    # No generative LLM or API key is required.
    lines = ['RELEVANT STATUTE EXCERPTS (local, API-free retrieval):']
    for i, passage in enumerate(passages, 1):
        doc, meta = passage['document'], passage['metadata']
        excerpt = doc[:850].strip()
        if len(doc) > 850:
            excerpt += ' ... [excerpt truncated]'
        lines.append(f'\n[{i}] {meta["name"]} — {meta["section"]}\n'
                     f'{excerpt}\nSource: {meta["url"]}')
    lines.append('\nThese are retrieved excerpts, not a verified legal conclusion. '
                 'Check the linked official law for full context and current wording.')
    return '\n'.join(lines)
