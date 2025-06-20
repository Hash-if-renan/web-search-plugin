from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import urlparse
import os
import requests
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

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

    def run_all_searches(
        self,
        main_query: str,
        trusted_sources: bool = True,
        external_sources: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Execute all generated queries and return consolidated results
        - Takes 5 results from main query (with exclusions applied)
        - Takes 2 results from each generated query (no exclusions)
        """
        results = {
            "main_query_results": self._execute_search(
                main_query,
                num_results=5,
                apply_exclusions=True,  # Only apply exclusions to main query
            ),
            "generated_query_results": [],
        }

        # Generate and execute additional queries (no exclusions)
        generated_queries = self.get_queries(
            main_query, trusted_sources, external_sources
        )

        with ThreadPoolExecutor() as executor:
            future_to_query = {
                executor.submit(self._execute_search, query, 2, False): query
                for query in generated_queries
            }

            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    query_results = future.result()
                    results["generated_query_results"].extend(query_results)
                except Exception as e:
                    print(f"Error processing query '{query}': {e}")

        return results


if __name__ == "__main__":
    search = Search()

    custom_sources = [
        "bikewale.com",
        "https://www.zigwheels.com/bike-comparison/",
    ]

    user_query = "Bullet vs classic 350 which one's better"
    results = search.run_all_searches(
        user_query, trusted_sources=True, external_sources=custom_sources
    )

    print("Main Query Results (5):")
    for i, result in enumerate(results["main_query_results"]):
        print(f"{i}. {result.get('title')} - {result.get('link')}")

    print("\nGenerated Query Results:")
    for i, result in enumerate(results["generated_query_results"]):
        print(f"{i}. {result.get('title')} - {result.get('link')}")
