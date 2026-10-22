"""Offline PDF extraction, validation, metadata, and rollback tests."""
import copy
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import numpy as np
from pypdf import PdfWriter

import core

SECTIONS = core.NY_SECTIONS


def article_text(sections=SECTIONS):
    contents = '\n'.join(f'{s}. Title.' for s in sections)
    bodies = '\n'.join(f'  § {s}. Short provision.' for s in sections)
    return 'ARTICLE XIII-B\nTRANSMITTERS OF MONEY\nSection ' + contents + '\n' + bodies


class ExtractionTests(unittest.TestCase):
    def test_all_sections_contents_removed_and_short_sections_preserved(self):
        text = article_text()
        sections = core.ny_sections(text)
        self.assertEqual(tuple(s for s, _ in sections), SECTIONS)
        with patch.object(core, 'ny_pdf_text', return_value=text):
            records = core.ny_records()
        self.assertEqual(len(records), 16)
        for (section, body), (piece, citation, url) in zip(sections, records):
            self.assertEqual(piece, body)
            self.assertEqual(citation, f'§ {section}')
            self.assertTrue(url.endswith('/' + section.upper()))
            self.assertLess(len(piece), 80)
            self.assertNotIn('Title.', piece)

    def test_missing_duplicate_foreign_and_empty_sections_rejected(self):
        for text in [article_text(SECTIONS[:-1]), article_text(SECTIONS + ('652-b',)),
                     article_text().replace('XIII-B', 'XIII-C'),
                     article_text().replace('§ 652-b. Short provision.', '§ 652-b.')]:
            with self.subTest(text=text[-100:]), self.assertRaises(ValueError):
                core.ny_sections(text)

    def test_notes_and_references_stay_in_their_section(self):
        note = ('§ 640. First version.\n* NB Effective until notification\n'
                'Alternative version.\n* NB Effective upon notification\n'
                '(Amended provision.) See § 641. for details.\nSection 2. Reference.')
        text = article_text().replace('§ 640. Short provision.', note)
        sections = dict(core.ny_sections(text))
        self.assertEqual(sections['640'], note)
        self.assertEqual(sections['641'], '§ 641. Short provision.')

    def test_long_section_character_coverage(self):
        text = '§ 640. ' + ' '.join(f'word{i}' for i in range(1000)) + ' final statutory words.'
        pieces = list(core.section_chunks(text, '§ 640'))
        covered = set()
        start = 0
        for piece, citation in pieces:
            self.assertEqual(citation, '§ 640')
            at = text.index(piece, start)
            covered.update(range(at, at + len(piece)))
            start = at
        self.assertTrue(all(ch.isspace() or i in covered for i, ch in enumerate(text)))

    def test_http_error_redirect_and_non_pdf_rejected(self):
        response = Mock(url=core.NY_PDF, content=b'<html>Challenge</html>')
        with patch.object(core.requests, 'get', return_value=response):
            with self.assertRaises(RuntimeError): core.ny_pdf_text()
            response.url = 'https://example.test/'
            response.content = b'%PDF-'
            with self.assertRaises(RuntimeError): core.ny_pdf_text()
            response.raise_for_status.side_effect = core.requests.HTTPError('403')
            with self.assertRaises(RuntimeError): core.ny_pdf_text()

    def test_blank_pdf_page_rejected(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        stream = BytesIO(); writer.write(stream)
        response = Mock(url=core.NY_PDF, content=stream.getvalue())
        with patch.object(core.requests, 'get', return_value=response):
            with self.assertRaises(RuntimeError): core.ny_pdf_text()

    def test_incomplete_article_does_not_write(self):
        collection = Mock(); db = Mock()
        db.get_or_create_collection.return_value = collection
        entry = {'url': core.NY_PDF, 'state': 'New York', 'name': 'NY'}
        with patch.object(core, 'ny_pdf_text', return_value=article_text(SECTIONS[:-1])), \
                patch.object(core, 'sources', return_value=[entry]), \
                patch.object(core.chromadb, 'PersistentClient', return_value=db), \
                patch.object(core, 'SentenceTransformer') as model:
            with self.assertRaises(RuntimeError): core.ingest()
        collection.upsert.assert_not_called()
        collection.delete.assert_not_called()
        model.return_value.encode.assert_not_called()

    def test_texas_and_pennsylvania_heading_contract(self):
        text = 'Section 16. Penalties.\nSection 17.\u00a0\u00a0Severability.\nSection 18.\u00a0\u00a0Effective Date.'
        self.assertEqual([s for _, s in core.chunks(text)], ['Section 16.', 'Section 17.', 'Section 18.'])
        self.assertEqual(list(core.chunks('Sec. 152.101. License required.')),
                         [('Sec. 152.101. License required.', 'Sec. 152.101.')])
        self.assertFalse(core.SECTION_HEADING.search('See Section 17. for details.'))


class MemoryCollection:
    def __init__(self, failure):
        self.rows = {'old': ('old text', [1.0], {'source_url': core.NY_INDEX}),
                     'texas': ('Texas text', [2.0], {'source_url': 'texas'})}
        self.failure = failure

    def get(self, **kwargs):
        ids = [i for i, row in self.rows.items() if row[2]['source_url'] == core.NY_INDEX]
        return {'ids': ids, 'documents': [self.rows[i][0] for i in ids],
                'embeddings': [self.rows[i][1] for i in ids],
                'metadatas': [self.rows[i][2] for i in ids]}

    def upsert(self, ids, documents, embeddings, metadatas):
        self.rows.update({i: (d, e, m) for i, d, e, m in zip(ids, documents, embeddings, metadatas)})
        if self.failure == 'upsert':
            self.failure = None
            raise RuntimeError('Simulated partial write')

    def delete(self, ids):
        for i in ids:
            self.rows.pop(i, None)
        if self.failure == 'delete':
            self.failure = None
            raise RuntimeError('Simulated cleanup failure')


class ReplacementTests(unittest.TestCase):
    def replace(self, collection, maximum=100):
        core.replace_ny_records(collection, ['new'], ['new text'], [[3.0]],
                                [{'source_url': core.NY_INDEX}], maximum)

    def test_rollback_after_write_or_cleanup_failure(self):
        for failure in ['upsert', 'delete']:
            collection = MemoryCollection(failure)
            before = copy.deepcopy(collection.rows)
            with self.subTest(failure=failure), self.assertRaises(RuntimeError):
                self.replace(collection)
            self.assertEqual(collection.rows, before)

    def test_success_and_batch_limit(self):
        collection = MemoryCollection(None)
        before = copy.deepcopy(collection.rows)
        with self.assertRaises(RuntimeError):
            self.replace(collection, maximum=0)
        self.assertEqual(collection.rows, before)
        self.replace(collection)
        self.assertEqual(set(collection.rows), {'new', 'texas'})

    def test_ingestion_metadata_and_repeat_ingestion_in_memory(self):
        # Exercise the installed Chroma API without opening the project's index.
        db = core.chromadb.EphemeralClient()
        collection = db.get_or_create_collection('statutes')
        collection.upsert(ids=['texas-fixture'], documents=['Texas statute'],
                          embeddings=[[1.0, 0.0]], metadatas=[{'state': 'Texas'}])
        entry = {'url': core.NY_PDF, 'state': 'New York', 'name': 'NY Article 13-B'}
        model = Mock()
        model.encode.side_effect = lambda texts, **kw: np.array([[1.0, 0.0]] * len(texts))
        with patch.object(core, 'sources', return_value=[entry]), \
                patch.object(core, 'ny_pdf_text', return_value=article_text()), \
                patch.object(core.chromadb, 'PersistentClient', return_value=db), \
                patch.object(core, 'SentenceTransformer', return_value=model):
            core.ingest()
            core.ingest()
        records = collection.get(where={'state': 'New York'}, include=['metadatas'])
        self.assertEqual(len(records['ids']), 16)
        self.assertEqual({m['section'] for m in records['metadatas']},
                         {f'§ {s.lower()}' for s in SECTIONS})
        for meta in records['metadatas']:
            self.assertEqual(meta['source_url'], core.NY_INDEX)
            self.assertEqual(meta['url'], 'https://www.nysenate.gov/legislation/laws/BNK/'
                             + meta['section'][2:].upper())
            self.assertEqual(meta['source_type'], 'statute')
            self.assertEqual(meta['pdf_url'], core.NY_PDF)
        self.assertEqual(collection.get(where={'state': 'Texas'})['ids'], ['texas-fixture'])
        result = collection.query(query_embeddings=[[1.0, 0.0]], n_results=4,
                                  where={'state': 'New York'}, include=['metadatas'])
        self.assertTrue(all(m['state'] == 'New York' for m in result['metadatas'][0]))
        db.delete_collection('statutes')


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.db = core.chromadb.EphemeralClient()
        self.collection = self.db.get_or_create_collection('retrieval-tests')
        self.model = Mock()
        self.model.encode.return_value = np.array([[1.0, 0.0]])

    def tearDown(self):
        self.db.delete_collection('retrieval-tests')

    def add(self, ident, state, citation, text, vector=None, source='law'):
        self.collection.upsert(ids=[ident], documents=[text], embeddings=[vector or [1.0, 0.0]],
                               metadatas=[{'state': state, 'section': citation,
                                           'url': source, 'source_url': source, 'name': source}])

    def test_exact_identifiers_and_trailing_punctuation(self):
        for query, expected in [('Section 648.', '648'), ('§ 651-a', '651-a'),
                                ('Sec. 152.101', '152.101'), ('Section 1.1', '1.1')]:
            self.assertEqual([m[1].lower() for m in core.CITATION.finditer(query)], [expected])
        self.add('651', 'New York', '§ 651', '§ 651. Investments.')
        self.add('651a', 'New York', '§ 651-a', '§ 651-a. Remittances.')
        self.add('1', 'Pennsylvania', 'Section 1.', 'Section 1. Definitions.')
        self.add('1.1', 'Pennsylvania', 'Section 1.1.', 'Section 1.1. Short title.')
        for query, state, expected in [('Section 651', 'New York', '§ 651'),
                                       ('Section 1', 'Pennsylvania', 'Section 1.')]:
            result, message = core.retrieve(self.collection, query, state, self.model)
            self.assertIsNone(message)
            self.assertEqual([m['section'] for _, m in result], [expected])
        self.model.encode.assert_not_called()

    def test_ambiguity_and_state_filter(self):
        self.add('pa', 'Pennsylvania', 'Section 18.', 'Section 18. Effective Date.')
        self.add('tx', 'Texas', 'Sec. 18.', 'Sec. 18. Other statute.')
        result, message = core.retrieve(self.collection, 'Section 18', None, self.model)
        self.assertEqual(result, [])
        self.assertIn('multiple states', message)
        result, message = core.retrieve(self.collection, 'Section 18', 'Pennsylvania', self.model)
        self.assertEqual(result[0][1]['state'], 'Pennsylvania')
        result, message = core.retrieve(self.collection, 'Section 999', 'Pennsylvania', self.model)
        self.assertEqual(result, [])
        self.assertIn('No matching section', message)

    def test_opening_and_continuations_in_text_order(self):
        text = '§ 648. Agents. ' + ' '.join(f'word{i}' for i in range(600))
        chunks = list(core.section_chunks(text, '§ 648'))
        for i, (piece, citation) in reversed(list(enumerate(chunks))):
            self.add(str(i), 'New York', citation, piece)
        result, message = core.retrieve(self.collection, 'Section 648', 'New York', self.model)
        self.assertEqual([d for d, _ in result], [d for d, _ in chunks])

    def test_new_york_licensing_and_pennsylvania_effective_date(self):
        cases = [
            ('New York', '§ 641', '§ 641. License. A person receiving money needs a license.',
             '§ 650', '§ 650. Violations. Money transmitter licensee penalties.',
             'Who needs a money transmitter license in New York?'),
            ('Pennsylvania', 'Section 18.', 'Section 18. Effective Date.--This act becomes effective.',
             'Section 8.', 'Section 8. Term of License.--A license has an effective date.',
             'What is the effective date?'),
        ]
        for state, citation, text, other_citation, other_text, question in cases:
            self.add(state + '-target', state, citation, text, [0.95, 0.05])
            self.add(state + '-other', state, other_citation, other_text)
            result, message = core.retrieve(self.collection, question, state, self.model)
            self.assertIsNone(message)
            self.assertEqual(result[0][1]['section'], citation)
            self.assertTrue(all(m['state'] == state for _, m in result))
        self.add('tx', 'Texas', 'Sec. 152.101.', 'Sec. 152.101. License required.')
        result, message = core.retrieve(self.collection, 'Sec. 152.101', 'Texas', self.model)
        self.assertEqual(result[0][1]['section'], 'Sec. 152.101.')

    def test_general_heading_boost_and_candidate_pool(self):
        for i in range(19):
            self.add(str(i), 'Texas', f'Sec. 152.{i:03}.',
                     f'Sec. 152.{i:03}. Disclosure. A money transmission licensee provides disclosures.')
        self.add('license', 'Texas', 'Sec. 152.101.',
                 'Sec. 152.101. MONEY TRANSMISSION LICENSE REQUIRED. A person needs a license.', [0.95, 0.05])
        result, message = core.retrieve(self.collection, 'Who needs a money transmission license?', 'Texas', self.model)
        self.assertEqual(result[0][1]['section'], 'Sec. 152.101.')
        self.assertEqual(len(result), 4)



if __name__ == '__main__':
    unittest.main()
