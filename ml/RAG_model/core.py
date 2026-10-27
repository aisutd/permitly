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
NY_INDEX = 'https://www.nysenate.gov/legislation/laws/BNK/A13-B'
NY_PDF = 'https://legislation.nysenate.gov/pdf/laws/BNKA13-B?full=true'
NY_SECTIONS = ('640', '641', '642', '643', '645', '646', '647', '648',
               '649', '650', '651', '651-a', '651-b', '652', '652-a', '652-b')
NY_SECTION_COUNT = len(NY_SECTIONS)
NY_HEADING = re.compile(r'(?m)^[^\S\r\n]*§[^\S\r\n]*(\d+(?:-[a-z])?)\.[^\S\r\n]*', re.I)


def ny_pdf_text():
    """Download the official complete article PDF; reject HTML challenge pages."""
    from io import BytesIO
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError
    try:
        response = requests.get(NY_PDF, timeout=40, headers={
            'User-Agent': 'PermitlyResearchDemo/0.1 (educational legal research)'})
        response.raise_for_status()
        if response.url != NY_PDF or not response.content.startswith(b'%PDF-'):
            raise ValueError('Expected the official Article 13-B PDF')
        pages = PdfReader(BytesIO(response.content)).pages
        if not pages:
            raise ValueError('Empty New York PDF')
        texts = [page.extract_text() or '' for page in pages]
        if any(not text.strip() for text in texts):
            raise ValueError('New York PDF contains a page without extractable text')
        return '\n'.join(texts)
    except (requests.RequestException, ValueError, PyPdfError) as exc:
        raise RuntimeError(f'Could not extract New York PDF: {exc}') from exc


def ny_sections(text):
    """Separate actual section bodies; the contents list has no § headings."""
    headings = list(NY_HEADING.finditer(text))
    labels = tuple(match[1].lower() for match in headings)
    preamble = text[:headings[0].start()] if headings else text
    if not (re.search(r'ARTICLE\s+(?:XIII|13)-B\b', preamble, re.I)
            and re.search(r'TRANSMITTERS\s+OF\s+MONEY', preamble, re.I)):
        raise ValueError('Expected the Article 13-B Transmitters of Money PDF')
    if labels != NY_SECTIONS:
        raise ValueError(f'Expected all 16 New York section bodies in order; found {labels}')
    sections = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[match.start():end].strip()
        if not text[match.end():end].strip():
            raise ValueError(f'Empty New York section {labels[index]}')
        sections.append((labels[index], body))
    return sections


def ny_records():
    """Validate every PDF section before returning any ingestible records."""
    try:
        sections = ny_sections(ny_pdf_text())
        records = []
        for section, text in sections:
            url = f'https://www.nysenate.gov/legislation/laws/BNK/{section.upper()}'
            records.extend((piece, citation, url) for piece, citation in
                           section_chunks(text, f'§ {section}'))
        return records
    except ValueError as exc:
        raise RuntimeError(f'New York article validation failed: {exc}') from exc


def replace_ny_records(collection, ids, texts, vectors, metadata, max_batch_size):
    """Replace the validated article, restoring its snapshot on a write failure.

    Chroma has no public multi-operation transaction. This compensates for
    ordinary exceptions; process termination or failed rollback needs recovery.
    """
    if len(ids) > max_batch_size:
        raise RuntimeError('New York exceeds one Chroma batch; index was not changed')
    previous = collection.get(where={'source_url': NY_INDEX},
                              include=['documents', 'metadatas', 'embeddings'])
    stale = sorted(set(previous['ids']) - set(ids))
    added = sorted(set(ids) - set(previous['ids']))
    try:
        collection.upsert(ids=ids, documents=texts, embeddings=vectors, metadatas=metadata)
        if stale:
            collection.delete(ids=stale)
    except Exception as exc:
        try:
            if previous['ids']:
                collection.upsert(ids=previous['ids'], documents=previous['documents'],
                                  embeddings=previous['embeddings'], metadatas=previous['metadatas'])
            if added:
                collection.delete(ids=added)
        except Exception as rollback_exc:
            raise RuntimeError('New York update and rollback failed; restore the index before retrying') from rollback_exc
        raise RuntimeError('New York update failed; previous article records restored') from exc


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


# Recognizes statute section headings for Texas (Sec. 152.001),
# Pennsylvania (Section 1. or Section 1.1.),
# and Delaware (§ 2304.) to split statutes into sections.
SECTION_HEADING = re.compile(
    r"(?m)^[^\S\r\n]*(?:"
    r"Sec\.[^\S\r\n]*\d+(?:\.\d+)*[A-Za-z]?\.?|"
    r"Section[^\S\r\n]+\d+(?:\.\d+)*\.|"
    r"§[^\S\r\n]*(?:\r?\n[^\S\r\n]*)?\d+(?:\.\d+)*[A-Za-z]?\."
    r")(?=[^\S\r\n]|$|[-—])"
)

