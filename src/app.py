import streamlit as st
import asyncio
import json

from core.search import Search
from core.llm import LLM
from core.scrape import Crawl4AIScraper
from core.query_generator import Persona, QueryGenerator


async def web_search(query: str, custom_sources=None, persona=None, ui_containers=None):
    """Perform web search and return scraped data and intermediate steps"""
    query_generator = QueryGenerator(persona)
    generated_queries = query_generator.get_queries(
        query, trusted_sources=True, external_sources=custom_sources
    )

    if ui_containers and "generated_queries" in ui_containers:
        with ui_containers["generated_queries"].container():
            st.subheader("🔎 Searching for...")
            for i, q in enumerate(generated_queries):
                st.markdown(f"{i + 1}. {q}")

    search = Search(query_generator.main_query_exclusions)
    search_results = search.run_all_searches(
        query, generated_queries, min_relevance=0.1
    )
    links = [r["link"] for r in search_results][:5]

    if ui_containers and "search_links" in ui_containers:
        with ui_containers["search_links"].container():
            st.subheader("🌐 Search Results")
            for i, result in enumerate(search_results):
                title = result.get("title", "No Title")
                snippet = result.get("snippet", "")
                link = result.get("link", "#")

                st.markdown(f"**{i + 1}. [{title}]({link})**")
                if snippet:
                    st.markdown(f"> {snippet}")
                st.markdown("---")
            st.subheader("📄 Gathering info")

    scraper = Crawl4AIScraper()
    scraped_data = await scraper.scrape_many(links)

    if ui_containers and "scraped_data" in ui_containers:
        with ui_containers["scraped_data"]:
            st.subheader("Analysing Results..")

    return scraped_data


async def process_tool_call(
    query, tool_call, sources=None, persona=None, ui_containers=None
):
    """Handle web search tool call and return all intermediate data"""
    if tool_call.function.name == "web_search":
        return await web_search(query, sources, persona, ui_containers)
    else:
        return []


async def handle_query(
    user_input, persona_name="finance_expert", sources=None, ui_containers=None
):
    """Run the main assistant logic asynchronously"""
    if not user_input:
        return "Please enter a query."

    persona = Persona(persona_name)
    llm = LLM(enable_tools=True, system_prompt=persona.prompt)
    response = llm.run(user_input)

    scraped_data = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_call = response.tool_calls[0]
        scraped_data = await process_tool_call(
            query, tool_call, sources, persona, ui_containers
        )

        combined_prompt = (
            f"Original Query: {user_input}\n\n"
            + "\n\n".join(
                f"Source: {r['metadata']['url']}\nContent: {r['content']['markdown']['raw']}"
                for r in scraped_data
            )
            + "\n\nPlease analyze these results and answer the query."
        )
        llm.add_message("system", combined_prompt)
        response = llm.run()

    final_answer = response.content
    llm.add_message("assistant", final_answer)
    return final_answer


# ---------- Streamlit UI ----------
st.set_page_config(page_title="AI Research Assistant", layout="wide")
st.title("🧠 AI Research Assistant")

query = st.text_input("Enter your question:")
persona_name = st.selectbox(
    "Choose a persona",
    ["finance_expert", "crypto_expert", "tech_expert", "news_monitor"],
)

if st.button("Ask"):
    if query:
        # Create empty containers for step-by-step display
        generated_queries_container = st.empty()
        search_links_container = st.empty()
        scraped_data_container = st.empty()
        answer_container = st.empty()

        with st.spinner("Thinking..."):
            ui_containers = {
                "generated_queries": generated_queries_container,
                "search_links": search_links_container,
                "scraped_data": scraped_data_container,
            }

            answer = asyncio.run(
                handle_query(query, persona_name, ui_containers=ui_containers)
            )

            with answer_container:
                st.subheader("🤖 Assistant Answer")
                st.markdown(answer)
    else:
        st.warning("Please enter a question.")
