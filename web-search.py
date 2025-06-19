from typing import List
from datetime import datetime


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


def get_queries(
    query: str, trusted_sources: bool = True, external_sources: List = None
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
        sources.extend(external_sources)
    current_date = datetime.now().strftime("%Y-%m-%d")
    for source in sources:
        if sources in NEWS_SOURCES:

            queries.append(f"site:{source} {query} after:{current_date}")
        else:
            queries.append(f"site:{source} {query}")

    return queries


if __name__ == "__main__":
    user_query = "Bullet vs classic 350 which one's better"
    result = get_queries(user_query, trusted_sources=False)
    print(result)