PA_FIRST_SECTION = re.compile(
    r"(?m)^[^\S\r\n]*Section[^\S\r\n]+1\.(?!\d)"
)

def section_chunks(text, citation, limit=1300, overlap=150):
    """Split one known section without interpreting references as headings."""
    if limit <= 0 or not 0 <= overlap < limit:
        raise ValueError('Require limit > 0 and 0 <= overlap < limit')
    for start in range(0, len(text), limit - overlap):
        piece = text[start:start + limit].strip()
        if piece:
            yield piece, citation
        if start + limit >= len(text):
            break


def chunks(text, limit=1300, overlap=150):
    """Yield (passage, section citation), keeping different sections separate.

    Pennsylvania's contents page repeats its section headings. If we find a
    contents page and a second 'Section 1.', begin at the second occurrence.
    """
    if limit <= 0 or not 0 <= overlap < limit:
        raise ValueError('Require limit > 0 and 0 <= overlap < limit')

    if 'TABLE OF CONTENTS' in text.upper():
        first_sections = list(PA_FIRST_SECTION.finditer(text))
        if len(first_sections) >= 2:
            text = text[first_sections[1].start():]

    headings = list(SECTION_HEADING.finditer(text))
    if not headings:
        raise ValueError('No recognizable statute section headings; refusing to chunk unverified text')

    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section_text = text[match.start():end].strip()
        section_label = re.sub(r'\s+', ' ', match.group(0)).strip()
        if not section_text:
            continue
        yield from section_chunks(section_text, section_label, limit, overlap)


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
        is_ny = url in {NY_INDEX, NY_PDF}
        if is_ny:
            if entry['state'] != 'New York':
                raise RuntimeError('New York article must have state metadata New York')
            records = ny_records()
        else:
            body, fetched_url = fetch_text(url)
            records = [(piece, section, fetched_url) for piece, section in chunks(body)]
        if not records:
            raise RuntimeError(f'No usable chunks from {url}')
        ids: list[str] = []
        texts: list[str] = []
        metadata: list[Metadata] = []
        retrieved = datetime.now(timezone.utc).date().isoformat()
        for idx, (piece, section, fetched_url) in enumerate(records):
            ids.append(hashlib.sha256(f'{url}:{idx}:{piece}'.encode()).hexdigest())
            texts.append(piece)
            metadata.append({'state': entry['state'], 'name': entry['name'], 'url': fetched_url, 'source_url': NY_INDEX if is_ny else url, 'section': section, 'source_type': 'statute', 'retrieved': retrieved})
        if is_ny:
            for meta in metadata:
                meta['pdf_url'] = NY_PDF
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        if is_ny:
            replace_ny_records(collection, ids, texts, vectors, metadata, db.get_max_batch_size())
            count += len(ids)
            print(f'Indexed {len(ids)} chunks from {NY_SECTION_COUNT} New York sections')
            continue
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


# Retrieval-only helpers: no changes to ingestion or stored metadata.
CITATION = re.compile(r'(?:\bSection\s+|\bSec\.\s*|§\s*)(\d+(?:\.\d+)*(?:-[a-z]|[a-z])?)(?![\w-]|\.\d)', re.I)


def section_id(citation):
    match = CITATION.fullmatch(citation.strip().rstrip('.'))
    return match[1].lower() if match else None


def opening_heading(document, citation):
    """Read a real citation at the start, never a continuation's first line."""
    match = CITATION.match(document.lstrip())
    if not match or match[1].lower() != section_id(citation):
        return None
    rest = document.lstrip()[match.end():].lstrip('. \t\n\r\u00a0')
    return re.split(r'--|[.\n]', rest, maxsplit=1)[0].strip()


def ordered_section(records):
    """Start at the heading and follow the existing overlapping chunk text."""
    remaining = list(records)
    opening = next((i for i, (doc, meta) in enumerate(remaining)
                    if opening_heading(doc, meta['section']) is not None), 0)
    ordered = [remaining.pop(opening)] if remaining else []
    while remaining:
        last = ordered[-1][0].rstrip()
        def overlap(record):
            doc = record[0].lstrip()
            return next((size for size in range(min(len(last), len(doc)) - 1, 0, -1)
                         if last.endswith(doc[:size])), 0)
        following = max(range(len(remaining)), key=lambda i: overlap(remaining[i]))
        ordered.append(remaining.pop(following))
    return ordered


