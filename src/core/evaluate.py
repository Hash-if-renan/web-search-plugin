from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas import evaluate
from datasets import Dataset


class Evaluator:
    def __init__(self):
        """Initialize the Evaluator with default metrics."""
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]

    def evaluate(self, inputs, prediction, contexts):
        """Evaluate predictions against contexts and input."""
        dataset = self.prepare_ragas_dataset(inputs, prediction, contexts)
        results = evaluate(dataset, self.metrics)

        # Convert results to a dictionary for easier access
        return results

    def prepare_ragas_dataset(self, inputs, prediction, contexts):

        data = {
            "question": [inputs],
            "answer": [prediction],
            "contexts": [contexts],  # Note: list of strings per row
        }

        return Dataset.from_dict(data)
