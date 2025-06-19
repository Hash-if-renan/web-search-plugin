from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse


ACADEMIC_SOURCES = [
    "jstor.org",  # Humanities, social sciences, academic
    "core.ac.uk",  # Open access research papers
    "dimensions.ai",
]

NEWS_SOURCES = [
    "bbc.com",  # International news
    "theguardian.com",  # Global news and opinion
    "indiatoday.in",  # Indian news/media
    "thehindu.com",
]
GK_SOURCES = [
    "wikipedia.org",  # General knowledge and reference
    "medium.com",  # Thought leadership, blogs, commentary"
    "stackoverflow.com",  # Programming Q&A"
    "reddit.com",
]


def get_domain_name(url: str) -> str:
    """
    Extracts the domain name from a given URL.

    Parameters:
    url (str): A full or partial URL.

    Returns:
    str: The domain name only (e.g., 'bikewale.com').
    """
    parsed = urlparse(url)
    netloc = parsed.netloc or parsed.path  # If no scheme, use path as domain
    domain = netloc.lstrip("www.")  # Remove 'www.' if present
    return domain


def get_queries(
    query: str,
    trusted_sources: bool = True,
    external_sources: Optional[List[str]] = None,
) -> List[str]:
    """
    This function takes a query and an optional list of external sources,
    and returns a list of queries to be used for web search.

    Parameters:
    query (str): The main query string.
    external_sources (list, optional): A list of external sources to include in the search.

    Returns:
    list: A list of queries to be used for web search.
    """
    queries = []
    if external_sources is None and not trusted_sources:
        queries.append(query)
        return queries

    sources = ACADEMIC_SOURCES + GK_SOURCES + NEWS_SOURCES if trusted_sources else []
    if external_sources:
        cleaned_sources = [get_domain_name(src) for src in external_sources]

        sources.extend(cleaned_sources)
    current_date = datetime.now().strftime("%Y-%m-%d")
    for source in sources:
        if sources in NEWS_SOURCES:

            queries.append(f"site:{source} {query} after:{current_date}")
        else:
            queries.append(f"site:{source} {query}")

    return queries


if __name__ == "__main__":
    custom_sources = [
        "bikewale.com",
        "https://www.zigwheels.com/bike-comparison/",
    ]
    user_query = "Bullet vs classic 350 which one's better"
    result = get_queries(
        user_query, trusted_sources=False, external_sources=custom_sources
    )
    print(result)
