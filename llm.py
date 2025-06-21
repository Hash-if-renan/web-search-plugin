from dotenv import load_dotenv
from openai import OpenAI
import os


class LLM:
    """A simple wrapper for OpenAI's LLM to manage conversation history and interactions."""

    def __init__(self, api_key=None, model="gpt-4o"):
        """Initialize the LLM with an API key and model.

        Args:
            api_key (str, optional): OpenAI API key. Defaults to None (will use environment variable).
            model (str, optional): Model to use. Defaults to "gpt-4o".
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either as an argument or through environment variables."
            )
        self.conversation_history = []
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def add_message(self, role, content):
        """Add a message to the conversation history.

        Args:
            role (str): "system", "user", or "assistant"
            content (str): The message content
        """
        self.conversation_history.append({"role": role, "content": content})

    def run(self, message=None, stream=False):
        """Get a response from the LLM.

        Args:
            message (str, optional): If provided, adds a user message before getting response.
            stream (bool): Whether to stream the response.

        Returns:
            The assistant's response (either Message object or Stream)
        """
        if message:
            self.add_message("user", message)

        kwargs = {
            "model": self.model,
            "messages": self.conversation_history,
        }

        if stream:
            return self.client.chat.completions.create(**kwargs, stream=True)
        else:
            response = self.client.chat.completions.create(**kwargs)
            assistant_message = response.choices[0].message
            self.add_message("assistant", assistant_message.content)
            return assistant_message

    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []


# sample test
if __name__ == "__main__":

    def interactive_chat():
        """Run an interactive chat session with the LLM."""
        llm = LLM()

        # Set up initial system message
        llm.add_message(
            "system", "You are a helpful assistant. Be concise in your answers."
        )

        print(
            "\nChat with the AI assistant! (Type 'quit' to exit, 'reset' to start new conversation)"
        )

        while True:
            try:
                user_input = input("\nYou: ")

                if user_input.lower() == "quit":
                    print("Goodbye!")
                    break

                if user_input.lower() == "reset":
                    llm.reset_conversation()
                    llm.add_message(
                        "system",
                        "You are a helpful assistant. Be concise in your answers.",
                    )
                    print("Conversation reset. New session started.")
                    continue

                # Get and display response
                response = llm.run(user_input)
                print(f"\nAssistant: {response.content}")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nAn error occurred: {e}")
                continue

    interactive_chat()
