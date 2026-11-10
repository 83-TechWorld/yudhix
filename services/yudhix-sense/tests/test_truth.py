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
        for name in ("cloud", "local"):  # no AI engine at all: rules and retrieval only
            patcher = mock.patch.object(llm, name, return_value=None)
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
            {"id": "d", "masked_text": "At 5:10 he is just wrong about saves"},
            {"id": "e", "masked_text": "At 5:10 he is just wrong"},
            {"id": "f", "masked_text": "Bro put a song in for no reason 1:20"},
            {"id": "g", "masked_text": "I thought he was right, the tech is fine"},
        ]
        links = {l.comment_id: l for l in attribution.attribute(self.CLAIMS, comments)}
        self.assertEqual(links["a"].claim_id, "c1")
        self.assertEqual(links["b"].claim_id, "c2")
        self.assertNotIn("c", links)  # brand words alone don't link
        self.assertEqual((links["d"].claim_id, links["d"].method), ("c2", "TIMESTAMP"))
        self.assertIn("handshake", links["a"].evidence)
        self.assertNotIn("e", links)  # a timestamp alone isn't enough
        self.assertNotIn("f", links)
        self.assertNotIn("g", links)  # everyday words don't link

    def test_ai_decision_wins(self):
        comments = [{"id": "a", "masked_text": "Needing an online handshake to play my own discs is insane"},
                    {"id": "b", "masked_text": "Whatever, cloud saves expire anyway"}]
        ai = {"a": {"claim": None, "why": ""}, "b": {"claim": "c2", "why": "cloud saves expire"}}
        links = {l.comment_id: l for l in attribution.attribute(self.CLAIMS, comments, ai)}
        self.assertNotIn("a", links)
        self.assertEqual((links["b"].claim_id, links["b"].method, links["b"].evidence), ("c2", "AI", "cloud saves expire"))

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


class AudienceTest(unittest.TestCase):
    def test_rule_topics(self):
        from app.truth.audience import rule_topics
        self.assertEqual(rule_topics("The PS5 should only cost $299, way too expensive")[0], "PRICE")
        self.assertIn("SERVICE", rule_topics("Paying monthly for PS Plus online is a joke"))
        self.assertEqual(rule_topics("lol"), [])

    def test_parse_ai_results(self):
        from app.truth.audience import _parse
        batch = [{"id": "x"}, {"id": "y"}, {"id": "z"}]
        claims = [{"id": "c1"}, {"id": "c2"}]
        out = _parse({"results": [
            {"i": 1, "s": "NEG", "t": ["price", "BOGUS"], "c": 2, "w": "costs too much", "n": "complaint"},
            {"i": 2, "s": "POS", "t": [], "c": 0, "w": "ignored", "n": "IDEA", "f": "more storage space please now ok"},
            {"i": 3, "s": "???"},               # unknown sentiment: left to rules
            {"i": 9, "s": "NEG"},               # out of range
        ]}, batch, claims)
        self.assertEqual(out["x"], {"sentiment": "NEGATIVE", "topics": ["PRICE"], "claim": "c2",
                                    "why": "costs too much", "intent": "COMPLAINT", "idea": ""})
        self.assertEqual(out["y"]["claim"], None)
        self.assertEqual((out["y"]["intent"], out["y"]["idea"]), ("IDEA", "more storage space please now ok"))
        self.assertEqual(out["y"]["why"], "")
        self.assertNotIn("z", out)


class ProductImpactTest(unittest.TestCase):
    def test_reach_weighting_and_score(self):
        from app.truth import product_impact
        now = datetime.now(timezone.utc)
        rows = [
            {"id": "1", "like_count": 2500, "reply_count": 100, "sentiment": "NEGATIVE", "verdict": "MISLEADING",
             "topics": ["PRICE"], "platform_created_at": now, "model_version": "llm/x"},
            {"id": "2", "like_count": 0, "reply_count": 0, "sentiment": "POSITIVE", "verdict": None,
             "topics": [], "platform_created_at": now, "model_version": "rules"},
        ] + [{"id": f"p{i}", "like_count": 0, "reply_count": 0, "sentiment": "POSITIVE", "verdict": None,
              "topics": ["QUALITY"], "platform_created_at": now - timedelta(days=30)} for i in range(50)]
        r = product_impact.compute(rows, now)
        # 51 positive comments vs 1 negative, but the negative one has almost all the reach
        self.assertEqual(r["sentiment"]["byComments"], {"positive": 51, "neutral": 0, "negative": 1})
        self.assertGreater(r["negativeShareOfReach"], 0.95)
        self.assertEqual(r["level"], "HIGH")
        self.assertEqual(r["topics"][0]["topic"], "PRICE")
        self.assertEqual(r["negativeByCause"][0], {"cause": "MISINFORMATION", "comments": 1, "reach": 2701, "share": 1.0})
        self.assertEqual(r["topNegative"][0]["id"], "1")
        self.assertEqual(r["coverage"]["aiComments"], 1)
        self.assertIn("price", r["headline"])

    def test_empty(self):
        from app.truth import product_impact
        r = product_impact.compute([])
        self.assertEqual((r["score"], r["level"], r["trend"]), (0, "LOW", "QUIET"))
        self.assertEqual(r["timeline"]["points"], [])


