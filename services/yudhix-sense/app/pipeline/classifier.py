from typing import Tuple


class FastSentimentClassifier:
    """
    Tier-1 lightweight, high-throughput sentiment classifier.
    Evaluates comments rapidly before deciding whether to invoke the deeper LLM.
    """

    CHURN_PHRASES = {
        "done with", "done for good", "never again", "lost a customer", "no buy",
        "cant believe", "can't believe", "boycott", "own nothing", "rip off",
        "garbage", "unacceptable", "disappointed", "cancelled", "canceling", "done for"
    }

    NEGATIVE_KEYWORDS = {
        "terrible", "worst", "broken", "awful", "dies", "fail", "useless", "scam",
        "horrible", "refund", "crash", "drift", "defective", "hate", "stole", "poor"
    }

    POSITIVE_KEYWORDS = {
        "amazing", "great", "excellent", "love", "best", "perfect",
        "awesome", "smooth", "helpful", "superb", "fantastic", "recommend"
    }

    def classify(self, text: str) -> Tuple[str, float]:
        if not text:
            return "NEUTRAL", 0.0

        lower = text.lower()

        # Check critical customer churn and departure phrases first
        for phrase in self.CHURN_PHRASES:
            if phrase in lower:
                return "NEGATIVE", -0.92

        # Check positive keywords, excluding idioms like "for good"
        pos_count = 0
        for word in self.POSITIVE_KEYWORDS:
            if word in lower:
                pos_count += 1
        if "good" in lower and "for good" not in lower and "not good" not in lower:
            pos_count += 1

        neg_count = sum(1 for word in self.NEGATIVE_KEYWORDS if word in lower)

        if neg_count > pos_count:
            score = -min(1.0, 0.5 + (neg_count * 0.15))
            return "NEGATIVE", round(score, 2)
        elif pos_count > neg_count:
            score = min(1.0, 0.5 + (pos_count * 0.15))
            return "POSITIVE", round(score, 2)
        else:
            return "NEUTRAL", 0.0
