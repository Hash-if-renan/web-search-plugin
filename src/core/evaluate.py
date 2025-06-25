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
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class Evaluator:
    def __init__(self):
        """Initialize the Evaluator with default LLM and metrics."""
        self.llm = llm_factory()
        self.embeddings = embedding_factory()
        self.factual_metric = FactualCorrectness(llm=self.llm)
        self.faithfulness_metric = Faithfulness(llm=self.llm)
        self.relevancy_metric = ResponseRelevancy(
            llm=self.llm, embeddings=self.embeddings
        )
        self.answer_accuracy_metric = AnswerAccuracy(llm=self.llm)
        self.groundedness_metric = ResponseGroundedness(llm=self.llm)

    async def evaluate(self, inputs, prediction, contexts):
        """Evaluate predictions against contexts and input using RAGAS metrics."""
        # Ensure contexts is a list of strings
        if isinstance(contexts, str):
            contexts = [contexts]

        factual_sample = SingleTurnSample(
            response=prediction, reference=" ".join(contexts)
        )

        faithful_sample = SingleTurnSample(
            user_input=inputs, response=prediction, retrieved_contexts=contexts
        )

        answer_accuracy_sample = SingleTurnSample(
            user_input=inputs,
            response=prediction,
            reference=" ".join(contexts),
        )

        answer_groundedness_sample = SingleTurnSample(
            response=prediction,
            retrieved_contexts=contexts,
        )

        # Evaluate both metrics asynchronously
        factual_score = await self.factual_metric.single_turn_ascore(factual_sample)
        faithful_score = await self.faithfulness_metric.single_turn_ascore(
            faithful_sample
        )
        relevance_score = await self.relevancy_metric.single_turn_ascore(
            faithful_sample
        )
        answer_accuracy_score = await self.answer_accuracy_metric.single_turn_ascore(
            answer_accuracy_sample
        )
        answer_groundedness_score = await self.groundedness_metric.single_turn_ascore(
            answer_groundedness_sample
        )

        return {
            "factual_correctness": factual_score,
            "faithfulness": faithful_score,
            "response_relevancy": relevance_score,
            "answer_accuracy": answer_accuracy_score,
            "response_groundedness": answer_groundedness_score,
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
