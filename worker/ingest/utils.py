import re

# Common English + a few Portuguese stopwords. Filtered out before building n-grams
# so terms like "report most" or "raises $113m" never reach the pipeline.
STOPWORDS = {
    # English
    "the", "a", "an", "and", "or", "but", "for", "nor", "so", "yet",
    "in", "on", "at", "to", "of", "off", "by", "up", "out", "as", "is",
    "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
    "have", "has", "had", "will", "would", "can", "could", "should", "may",
    "might", "must", "shall", "with", "from", "into", "onto", "upon", "over",
    "under", "this", "that", "these", "those", "their", "there", "here",
    "what", "when", "where", "which", "who", "whom", "how", "why", "you",
    "your", "they", "them", "its", "his", "her", "our", "we", "i", "he",
    "she", "it", "my", "me", "us", "all", "any", "some", "most", "more",
    "much", "many", "few", "not", "no", "yes", "now", "then", "than",
    "just", "only", "also", "very", "too", "about", "after", "before",
    "again", "new", "via", "use", "using", "get", "got", "make", "made",
    # Portuguese
    "que", "com", "para", "por", "uma", "dos", "das", "como", "mais",
    "mas", "foi", "ser", "sua", "seu", "nao", "sim", "até", "ate",
}

# Matches a "word" worth keeping: alphabetic (incl. accents), length >= 3,
# not purely numeric, not a money/figure token like $113m.
_WORD_RE = re.compile(r"^[a-záàâãéêíóôõúüç][a-záàâãéêíóôõúüç\-']{2,}$")


def _clean_words(title: str) -> list[str]:
    """Tokenize a title into significant words: drop stopwords, numbers, symbols."""
    raw = title.lower().split()
    words = []
    for w in raw:
        # strip surrounding punctuation but keep internal hyphens/apostrophes
        w = w.strip(".,;:!?()[]{}\"'`")
        if not _WORD_RE.match(w):
            continue
        if w in STOPWORDS:
            continue
        words.append(w)
    return words


def extract_terms(title: str) -> list[str]:
    """
    Build clean keyword candidates from a title:
    - the full normalized title (kept as the broad-match term)
    - bigrams and trigrams of *significant* words only (no stopwords/numbers)

    Returns up to 5 unique terms, longest-meaningful first.
    """
    full = title.lower().strip()
    words = _clean_words(title)

    terms: list[str] = []
    seen: set[str] = set()

    def add(t: str):
        if t and t not in seen:
            seen.add(t)
            terms.append(t)

    # Trigrams (most specific, best long-tail keywords)
    for i in range(len(words) - 2):
        add(f"{words[i]} {words[i+1]} {words[i+2]}")
    # Bigrams
    for i in range(len(words) - 1):
        add(f"{words[i]} {words[i+1]}")
    # Full title as broad term (only if it adds signal beyond the n-grams)
    if len(full.split()) <= 8:
        add(full)

    return terms[:5]
