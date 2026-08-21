# src/weakness_tracker.py
import json
import os
import random
import math
from utils import load_available_topics

WEAKNESS_TRACKER_PATH = "data/state/tracker.json"
ALLOWED_TOPICS = load_available_topics()
class WeaknessTracker:
    """
    Tracks per‑topic weakness scores and samples topics
    with higher probability for weak areas.
    """
    def __init__(self):
        # scores: higher = weaker
        self.temperature = 1.5  # softness of weighting
        self._load_scores()
        if not self.scores:
            self.scores = {topic : 0 for topic in ALLOWED_TOPICS}

    def _load_scores(self):
        if os.path.exists(WEAKNESS_TRACKER_PATH):
            try:
                with open(WEAKNESS_TRACKER_PATH, "r") as f:
                    self.scores = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.scores = {}
        else:
            self.scores = {}

        if len(self.scores) < len(ALLOWED_TOPICS):
            self.scores = {topic: self.scores.get(topic, 0) for topic in ALLOWED_TOPICS} 
    def _save_scores(self):
        os.makedirs(os.path.dirname(WEAKNESS_TRACKER_PATH), exist_ok=True)  
        with open(WEAKNESS_TRACKER_PATH, "w") as f:
            json.dump(self.scores, f, indent=2)
    
    def update(self, topic: str, correct: bool):
        if topic not in self.scores:
            self.scores[topic] = 0.0
        if correct:
            self.scores[topic] = max(0.0, self.scores[topic] - 0.5)
        else:
            self.scores[topic] += 1.0
        self._save_scores()

    def sample_topic(self) -> str:
        """Return a topic using softmax over weakness scores."""
        if not self.scores:
            # return random topic
            return random.choice(ALLOWED_TOPICS)
        topics = list(self.scores.keys())

        # exponentiate scores to increase differences scaled by temperaturu
        exp_scores = [math.exp(self.scores[t] / self.temperature) for t in topics]
        total = sum(exp_scores)
        probs = [s / total for s in exp_scores]
        return random.choices(topics, weights=probs, k=1)[0]

    def get_all_topics(self) -> list[str]:
        return list(self.scores.keys())