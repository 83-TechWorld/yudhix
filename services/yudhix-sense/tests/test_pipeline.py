import unittest
import sys
import os

# Add service directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.masker import PiiMasker
from app.pipeline.classifier import FastSentimentClassifier


class PipelineTest(unittest.TestCase):

    def test_pii_masker_scrubs_sensitive_entities(self):
        masker = PiiMasker()
        sample = "Call me at +91 9876543210 or email test@example.com for order #12345. Aadhaar is 2345 6789 0123"

        masked, entities = masker.mask(sample)

        self.assertNotIn("+91 9876543210", masked)
        self.assertNotIn("test@example.com", masked)
        self.assertNotIn("2345 6789 0123", masked)
        self.assertIn("<PHONE>", masked)
        self.assertIn("<EMAIL>", masked)
        self.assertIn("<GOV_ID>", masked)
        self.assertIn("PHONE", entities)
        self.assertIn("EMAIL", entities)

    def test_fast_sentiment_classifier(self):
        classifier = FastSentimentClassifier()

        neg_text = "The controller battery dies in 2 hours, terrible and broken."
        sentiment, score = classifier.classify(neg_text)
        self.assertEqual("NEGATIVE", sentiment)
        self.assertTrue(score < 0)

        pos_text = "Amazing game, I love the graphics, fantastic experience!"
        pos_sentiment, pos_score = classifier.classify(pos_text)
        self.assertEqual("POSITIVE", pos_sentiment)
        self.assertTrue(pos_score > 0)


if __name__ == "__main__":
    unittest.main()

