"""Shared helpers for checking quotes. Used by check.py and llm_extract.py.

clean():          ignore spacing, line breaks, curly quotes and capitals when comparing text
number_in_quote(): True if a number is actually written in the quote
                   (375 -> "$375", 2000000 -> "$2 million", 90 -> "ninety (90) days")
"""
import re

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def clean(text):
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def _words(n):
    """Ways to spell 0-999 in words, e.g. 95 -> {'ninety-five', 'ninety five'}."""
    if n < 20:
        return {_ONES[n]}
    if n < 100:
        t, o = divmod(n, 10)
        return {_TENS[t]} if o == 0 else {f"{_TENS[t]}-{_ONES[o]}", f"{_TENS[t]} {_ONES[o]}"}
    h, rest = divmod(n, 100)
    if rest == 0:
        return {f"{_ONES[h]} hundred"}
    return {f"{_ONES[h]} hundred {w}" for w in _words(rest)} | {f"{_ONES[h]} hundred and {w}" for w in _words(rest)}


def _forms(value):
    v = int(value)
    digits = {str(v), f"{v:,}"}
    for size, word in ((10**9, "billion"), (10**6, "million")):
        if v >= size and v % (size // 10) == 0:        # 2 million, 1.5 million
            n = v / size
            digits.add(f"{int(n) if n == int(n) else n} {word}")
    words = _words(v) if v < 1000 else set()
    return digits, words


def number_in_quote(value, quote):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return True                                     # not a number field, nothing to check
    q = clean(quote)
    digits, words = _forms(value)
    for d in digits:                                    # "5" must not match inside "50,000" or "1,500"
        if re.search(rf"(?<![\d,.]){re.escape(d)}(?!\d|,\d)", q):
            return True
    return any(re.search(rf"\b{re.escape(w)}\b", q) for w in words)
