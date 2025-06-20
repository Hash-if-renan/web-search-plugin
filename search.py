from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import urlparse
import re
import numpy as np
import os
import requests
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()


class Search:
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

    def __init__(self):
        self.serper_endpoint = os.getenv("SERPER_ENDPOINT")
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.main_query_exclusions = set(
            self.ACADEMIC_SOURCES
            + self.NEWS_SOURCES
            + self.GK_SOURCES
            + self.EXCLUDED_SOURCES
        )
        self.bm25 = None

    @staticmethod
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
        self,
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

        sources = (
            self.ACADEMIC_SOURCES + self.GK_SOURCES + self.NEWS_SOURCES
            if trusted_sources
            else []
        )
        if external_sources:
            cleaned_sources = [self.get_domain_name(src) for src in external_sources]
            sources.extend(cleaned_sources)

        current_date = datetime.now().strftime("%Y-%m-%d")
        for source in sources:
            if source in self.NEWS_SOURCES:
                queries.append(f"site:{source} {query} after:{current_date}")
            else:
                queries.append(f"site:{source} {query}")

        return queries

    def _execute_search(
        self, query: str, num_results: int = 5, apply_exclusions: bool = False
    ) -> List[Dict]:
        """Execute a single search query and optionally filter results"""
        payload = json.dumps({"q": query, "num": num_results})
        headers = {
            "x-api-key": self.serper_api_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.serper_endpoint, headers=headers, data=payload
            )
            response.raise_for_status()
            results = response.json().get("organic", [])

            if apply_exclusions:
                # Filter out results from excluded domains (only for main query)
                filtered_results = [
                    result
                    for result in results
                    if self.get_domain_name(result.get("link", ""))
                    not in self.main_query_exclusions
                ]
                return filtered_results[:num_results]
            return results[:num_results]
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            return []

    def _tokenize(self, text: str) -> List[str]:
        """Improved tokenizer that keeps key phrases like 'Bullet 350'"""
        # Lowercase and split into words
        words = re.findall(r"\w+", text.lower())

        # Merge numbers with preceding words (e.g., "Bullet 350" -> "bullet_350")
        tokens = []
        i = 0
        while i < len(words):
            if i + 1 < len(words) and words[i + 1].isdigit():
                tokens.append(f"{words[i]}_{words[i+1]}")
                i += 2
            else:
                tokens.append(words[i])
                i += 1
        return tokens

    def _init_bm25(self, corpus: List[str]):
        """Initialize BM25 with given corpus"""
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _calculate_relevance(
        self,
        text: str,
        query: str,
        corpus: List[str],
    ) -> float:
        """Calculate BM25 score with better normalization"""
        if not corpus:
            return 0.0

        # Initialize BM25 with the full corpus
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

        tokenized_text = self._tokenize(text)
        tokenized_query = self._tokenize(query)

        if not tokenized_query:
            return 0.0

        # Get raw BM25 score
        doc_index = corpus.index(text)  # Find position in corpus
        raw_score = self.bm25.get_scores(tokenized_query)[doc_index]

        # Normalize to 0-1 range (min-max scaling)
        all_scores = self.bm25.get_scores(tokenized_query)
        if max(all_scores) - min(all_scores) > 0:
            normalized_score = (raw_score - min(all_scores)) / (
                max(all_scores) - min(all_scores)
            )
        else:
            normalized_score = 0.0  # Avoid division by zero

        return float(normalized_score)

    def _filter_results(
        self,
        results: List[Dict],
        query: str,
        min_score: float = 0.2,
    ) -> List[Dict]:
        """Filter results using titles and snippets with BM25 scoring"""
        # Combine title + snippet for each result (snippet adds context)
        texts = [f"{res.get('title', '')} {res.get('snippet', '')}" for res in results]

        # Initialize BM25 with all titles
        tokenized_corpus = [self._tokenize(text) for text in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        tokenized_query = self._tokenize(query)
        all_scores = self.bm25.get_scores(tokenized_query)

        # Normalize scores to 0-1 range (min-max scaling)
        if len(all_scores) > 0:
            max_score = max(all_scores)
            min_score_bm25 = min(all_scores)
            score_range = max_score - min_score_bm25
        else:
            score_range = 0

        scored_results = []
        for i, res in enumerate(results):
            if score_range > 0:
                normalized_score = (all_scores[i] - min_score_bm25) / score_range
            else:
                normalized_score = 0.0

            print(f"Title: {res.get('title', '')}\nScore: {normalized_score:.4f}")
            if normalized_score >= min_score:
                res["relevance_score"] = round(normalized_score, 2)
                scored_results.append(res)

        # Sort by score (highest first)
        return sorted(scored_results, key=lambda x: x["relevance_score"], reverse=True)

    def run_all_searches(
        self,
        main_query: str,
        trusted_sources: bool = True,
        external_sources: Optional[List[str]] = None,
        filter: bool = True,
        min_relevance: float = 0.1,
        max_main_results: int = 5,
        max_generated_results: int = 2,
    ) -> List[Dict]:  # Now returns List[Dict] instead of Dict[str, List[Dict]]
        """
        Execute all searches and return COMBINED results (main + generated queries).

        Args:
            main_query: Primary search query
            trusted_sources: Whether to use predefined sources
            external_sources: Additional domains to include
            filter: Whether to apply relevance filtering
            min_relevance: Minimum BM25 score threshold (0-1)
            max_main_results: Max results from main query
            max_generated_results: Max results per generated query

        Returns:
            List[Dict]: Combined results from all queries, sorted by relevance.
        """
        # Execute main query
        raw_main_results = self._execute_search(
            query=main_query,
            num_results=max_main_results,  # Get extra for filtering
            apply_exclusions=True,
        )

        # Execute generated queries
        generated_queries = self.get_queries(
            main_query, trusted_sources, external_sources
        )
        raw_generated_results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    self._execute_search,
                    query=query,
                    num_results=max_generated_results,
                    apply_exclusions=False,
                ): query
                for query in generated_queries
            }
            for future in as_completed(futures):
                try:
                    raw_generated_results.extend(future.result())
                except Exception as e:
                    print(f"Error processing query: {str(e)}")

        # Combine all results
        all_results = raw_main_results + raw_generated_results

        if filter:
            # Apply relevance filtering to ALL results at once
            filtered_results = self._filter_results(
                all_results, main_query, min_relevance
            )

            # Prioritize main query results (higher diversity) by keeping them first
            # while still respecting relevance scores
            return filtered_results
        else:
            # Return raw results (main queries first)
            return all_results


if __name__ == "__main__":
    search = Search()

    custom_sources = [
        "bikewale.com",
        "https://www.zigwheels.com/bike-comparison/",
    ]

    user_query = "Bullet vs classic 350 which one's better"
    results = search.run_all_searches(
        user_query,
        trusted_sources=True,
        external_sources=custom_sources,
        min_relevance=0.1,
        # filter=False,
    )

    print("Main Query Results (5):")
    for i, result in enumerate(results):
        print(f"{i}. {result.get('title')} - {result.get('link')}")
