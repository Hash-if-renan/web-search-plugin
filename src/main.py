from core.search import Search
from core.llm import LLM
from core.scrape import Crawl4AIScraper
import asyncio
import json
from core.query_generator import Persona, QueryGenerator
from core.evaluate import Evaluator


async def web_search(
    query: str,
    persona: Persona,
    custom_sources: list = None,
) -> list:
    """Perform web search and return scraped data"""
    query_generator = QueryGenerator(persona)
    generated_queries = query_generator.get_queries(
        query, trusted_sources=True, external_sources=custom_sources
    )
    search = Search(query_generator.main_query_exclusions)
    search_results = search.run_all_searches(
        query,
        generated_queries,
        min_relevance=0.1,
    )
    links = [r["link"] for r in search_results]
    scraper = Crawl4AIScraper()
    scraped_data = await scraper.scrape_many(links)
    return scraped_data


async def process_tool_call(tool_call, sources: list, persona: Persona) -> str:
    """Handle web search tool call and return formatted results"""
    if tool_call.function.name == "web_search":
        args = json.loads(tool_call.function.arguments)
        query = args["query"]

        print(f"\n🔍 Performing web search: {query}...")
        scraped_data = await web_search(query, persona, sources)

        if not scraped_data:
            return "No relevant results found for this query."

        # Format the search results into the prompt format
        results_str = f"Search Results for '{query}':\n\n" + "\n\n".join(
            f"Source: {r['metadata']['url']}\nContent: {r['content']['markdown']['raw']}"
            for r in scraped_data
        )

        print("results_str:", results_str)

        return results_str
    else:
        return f"Unknown tool called: {tool_call.function.name}"


async def chat():

    persona = Persona("finance_expert")
    llm = LLM(enable_tools=True, system_prompt=persona.prompt)
    sources = [
        # "bikewale.com",
        # "https://www.zigwheels.com/bike-comparison/",
    ]

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
                print("executing function call..")
                search_results_prompt = ""
                tool_call = response.tool_calls[
                    0
                ]  # Assuming single tool call for simplicity
                # Process each tool call and collect results
                tool_result = await process_tool_call(tool_call, sources, persona)
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
