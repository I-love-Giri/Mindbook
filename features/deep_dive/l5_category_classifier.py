CODE_DOMAIN_KEYWORDS = {
    "programming",
    "code",
    "coding",
    "software",
    "software engineering",
    "web dev",
    "web development",
    "backend",
    "frontend",
    "database",
    "devops",
    "cybersecurity",
    "networking",
    "cloud computing",
    "algorithm",
    "data structures",
    "framework",
    "library",
    "app development",
    "machine learning",
    "deep learning",
    "data science",
    "artificial intelligence",
}


QUANT_DOMAIN_KEYWORDS = {
    "mathematics",
    "math",
    "statistics",
    "physics",
    "chemistry",
    "biology",
    "engineering",
    "economics",
    "finance",
    "accounting",
    "calculus",
    "algebra",
    "geometry",
    "probability",
    "science",
    "astronomy",
    "thermodynamics",
    "mechanics",
    "geology",
    "neuroscience",
    "medicine",
}


NARRATIVE_CONTENT_TYPES = {
    "vlog",
    "interview",
    "documentary",
    "news",
    "debate",
    "review",
    "podcast",
    "story",
}


def classify_content_category(
    domain: str,
    content_type: str,
) -> str:

    domain_l = (domain or "").lower()
    content_type_l = (content_type or "").lower()

    if content_type_l in NARRATIVE_CONTENT_TYPES:
        return "narrative"

    if any(keyword in domain_l for keyword in CODE_DOMAIN_KEYWORDS):
        return "code"

    if any(keyword in domain_l for keyword in QUANT_DOMAIN_KEYWORDS):
        return "quant"

    return "narrative"
