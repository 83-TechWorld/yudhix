"""Unit tests for the truth-first core. No database or LLM needed (the LLM is forced off)."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core import llm  # noqa: E402
from app.truth import attribution, youtube  # noqa: E402
from app.truth.claims import extract_claims  # noqa: E402
from app.truth.retrieval import KnowledgeIndex  # noqa: E402
from app.truth.scoring import impact_score, priority_band  # noqa: E402
from app.truth.verifier import verify  # noqa: E402
from app.workflow.state import Actor, WorkflowError, next_status, outcome_from  # noqa: E402

KNOWLEDGE = [
    {"id": "k1", "document_title": "PS5 Disc Drive Offline Policy", "category": "Hardware", "clause_ref": "HW-1",
     "official_statement": "The disc drive does not require a continuous online connection. After a one-time "
                           "pairing, discs play offline."},
    {"id": "k2", "document_title": "PlayStation Plus Cloud Saves", "category": "Services", "clause_ref": "SV-2",
     "official_statement": "If a subscription lapses, cloud saves are retained for 6 months grace period."},
    {"id": "k3", "document_title": "Disc Drive Retail Price", "category": "Pricing", "clause_ref": "PR-3",
     "official_statement": "The detachable disc drive retails at $79.99 in the US."},
]

AGENT = Actor("11111111-1111-4111-8111-111111111111", "agent")
APPROVER = Actor("22222222-2222-4222-8222-222222222222", "approver")


class NoLlm(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(llm, "is_available", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)


class VideoIdTest(unittest.TestCase):
    def test_parses_common_url_shapes(self):
        for url in ["https://www.youtube.com/watch?v=PTblI6oYfSU", "https://youtu.be/PTblI6oYfSU?t=10",
                    "youtube.com/shorts/PTblI6oYfSU", "https://m.youtube.com/watch?feature=x&v=PTblI6oYfSU",
                    "PTblI6oYfSU"]:
            self.assertEqual(youtube.parse_video_id(url), "PTblI6oYfSU", url)

    def test_rejects_non_youtube(self):
        with self.assertRaises(youtube.YouTubeError):
            youtube.parse_video_id("https://vimeo.com/123456")

    def test_manual_transcript_timestamps(self):
        t = youtube.parse_manual_transcript("[01:14] Discs need internet\n1:02:03 - Late claim\nno timestamp line")
        self.assertEqual([s.start for s in t.segments], [74, 3723, 3723])
        self.assertEqual(t.segments[0].text, "Discs need internet")


class VerifierTest(NoLlm):
    def setUp(self):
        super().setUp()
        self.index = KnowledgeIndex(KNOWLEDGE)

    def check(self, claim):
        return verify(claim, self.index.search(claim))

    def test_absolute_claim_contradicted_by_policy_is_misleading(self):
        v = self.check("Sony is forcing a continuous online connection on the disc drive")
        self.assertEqual(v.verdict, "MISLEADING")
        self.assertEqual(v.knowledge["id"], "k1")

    def test_matching_price_is_correct(self):
        self.assertEqual(self.check("The disc drive retails at $79.99").verdict, "FACTUALLY_CORRECT")

    def test_wrong_price_is_misleading(self):
        self.assertEqual(self.check("The detachable disc drive retails at $129.99").verdict, "MISLEADING")

    def test_unknown_topic_is_unverified(self):
        v = self.check("The new handheld has an OLED screen")
        self.assertEqual(v.verdict, "UNVERIFIED_SPECULATION")
        self.assertIsNone(v.knowledge)


class ClaimExtractionTest(NoLlm):
    def test_heuristic_picks_assertions_and_skips_filler(self):
        t = youtube.parse_manual_transcript(
            "[00:05] Hey everyone welcome back to the channel.\n"
            "[00:40] If your PlayStation Plus subscription lapses, Sony deletes your cloud saves the next day.\n"
            "[01:30] The disc drive costs $79.99 and is sold separately.\n"
            "[03:45] Don't forget to like and subscribe to the channel.")
        claims = extract_claims(t, ["PlayStation Plus", "Disc Drive"])
        self.assertEqual([c.timestamp_seconds for c in claims], [40, 90])


class AttributionTest(unittest.TestCase):
    CLAIMS = [
        {"id": "c1", "creator_quote": "Sony is forcing an online handshake on disc drives", "topic": "Offline Disc",
         "timestamp_seconds": 74, "verdict": "MISLEADING"},
        {"id": "c2", "creator_quote": "Your cloud saves are wiped when PS Plus expires", "topic": "Cloud Saves",
         "timestamp_seconds": 308, "verdict": "FALSE"},
    ]

    def test_links_comments_to_the_right_claim(self):
        comments = [
            {"id": "a", "masked_text": "Needing an online handshake to play my own discs is insane"},
            {"id": "b", "masked_text": "Losing my cloud saves because the subscription expires? No way"},
            {"id": "c", "masked_text": "Sony boycott activated"},
            {"id": "d", "masked_text": "At 5:10 he is just wrong"},
        ]
        links = {l.comment_id: l for l in attribution.attribute(self.CLAIMS, comments)}
        self.assertEqual(links["a"].claim_id, "c1")
        self.assertEqual(links["b"].claim_id, "c2")
        self.assertNotIn("c", links)  # brand words alone don't link
        self.assertEqual((links["d"].claim_id, links["d"].method), ("c2", "TIMESTAMP"))
        self.assertIn("handshake", links["a"].evidence)

    def test_root_cause(self):
        self.assertEqual(attribution.root_cause("MISLEADING"), "MISINFORMATION")
        self.assertEqual(attribution.root_cause("FACTUALLY_CORRECT"), "VALID_CONCERN")
        self.assertEqual(attribution.root_cause(None), "UNLINKED")


class ScoringTest(unittest.TestCase):
    def test_bands(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(priority_band(impact_score("NEGATIVE", 0.7, 100, 0, now)), "P1")
        self.assertEqual(priority_band(impact_score("NEGATIVE", 0.7, 100, 0, now - timedelta(days=40))), "P2")
        self.assertEqual(priority_band(impact_score("NEGATIVE", 0.7, 0, 0, now)), "P3")
        self.assertEqual(priority_band(impact_score("POSITIVE", 0.0, 5000, 50, now)), "P3")

    def test_misinformation_boost(self):
        now = datetime.now(timezone.utc)
        self.assertGreater(impact_score("NEGATIVE", 0.5, 20, 1, now, misinformation=True),
                           impact_score("NEGATIVE", 0.5, 20, 1, now))


class WorkflowStateTest(unittest.TestCase):
    def test_happy_path(self):
        s = next_status("submit", "DRAFT", AGENT, AGENT.id)
        s = next_status("approve", s, APPROVER, AGENT.id)
        self.assertEqual(next_status("post", s, AGENT, AGENT.id), "POSTED")

    def test_agent_cannot_approve(self):
        with self.assertRaises(WorkflowError) as e:
            next_status("approve", "IN_REVIEW", AGENT, APPROVER.id)
        self.assertEqual(e.exception.status_code, 403)

    def test_separation_of_duties(self):
        with self.assertRaises(WorkflowError):
            next_status("approve", "IN_REVIEW", APPROVER, APPROVER.id)

    def test_reject_needs_reason_and_can_resubmit(self):
        with self.assertRaises(WorkflowError):
            next_status("reject", "IN_REVIEW", APPROVER, AGENT.id, reason=" ")
        s = next_status("reject", "IN_REVIEW", APPROVER, AGENT.id, reason="Cite the policy")
        self.assertEqual(next_status("submit", s, AGENT, AGENT.id), "IN_REVIEW")

    def test_cannot_post_unapproved(self):
        with self.assertRaises(WorkflowError):
            next_status("post", "IN_REVIEW", AGENT, AGENT.id)

    def test_outcome(self):
        self.assertEqual(outcome_from("NEGATIVE", "POSITIVE"), "IMPROVED")
        self.assertEqual(outcome_from("NEGATIVE", "NEGATIVE"), "NEUTRAL")
        self.assertEqual(outcome_from("NEUTRAL", "NEGATIVE"), "WORSENED")


if __name__ == "__main__":
    unittest.main()