def retrieval_terms(text):
    stop = {'a', 'an', 'the', 'of', 'in', 'for', 'to', 'and', 'or', 'is', 'are',
            'what', 'who', 'how', 'does', 'do', 'under', 'law', 'banking', 'this',
            'that', 'be', 'it', 'its', 'on', 'by', 'with', 'as'}
    aliases = {'transmitter': 'transmit', 'transmitters': 'transmit',
               'transmission': 'transmit', 'transmitting': 'transmit',
               'licensed': 'license', 'licensee': 'license', 'licensees': 'license',
               'licensing': 'license', 'licenses': 'license',
               'needs': 'require', 'need': 'require', 'required': 'require',
               'requirements': 'require', 'requirement': 'require',
               'exemption': 'exempt',
                'exemptions': 'exempt',
                'exempted': 'exempt',
                'exempting': 'exempt',}
    return {aliases.get(word, word[:-1] if word.endswith('s') and len(word) > 3 else word)
            for word in re.findall(r'[a-z]+', text.lower()) if word not in stop}


def retrieve(collection, question, state, model, k=4):
    """Resolve explicit citations, otherwise rerank semantic candidates."""
    if k <= 0:
        raise ValueError('k must be positive')
    where = {'state': state} if state else None
    stored = collection.get(where=where, include=['documents', 'metadatas'])
    if stored['documents'] is None or stored['metadatas'] is None or len(stored['documents']) != len(stored['metadatas']):
        raise RuntimeError('Index is missing source documents or metadata.')
    records = list(zip(stored['documents'], stored['metadatas']))
    requested = list(dict.fromkeys(m[1].lower() for m in CITATION.finditer(question)))
    if requested:
        if len(requested) > 1:
            return [], 'Please request one section at a time.'
        matches = [(doc, meta) for doc, meta in records
                   if section_id(meta['section']) == requested[0]]
        states = {meta['state'] for _, meta in matches}
        if not state and len(states) > 1:
            return [], 'This section number occurs in multiple states. Select --state: ' + ', '.join(sorted(states))
        groups = {(meta['state'], meta.get('source_url'), meta['url']) for _, meta in matches}
        if len(groups) > 1:
            return [], 'This section occurs in multiple statute sources. Please specify the statute source.'
        if not matches:
            return [], 'No matching section was found in the selected state or index.'
        return ordered_section(matches), None
    if not records:
        return [], 'No matching statute passages were found. Add an official statute source for this state.'
    embedding = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=embedding, n_results=min(len(records), max(100, k)),
                               where=where, include=['documents', 'metadatas', 'distances'])
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    distances = results['distances'][0]
    if not len(docs) == len(metas) == len(distances):
        raise RuntimeError('Retrieved passages are missing metadata or similarity distances.')
    def group(meta):
        return (meta['state'], meta.get('source_url'), meta['url'], meta['section'])
    headings = {group(meta): heading for doc, meta in records
                if (heading := opening_heading(doc, meta['section'])) is not None}
    state_terms = set().union(*(retrieval_terms(meta['state']) for _, meta in records))
    terms = retrieval_terms(question) - state_terms
    def score(item):
        doc, meta, distance = item
        heading_terms = retrieval_terms(headings.get(group(meta), ''))
        keywords = len(terms & retrieval_terms(doc)) / max(1, len(terms))
        heading = len(terms & heading_terms) / max(1, len(terms))
        return 1 / (1 + max(0, distance)) + 0.25 * keywords + 1.2 * heading
    candidates = list(zip(docs, metas, distances))
    candidates.sort(key=score, reverse=True)  # Stable: keep semantic order on ties.
    return [(doc, meta) for doc, meta, _ in candidates[:k]], None


def ask(question, state=None, k=4): #Finds passages whose embeddings are similar to your question.
    db = chromadb.PersistentClient(path=str(ROOT / '.chroma'))
    try:
        collection = db.get_collection('statutes')
    except Exception as exc:
        raise RuntimeError('No statute index. Run python main.py ingest from rag-model-ss-demo first.') from exc
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    passages, message = retrieve(collection, question, state, model, k)
    if message:
        return message
    docs = [doc for doc, _ in passages]
    metas = [meta for _, meta in passages]
    # Fully offline extractive answer: quote the most relevant retrieved passages.
    # No generative LLM or API key is required.
    lines = ['RELEVANT STATUTE EXCERPTS (local, API-free retrieval):']
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        excerpt = doc[:850].strip()
        if len(doc) > 850:
            excerpt += ' ... [excerpt truncated]'
        lines.append(f'\n[{i}] {meta["name"]} — {meta["section"]}\n'
                     f'{excerpt}\nSource: {meta["url"]}')
    lines.append('\nThese are retrieved excerpts, not a verified legal conclusion. '
                 'Check the linked official law for full context and current wording.')
    return '\n'.join(lines)
