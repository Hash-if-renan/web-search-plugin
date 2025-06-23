from pathlib import Path
import logging

PERSONAS = ["crypto_expert", "finance_expert", "news_monitor", "tech_expert"]

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

EXCLUDED_SOURCES = ["youtube.com", "quora.com"]


#

# Persona-specific sources
CRYPTO_EXPERT_SOURCES = (
    ACADEMIC_SOURCES
    + NEWS_SOURCES
    + ["coindesk.com", "cointelegraph.com", "decrypt.co", "bankless.com"]
)

FINANCE_EXPERT_SOURCES = (
    ACADEMIC_SOURCES
    + NEWS_SOURCES
    + ["bloomberg.com", "reuters.com", "investopedia.com", "marketwatch.com"]
)

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
        "crypto_expert": CRYPTO_EXPERT_SOURCES,
        "finance_expert": FINANCE_EXPERT_SOURCES,
        "news_monitor": NEWS_MONITOR_SOURCES,
        "tech_expert": TECH_EXPERT_SOURCES,
    }

    def __init__(self, persona_name, prompt_dir="/prompt/personas"):
        """
        Initialize the Persona class for a specific persona.

        :param persona_name: The name of the persona to load
        :param prompt_dir: Directory containing text files for each persona's prompt
        """
        self.prompt_dir = Path(prompt_dir)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)

        self.persona_name = persona_name
        self.personas = PERSONAS  # Should be a list like ["crypto_expert", ...]

        if persona_name not in self.personas:
            raise ValueError(
                f"Persona '{persona_name}' not found in allowed personas: {self.personas}"
            )

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
