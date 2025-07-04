from dotenv import load_dotenv
from openai import OpenAI
import os
import json


class LLM:
    """An enhanced LLM wrapper with tool calling capabilities including web search."""

    WEB_SEARCH_TOOL = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Initiates a web search using the user's exact query text",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The exact text from the user's query to search verbatim",
                    },
                },
                "required": ["query"],
            },
        },
    }

    def __init__(self, system_prompt, api_key=None, model="gpt-4.1", enable_tools=True):
        """Initialize the LLM with extended capabilities."""
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either as an argument or through environment variables."
            )
        self.conversation_history = []
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.enable_tools = enable_tools
        self.tools = [self.WEB_SEARCH_TOOL] if enable_tools else []
        self.system_prompt = system_prompt
        self.add_message("system", self.system_prompt)

    def add_message(self, role, content, name=None):
        """Add a message to the conversation history."""
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        self.conversation_history.append(message)

    def run_with_streaming(self, message=None, tool_choice="auto"):
        """Stream a response from the LLM"""
        if message:
            self.add_message("user", message)

        kwargs = {
            "model": self.model,
            "messages": self.conversation_history,
            "stream": True,
        }

        if self.enable_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = tool_choice

        try:
            stream = self.client.chat.completions.create(**kwargs)
            return stream  # returns generator
        except Exception as e:
            print(f"Streaming error: {e}")
            raise

    def run_without_streaming(self, message=None, tool_choice="auto"):
        """Get a response from the LLM with optional tool usage.
        Returns the raw assistant message without modifying history."""
        if message:
            self.add_message("user", message)

        kwargs = {
            "model": self.model,
            "messages": self.conversation_history,
        }

        if self.enable_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = tool_choice

        try:
            response = self.client.chat.completions.create(**kwargs)
            assistant_message = response.choices[0].message
            return assistant_message

        except Exception as e:
            print(f"Error during API call: {e}")
            raise

    def run(self, message=None, stream=False, tool_choice="auto"):
        """Get a response from the LLM with optional tool usage.
        Returns the raw assistant message without modifying history."""
        if stream:
            return self.run_with_streaming(message, tool_choice)
        else:
            return self.run_without_streaming(message, tool_choice)

    def reset_history(self):
        """Reset the conversation history."""
        self.conversation_history = []
        self.add_message("system", self.system_prompt)


if __name__ == "__main__":
    from query_generator import Persona

    def interactive_chat():
        """Run an interactive chat session with tool demonstration."""
        persona = Persona("crypto_expert")
        llm = LLM(persona.prompt)

        # Set up initial system message

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() == "quit":
                    print("Goodbye!")
                    break
                if not user_input:
                    continue

                # Get initial response (won't modify history)
                response = llm.run(user_input)

                # Handle tool calls
                if hasattr(response, "tool_calls") and response.tool_calls:
                    print("\n🔍 Searching for information...")
                    for tool_call in response.tool_calls:
                        if tool_call.function.name == "web_search":
                            args = json.loads(tool_call.function.arguments)
                            print(f"Search query: {args['query']}")

                            # Simulate search results
                            mock_results = (
                                f"Search results for '{args['query']}':\n"
                                "- Royal Enfield Bullet 350: 20.2 HP, 349cc engine [source: bikewale.com]\n"
                                "- Royal Enfield Classic 350: 20.4 HP, 349cc engine [source: zigwheels.com]"
                            )
                            # Add tool response to history
                            llm.conversation_history.append(
                                {  # append result message
                                    "type": "function_call_output",
                                    "call_id": tool_call.id,
                                    "output": str(mock_results),
                                }
                            )

                    # Get final response after tool use

                # Add assistant message to history only after we're done processing
                else:
                    llm.add_message("assistant", response.content)
                    print(f"\nAssistant: {response.content}")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                continue

    interactive_chat()
