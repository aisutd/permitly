"""Evaluate retrieval against manually labeled relevant chunk IDs.

Inspect core.retrieve(question) to see chunk IDs, then label relevant chunks
from the index independently. Retrieved results alone are not ground truth.
Labels must refer to the current index: changed source text can change IDs.
"""


def recall_at_k(retrieved_ids, relevant_ids, k=4): #Recall Function
    """Fraction of all labeled relevant chunks present in the top k results."""
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError('k must be a positive integer')
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError('Provide at least one labeled relevant chunk ID')
    return len(set(list(retrieved_ids)[:k]) & relevant) / len(relevant)


def evaluate_recall(question, relevant_ids, state=None, k=4):
    """Retrieve passages and return recall@k for a labeled test question.

    Example: evaluate_recall('Your question', ['known-relevant-chunk-id'], k=4)
    Returns a score between 0.0 and 1.0; requires an existing statute index.
    """
    # Validate labels before loading the embedding model or querying the index.
    relevant_ids = set(relevant_ids)
    recall_at_k([], relevant_ids, k=k)
    if __package__:
        from .core import retrieve
    else:
        from core import retrieve
    passages = retrieve(question, state=state, k=k)
    return recall_at_k([passage['id'] for passage in passages], relevant_ids, k=k)
