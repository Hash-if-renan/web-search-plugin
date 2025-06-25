import os
from dotenv import load_dotenv
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    AnswerAccuracy,
    ResponseGroundedness,
)
from ragas.metrics._factual_correctness import FactualCorrectness
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class Evaluator:
    def __init__(self):
        """Initialize the Evaluator with default LLM and metrics."""
        llm = llm_factory()
        embeddings = embedding_factory()

        self.factual_metric = FactualCorrectness(llm=llm)
        self.faithfulness_metric = Faithfulness(llm=llm)
        self.relevancy_metric = ResponseRelevancy(llm=llm, embeddings=embeddings)
        self.answer_accuracy_metric = AnswerAccuracy(llm=llm)
        self.groundedness_metric = ResponseGroundedness(llm=llm)

    async def evaluate(self, inputs: str, prediction: str, contexts: list[str] | str):
        """Evaluate predictions using RAGAS metrics."""
        if isinstance(contexts, str):
            contexts = [contexts]

        reference = " ".join(contexts)

        sample = {
            "factual": SingleTurnSample(response=prediction, reference=reference),
            "faithful": SingleTurnSample(
                user_input=inputs, response=prediction, retrieved_contexts=contexts
            ),
            "accuracy": SingleTurnSample(
                user_input=inputs, response=prediction, reference=reference
            ),
            "grounded": SingleTurnSample(
                response=prediction, retrieved_contexts=contexts
            ),
        }

        return {
            "factual_correctness": await self.factual_metric.single_turn_ascore(
                sample["factual"]
            ),
            "faithfulness": await self.faithfulness_metric.single_turn_ascore(
                sample["faithful"]
            ),
            "response_relevancy": await self.relevancy_metric.single_turn_ascore(
                sample["faithful"]
            ),
            "answer_accuracy": await self.answer_accuracy_metric.single_turn_ascore(
                sample["accuracy"]
            ),
            "response_groundedness": await self.groundedness_metric.single_turn_ascore(
                sample["grounded"]
            ),
        }


if __name__ == "__main__":
    import asyncio

    async def main():
        evaluator = Evaluator()
        inputs = "What is the capital of France?"
        prediction = "The capital of France is Paris."
        contexts = ["Paris is the capital of France."]

        results = await evaluator.evaluate(inputs, prediction, contexts)
        print(results)

    asyncio.run(main())
