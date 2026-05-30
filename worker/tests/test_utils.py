from worker.ingest.utils import extract_terms, _clean_words


def test_filters_stopwords():
    words = _clean_words("EY Canada published a cybersecurity report and most citations were hallucinated")
    # stopwords removed
    assert "a" not in words
    assert "and" not in words
    assert "most" not in words
    assert "were" not in words
    # significant words kept
    assert "canada" in words
    assert "cybersecurity" in words
    assert "report" in words


def test_filters_numbers_and_symbols():
    words = _clean_words("OpenRouter raises $113M Series B")
    # money/figure tokens dropped
    assert "$113m" not in words
    assert "113m" not in words
    # single-letter "B" dropped (too short)
    assert "b" not in words
    # real words kept
    assert "openrouter" in words
    assert "raises" in words
    assert "series" in words


def test_no_garbage_bigrams():
    terms = extract_terms("EY Canada published a cybersecurity report and most citations were hallucinated")
    # the old broken bigrams must not appear
    assert "report most" not in terms
    assert "report were" not in terms
    # clean n-grams should
    assert any("cybersecurity report" in t for t in terms)


def test_returns_at_most_five_unique():
    terms = extract_terms("artificial intelligence machine learning deep neural networks transformers attention")
    assert len(terms) <= 5
    assert len(terms) == len(set(terms))  # all unique


def test_empty_and_stopword_only_titles():
    assert extract_terms("") == []
    # title made only of stopwords yields no n-grams
    assert extract_terms("the a and to of") == []


def test_keeps_hyphenated_and_apostrophe_words():
    terms = extract_terms("Thiel moves to Milei's zero-shot libertarian model")
    flat = " ".join(terms)
    assert "zero-shot" in flat or "milei's" in flat
