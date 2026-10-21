from typing import Tuple


class FastSentimentClassifier:
    """
    Tier-1 lightweight, high-throughput sentiment classifier.
    Evaluates comments rapidly before deciding whether to invoke the deeper LLM.
    """

    NEGATIVE_KEYWORDS = {
        "terrible", "worst", "broken", "awful", "dies", "fail", "useless", "scam",
        "horrible", "refund", "crash", "drift", "defective", "hate", "stole", "poor"
    }

    POSITIVE_KEYWORDS = {
        "amazing", "great", "excellent", "love", "best", "perfect", "good",
        "awesome", "smooth", "helpful", "superb", "fantastic", "recommend"
    }

    def classify(self, text: str) -> Tuple[str, float]:
        if not text:
            return "NEUTRAL", 0.0

        lower = text.lower()
        neg_count = sum(1 for word in self.NEGATIVE_KEYWORDS if word in lower)
        pos_count = sum(1 for word in self.POSITIVE_KEYWORDS if word in lower)

        if neg_count > pos_count:
            score = -min(1.0, 0.5 + (neg_count * 0.15))
            return "NEGATIVE", round(score, 2)
        elif pos_count > neg_count:
            score = min(1.0, 0.5 + (pos_count * 0.15))
            return "POSITIVE", round(score, 2)
        else:
            return "NEUTRAL", 0.0