class SamplingTest(unittest.TestCase):
    def test_spread_picks_newest_oldest_and_middle(self):
        pool = [{"comment_id": str(i)} for i in range(500)]  # newest first
        picked = youtube.pick_spread(pool, 100, seed="x")
        ids = [int(c["comment_id"]) for c in picked]
        self.assertEqual(len(ids), 100)
        self.assertEqual(len(set(ids)), 100)
        self.assertEqual(ids[:40], list(range(40)))            # 40 newest
        self.assertEqual(ids[-40:], list(range(460, 500)))     # 40 oldest
        self.assertTrue(all(40 <= i < 460 for i in ids[40:60]))  # 20 from the middle
        self.assertEqual(ids, [int(c["comment_id"]) for c in youtube.pick_spread(pool, 100, seed="x")])

    def test_small_videos_keep_everything(self):
        pool = [{"comment_id": str(i)} for i in range(30)]
        self.assertEqual(youtube.pick_spread(pool, 100), pool)


class IntentRulesTest(unittest.TestCase):
    def test_intents(self):
        from app.truth.audience import rule_intent
        self.assertEqual(rule_intent("Please add a sleep timer to the controller.", "NEUTRAL"), "IDEA")
        self.assertEqual(rule_intent("I wish they made it with more storage", "NEGATIVE"), "IDEA")
        self.assertEqual(rule_intent("They should be ashamed of this price", "NEGATIVE"), "COMPLAINT")
        self.assertEqual(rule_intent("Just pre-ordered mine, can't wait!", "POSITIVE"), "BUY")
        self.assertEqual(rule_intent("Returning it tomorrow, not worth it", "NEGATIVE"), "LEAVE")
        self.assertEqual(rule_intent("Not buying this at $700", "NEGATIVE"), "LEAVE")
        self.assertEqual(rule_intent("Does it come with a stand?", "NEUTRAL"), "QUESTION")
        self.assertEqual(rule_intent("Best console ever", "POSITIVE"), "PRAISE")
        self.assertEqual(rule_intent("This is overpriced garbage", "NEGATIVE"), "COMPLAINT")


class IdeaGroupingTest(unittest.TestCase):
    def test_similar_requests_share_an_idea(self):
        from app.truth import growth
        self.assertEqual(growth.theme_key("Add more storage"), growth.theme_key("more Storage please"))
        self.assertEqual(growth.theme_words("cheaper digital games"), ["cheaper", "digital", "game"])
        ideas = [{"id": "a", "theme_key": "storage"}, {"id": "b", "theme_key": "cheaper digital game"}]
        self.assertEqual(growth.match_idea(growth.theme_words("bigger storage"), ideas)["id"], "a")  # half the words match
        self.assertEqual(growth.match_idea(growth.theme_words("cheaper digital games price"), ideas)["id"], "b")
        self.assertEqual(growth.match_idea(growth.theme_words("sleep timer"), ideas), None)


class GrowthTest(unittest.TestCase):
    def test_growth_view(self):
        from app.truth import growth
        rows = [
            {"id": "1", "like_count": 900, "reply_count": 0, "sentiment": "POSITIVE", "intent": "PRAISE",
             "topics": ["CONTENT"], "model_version": "llm/x"},
            {"id": "2", "like_count": 40, "reply_count": 5, "sentiment": "NEUTRAL", "intent": "IDEA",
             "topics": ["QUALITY"], "idea_id": "i1", "idea_title": "More storage", "idea_status": "NEW"},
            {"id": "3", "like_count": 2, "reply_count": 0, "sentiment": "NEGATIVE", "intent": "IDEA",
             "topics": [], "idea_id": "i1", "idea_title": "More storage", "idea_status": "NEW"},
            {"id": "4", "like_count": 0, "reply_count": 0, "sentiment": "POSITIVE", "intent": "BUY", "topics": []},
            {"id": "5", "like_count": 0, "reply_count": 0, "sentiment": "NEGATIVE", "intent": "GENERAL", "topics": []},
        ]
        r = growth.compute(rows)
        self.assertEqual(r["level"], "STRONG")
        self.assertEqual(r["loved"][0]["topic"], "CONTENT")
        self.assertEqual(r["ideas"][0]["id"], "i1")
        self.assertEqual((r["ideas"][0]["comments"], r["ideas"][0]["reach"]), (2, 54))
        self.assertEqual(r["ideaComments"], 2)
        self.assertEqual(r["buyingSignals"][0]["id"], "4")
        intents = {i["intent"]: i["comments"] for i in r["intents"]}
        self.assertEqual((intents["COMPLAINT"], intents["PRAISE"]), (1, 1))  # old GENERAL + negative -> complaint
        self.assertIn("More storage", r["headline"])

    def test_empty(self):
        from app.truth import growth
        r = growth.compute([])
        self.assertEqual((r["score"], r["level"], r["headline"]), (0, "LOW", "No comments yet."))


class NewCommentsTest(unittest.TestCase):
    def test_stops_at_first_known_comment(self):
        page = {"items": [{"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": cid, "snippet": {
            "textOriginal": cid, "likeCount": 0, "publishedAt": "2026-11-01T00:00:00Z"}}}} for cid in
            ("n1", "n2", "old1", "old2")], "nextPageToken": "more"}
        res = mock.Mock(status_code=200, json=lambda: page)
        with mock.patch.object(youtube, "has_api_key", return_value=True), \
                mock.patch.object(youtube.httpx, "get", return_value=res) as get:
            out = youtube.fetch_new_comments("vid", {"old1", "old2"}, 100)
        self.assertEqual([c["comment_id"] for c in out], ["n1", "n2"])
        self.assertEqual(get.call_count, 1)  # never reads the next page
