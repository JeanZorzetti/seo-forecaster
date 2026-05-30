def extract_terms(title: str) -> list[str]:
    terms = [title.lower()]
    words = [w for w in title.lower().split() if len(w) > 3]
    for i in range(len(words) - 1):
        terms.append(f"{words[i]} {words[i+1]}")
    return terms[:5]
