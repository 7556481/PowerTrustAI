"""Deterministic BM25 baseline. Scores express retrieval relevance only."""
from collections import Counter
import math
import re


TOKENIZER_VERSION = "latin-alnum-cjk-unigram-bigram-v1"
SCORING_METHOD = "BM25-v1(k1=1.5,b=0.75,ln-positive-idf,unique-query-terms)"
INDEX_CONFIG = {"parser": "markdown-blocks-v1", "tokenizer": TOKENIZER_VERSION,
                "scoring_method": SCORING_METHOD, "heading_enhancement": True,
                "term_expansion": False}


def tokenize(text: str) -> tuple[str, ...]:
    tokens = []
    for match in re.finditer(r"[a-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]+", text.casefold()):
        word = match[0]
        if "\u3400" <= word[0] <= "\u9fff":
            tokens.extend(word)
            tokens.extend(word[i:i + 2] for i in range(len(word) - 1))
        else:
            tokens.append(word)
    return tuple(tokens)


def score_corpus(query: str, corpus: list[tuple[str, ...]]) -> list[float]:
    terms = set(tokenize(query))
    counts = [Counter(tokens) for tokens in corpus]
    n = len(counts)
    average = sum(map(len, corpus)) / n if n else 0
    if not average or not terms:
        return [0.0] * n
    df = {term: sum(term in count for count in counts) for term in terms}
    scores = []
    for tokens, count in zip(corpus, counts):
        score = 0.0
        for term in sorted(terms):
            tf = count[term]
            if tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * (tf * 2.5) / (tf + 1.5 * (0.25 + 0.75 * len(tokens) / average))
        scores.append(score)
    return scores
