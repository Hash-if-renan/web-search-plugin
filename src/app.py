import streamlit as st
import asyncio
import json

from core.search import Search
from core.llm import LLM
from core.scrape import Crawl4AIScraper
from core.query_generator import Persona, QueryGenerator
import re
import asyncio


async def web_search(query: str, custom_sources=None, persona=None, ui_containers=None):
    """Perform web search and return scraped data and intermediate steps"""
    query_generator = QueryGenerator(persona)
    generated_queries = query_generator.get_queries(
        query, trusted_sources=True, external_sources=custom_sources
    )

    print("Generated Queries:", generated_queries)

    if ui_containers and "generated_queries" in ui_containers:
        with ui_containers["generated_queries"].container():
            st.subheader("🔎 Sources:")
            domains = []
            for q in generated_queries:
                match = re.search(r"site:([^\s]+)", q)
                if match:
                    domains.append(match.group(1))
            print("Domains found:", domains)
            cols = st.columns(3)
            for i, domain in enumerate(domains):
                with cols[i % 3]:
                    st.markdown(f"{i+1}. <code>{domain}</code>", unsafe_allow_html=True)

    search = Search(query_generator.main_query_exclusions)
    search_results = search.run_all_searches(
        query, generated_queries, min_relevance=0.1
    )
    links = [r["link"] for r in search_results]

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
    if not user_input:
        return "Please enter a query."

    if "llm" not in st.session_state or st.session_state.persona_name != persona_name:
        persona = Persona(persona_name)
        st.session_state.llm = LLM(enable_tools=True, system_prompt=persona.prompt)
        st.session_state.persona_name = persona_name

    llm = st.session_state.llm

    stream = llm.run(user_input, stream=True)
    collected_response = ""
    final_tool_calls = {}

    answer_placeholder = ui_containers.get("answer", st.empty())
    with answer_placeholder:
        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index
                    if index not in final_tool_calls:
                        final_tool_calls[index] = tool_call
                    else:
                        final_tool_calls[
                            index
                        ].function.arguments += tool_call.function.arguments

            elif delta.content:
                collected_response += delta.content
                answer_placeholder.markdown(collected_response)

    if final_tool_calls:
        first_call = list(final_tool_calls.values())[0]
        scraped_data = await process_tool_call(
            user_input, first_call, sources, Persona(persona_name), ui_containers
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

        stream2 = llm.run(stream=True)
        final_response = ""
        with answer_placeholder:
            for chunk in stream2:
                delta = chunk.choices[0].delta
                content = delta.content
                final_response += content if content else ""
                answer_placeholder.markdown(final_response)

        llm.add_message("assistant", final_response)
        return final_response

    llm.add_message("assistant", collected_response)
    return collected_response


def app():
    st.set_page_config(page_title="AI Research Assistant", layout="wide")
    st.title("🧠 AI Research Assistant")

    query = st.text_input("Enter your question:")
    custom_sources_input = st.text_area(
        "Optional: Enter custom sources (comma-separated, e.g., marketwatch.com, bloomberg.com)",
        value="",
        height=100,
    )
    custom_sources = [s.strip() for s in custom_sources_input.split(",") if s.strip()]

    persona_name = st.selectbox(
        "Choose a persona",
        ["default", "finance_expert", "crypto_expert", "tech_expert", "news_monitor"],
    )

    # 🔘 Clear conversation history
    if st.button("🧹 Clear History"):
        if "llm" in st.session_state:
            st.session_state.llm.reset_history()
            st.success("Conversation history cleared.")

    # 🚀 Ask button
    if st.button("Ask"):
        if query:
            # Create UI containers for displaying steps
            generated_queries_container = st.empty()
            search_links_container = st.empty()
            scraped_data_container = st.empty()
            answer_container = st.empty()

            ui_containers = {
                "generated_queries": generated_queries_container,
                "search_links": search_links_container,
                "scraped_data": scraped_data_container,
                "answer": answer_container,
            }

            with st.spinner("Thinking..."):
                asyncio.run(
                    handle_query(query, persona_name, custom_sources, ui_containers)
                )
        else:
            st.warning("Please enter a question.")


if __name__ == "__main__":
    app()
