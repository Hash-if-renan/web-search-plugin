from pathlib import Path
import logging
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse


PERSONAS = ["default", "crypto_expert", "finance_expert", "news_monitor", "tech_expert"]

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

COMMON_SOURCES = ACADEMIC_SOURCES + NEWS_SOURCES + GK_SOURCES

EXCLUDED_SOURCES = ["youtube.com", "quora.com"]

# Persona-specific sources
CRYPTO_EXPERT_SOURCES = NEWS_SOURCES + [
    "coindesk.com",
    "cointelegraph.com",
    "decrypt.co",
    "bankless.com",
]

FINANCE_EXPERT_SOURCES = [
    "bloomberg.com",
    "reuters.com",
    "investopedia.com",
    "marketwatch.com",
]


NEWS_MONITOR_SOURCES = NEWS_SOURCES + [
    "apnews.com",
    "aljazeera.com",
    "nytimes.com",
    "washingtonpost.com",
]

TECH_EXPERT_SOURCES = (
    ACADEMIC_SOURCES
    + GK_SOURCES
    + ["techcrunch.com", "wired.com", "theverge.com", "arstechnica.com"]
)


class Persona:
    DEFAULT_SOURCES = {
        "default": COMMON_SOURCES,
        "crypto_expert": CRYPTO_EXPERT_SOURCES,
        "finance_expert": FINANCE_EXPERT_SOURCES,
        "news_monitor": NEWS_MONITOR_SOURCES,
        "tech_expert": TECH_EXPERT_SOURCES,
    }

    def __init__(self, persona_name, prompt_dir="./prompts/personas/"):
        """
        Initialize the Persona class for a specific persona.

        :param persona_name: The name of the persona to load
        :param prompt_dir: Directory containing text files for each persona's prompt
        """
        self.personas = PERSONAS
        if persona_name not in self.personas:
            raise ValueError(
                f"Persona '{persona_name}' not found in allowed personas: {self.personas}"
            )
        self.prompt_dir = Path(prompt_dir)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)

        self.persona_name = persona_name

        self.sources = self.DEFAULT_SOURCES
        self.source = self._get_source()
        self.prompt = self._get_prompt()

    def _get_prompt(self):
        """Read and return the prompt text for the initialized persona"""
        file_path = self.prompt_dir / f"{self.persona_name}.txt"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Prompt file not found for persona '{self.persona_name}'")
            return None

    def _get_source(self):
        """Get the appropriate sources for a given persona"""
        return self.sources.get(
            self.persona_name, ACADEMIC_SOURCES + NEWS_SOURCES + GK_SOURCES
        )

    def add_persona(self, persona_name, prompt, sources=None):
        """Add or update a persona prompt and optionally its sources"""
        file_path = self.prompt_dir / f"{persona_name}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Add new persona to the list if not already present
        if persona_name not in self.personas:
            self.personas.append(persona_name)

        if sources:
            self.sources[persona_name] = sources


class QueryGenerator:
    def __init__(self, persona: Persona):
        """
        Initialize the QueryGenerator.

        :param persona: Optional Persona instance to use its sources.
        """
        # Fallback default source groups (must be defined elsewhere)
        self.ACADEMIC_SOURCES = ACADEMIC_SOURCES
        self.NEWS_SOURCES = NEWS_SOURCES
        self.GK_SOURCES = GK_SOURCES
        self.EXCLUDED_SOURCES = EXCLUDED_SOURCES

        self.persona = persona
        self.main_query_exclusions = self.EXCLUDED_SOURCES + self.persona.source

    def get_domain_name(self, url: str) -> str:
        """Extract domain from URL"""

        return urlparse(url).netloc.lower()

    def get_queries(
        self,
        query: str,
        trusted_sources: bool = True,
        external_sources: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate a list of web search queries based on the input parameters.

        :param query: The query string to search.
        :param trusted_sources: Whether to include default trusted sources.
        :param external_sources: List of extra domains to include in search.
        :return: List of query strings.
        """
        queries = []
        if external_sources is None and not trusted_sources and not self.persona:
            return [query]

        # Use persona's sources if available, else fallback to trusted/default ones
        if self.persona.persona_name != "default":
            sources = self.persona.source
        elif trusted_sources:
            sources = self.ACADEMIC_SOURCES + self.GK_SOURCES + self.NEWS_SOURCES
        else:
            sources = []

        # Add cleaned external sources if provided
        if external_sources:
            cleaned = [self.get_domain_name(src) for src in external_sources]
            sources.extend(cleaned)

        current_date = datetime.now().strftime("%Y-%m-%d")

        for source in sources:
            if source in self.NEWS_SOURCES:
                queries.append(f"site:{source} {query} after:{current_date}")
            else:
                queries.append(f"site:{source} {query}")

        return queries


if __name__ == "__main__":
    # Example usage
    persona = Persona("crypto_expert")
    query_gen = QueryGenerator(persona)

    query = "latest trends in blockchain technology"
    queries = query_gen.get_queries(query, trusted_sources=True)

    print("Generated Queries:")
    for q in queries:
        print(q)

    print("\nPersona Prompt:")
    print(persona.prompt)
