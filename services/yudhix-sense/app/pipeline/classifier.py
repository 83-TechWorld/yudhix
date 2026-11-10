import re
from typing import Tuple


def _has(term: str, text: str) -> bool:
    """Whole-word / whole-phrase match, so 'rent' does not match 'current'."""
    return re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text) is not None


class FastSentimentClassifier:
    """
    Tier-1 lightweight, high-throughput sentiment classifier.
    Evaluates comments rapidly before deciding whether to invoke the deeper LLM.
    """

    CHURN_PHRASES = {
        "done with", "done for good", "never again", "lost a customer", "no buy",
        "cant believe", "can't believe", "boycott", "own nothing", "rip off",
        "garbage", "unacceptable", "disappointed", "cancelled", "canceling", "done for",
        "never buy", "never buying", "not buying", "won't buy", "wont buy", "stop giving", "last console",
        "switching to", "go back to", "sold my", "selling my", "reasons to never", "anti-consumer", "anti consumer"
    }

    NEGATIVE_KEYWORDS = {
        "terrible", "worst", "broken", "awful", "dies", "fail", "useless", "scam",
        "horrible", "refund", "crash", "drift", "defective", "hate", "stole", "poor",
        "pirate", "pirates", "pirating", "piracy", "boycotting", "greed", "greedy", "ridiculous", "pathetic", "sucks", "trash", "joke",
        "scummy", "shame", "shameful", "lost their minds", "killing", "rent", "renting", "ripoff",
        "worse", "insane", "disgusting", "overpriced", "bad"
    }

    POSITIVE_KEYWORDS = {
        "amazing", "great", "excellent", "love", "best", "perfect",
        "awesome", "smooth", "helpful", "superb", "fantastic", "recommend",
        "thanks", "thank you", "glad", "happy", "works now", "working now", "fixed", "appreciate"
    }

    def classify(self, text: str) -> Tuple[str, float]:
        if not text:
            return "NEUTRAL", 0.0

        lower = text.lower()

        # Check critical customer churn and departure phrases first
        for phrase in self.CHURN_PHRASES:
            if _has(phrase, lower):
                return "NEGATIVE", -0.92

        # Check positive keywords, excluding idioms like "for good"
        pos_count = 0
        for word in self.POSITIVE_KEYWORDS:
            if _has(word, lower):
                pos_count += 1
        if _has("good", lower) and "for good" not in lower and "not good" not in lower:
            pos_count += 1

        neg_count = sum(1 for word in self.NEGATIVE_KEYWORDS if _has(word, lower))

        if neg_count > pos_count:
            score = -min(1.0, 0.5 + (neg_count * 0.15))
            return "NEGATIVE", round(score, 2)
        elif pos_count > neg_count:
            score = min(1.0, 0.5 + (pos_count * 0.15))
            return "POSITIVE", round(score, 2)
        else:
            return "NEUTRAL", 0.0
