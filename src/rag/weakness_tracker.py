# src/weakness_tracker.py
import random
import math

class WeaknessTracker:
    """
    Tracks per‑topic weakness scores and samples topics
    with higher probability for weak areas.
    """
    def __init__(self, default_scores: dict[str, float] | None = None):
        # scores: higher = weaker
        self.scores = default_scores.copy() if default_scores else {}
        self.temperature = 1.5  # softness of weighting

    def update(self, topic: str, correct: bool):
        if topic not in self.scores:
            self.scores[topic] = 0.0
        if correct:
            self.scores[topic] = max(0.0, self.scores[topic] - 0.5)
        else:
            self.scores[topic] += 1.0

    def sample_topic(self) -> str:
        """Return a topic using softmax over weakness scores."""
        if not self.scores:
            return "General Biology"
        topics = list(self.scores.keys())
        # exponentiate scores scaled by temperature
        exp_scores = [math.exp(self.scores[t] / self.temperature) for t in topics]
        total = sum(exp_scores)
        probs = [s / total for s in exp_scores]
        return random.choices(topics, weights=probs, k=1)[0]

    def get_all_topics(self) -> list[str]:
        return list(self.scores.keys())