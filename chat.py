from search import Search
from llm import LLM
from scrape import Crawl4AIScraper
import asyncio
import json

SYSTEM_PROMPT_TEMPLATE = """You are a research assistant that can search the web. For each question:
1. Perform a fresh web search when needed
2. Analyze the results
3. Respond in markdown format with:
   - Point-by-point answers
   - Source links for all facts
   - Clear comparisons when needed

Guidelines:
- Be concise but thorough
- Only use information from the provided search results
- If information is conflicting, note this
- If no relevant results found, say so"""


async def web_search(query: str, custom_sources: list = None) -> list:
    """Perform web search and return scraped data"""
    search = Search()
    search_results = search.run_all_searches(
        query,
        trusted_sources=True,
        external_sources=custom_sources,
        min_relevance=0.1,
    )
    links = [r["link"] for r in search_results]
    scraper = Crawl4AIScraper()
    scraped_data = await scraper.scrape_many(links)
    return scraped_data


async def process_tool_call(llm: LLM, tool_call, sources: list) -> str:
    """Handle web search tool call and return formatted results"""
    if tool_call.function.name == "web_search":
        args = json.loads(tool_call.function.arguments)
        query = args["query"]

        print(f"\n🔍 Performing web search: {query}...")
        scraped_data = await web_search(query, sources)

        if not scraped_data:
            return "No relevant results found for this query."

        # Format the search results into the prompt format
        results_str = f"Search Results for '{query}':\n\n" + "\n\n".join(
            f"Source: {r['metadata']['url']}\nContent: {r['content']['markdown']['raw'][:2000]}"
            for r in scraped_data
        )

        print("results_str:", results_str)

        return results_str
    else:
        return f"Unknown tool called: {tool_call.function.name}"


async def chat():
    llm = LLM(enable_tools=True)
    sources = [
        "bikewale.com",
        "https://www.zigwheels.com/bike-comparison/",
    ]

    # Set up system prompt
    llm.add_message("system", SYSTEM_PROMPT_TEMPLATE)

    print("Research Assistant ready. I'll perform web searches when needed.")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("\nYour question: ").strip()

            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Get initial response (may include tool calls)
            response = llm.run(user_input)

            # Handle tool calls if present
            if hasattr(response, "tool_calls") and response.tool_calls:
                search_results_prompt = ""
                tool_call = response.tool_calls[
                    0
                ]  # Assuming single tool call for simplicity
                # Process each tool call and collect results
                tool_result = await process_tool_call(llm, tool_call, sources)
                search_results_prompt += f"\n\n{tool_result}"

                # Create a new prompt combining original query and search results
                combined_prompt = f"Original Query: {user_input}\n\n{search_results_prompt}\n\nPlease analyze these results and answer the query."
                llm.add_message("system", combined_prompt)

                print("combined_prompt:", combined_prompt)

                # Get final response using the combined prompt
                response = llm.run()

            # Add assistant response to history and print it
            llm.add_message("assistant", response.content)
            print("\nAssistant:")
            print(response.content)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(chat())
