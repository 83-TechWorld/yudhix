"""AI layer: providers, automatic fallback, anti-hallucination guards and hybrid search. No network or DB."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core import llm, providers  # noqa: E402
from app.core.providers import CATALOG, Provider, ProviderError  # noqa: E402
from app.truth import verifier  # noqa: E402
from app.truth.retrieval import KnowledgeIndex  # noqa: E402

DOCS = [
    {"id": "k1", "document_title": "PS5 Storage", "category": "Hardware", "clause_ref": "HW-2",
     "official_statement": "The PS5 Pro ships with a 2TB SSD. Storage can be expanded with an M.2 drive."},
    {"id": "k2", "document_title": "Disc Drive Retail Price", "category": "Pricing", "clause_ref": "PR-3",
     "official_statement": "The detachable disc drive retails at $79.99 in the US."},
]


def res(status, body):
    return mock.Mock(status_code=status, json=lambda: body, text=str(body))


class ProviderTest(unittest.TestCase):
    def test_parse_json_tolerates_fences(self):
        self.assertEqual(providers.parse_json('```json\n{"ok": true}\n```'), {"ok": True})
        self.assertEqual(providers.parse_json('Sure! {"a": 1} hope that helps'), {"a": 1})
        self.assertIsNone(providers.parse_json("no json here"))

    def test_chat_model_filter_and_suggestion(self):
        ids = ["gpt-4o-mini", "text-embedding-3-small", "whisper-1", "gpt-4o", "tts-1", "dall-e-3"]
        chat = [i for i in ids if providers._is_chat_model("openai", i)]
        self.assertEqual(sorted(chat), ["gpt-4o", "gpt-4o-mini"])
        self.assertEqual(providers.suggest_model(CATALOG["anthropic"], ["claude-haiku-5-5", "claude-sonnet-5-5"]),
                         "claude-sonnet-5-5")

    def test_anthropic_request_shape(self):
        p = Provider(CATALOG["anthropic"], "claude-sonnet-5-5", api_key="sk-test")
        with mock.patch.object(providers.httpx, "post",
                               return_value=res(200, {"content": [{"type": "text", "text": '{"ok": true}'}]})) as post:
            self.assertEqual(p.generate_json("hi"), {"ok": True})
        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["x-api-key"], "sk-test")
        self.assertIn("JSON", kwargs["json"]["system"])

    def test_gemini_and_openai_embeddings(self):
        g = Provider(CATALOG["gemini"], "gemini-x-flash", api_key="g", embed_model="text-embedding-x")
        with mock.patch.object(providers.httpx, "post", return_value=res(200, {"embeddings": [{"values": [1, 0]}]})):
            self.assertEqual(g.embed(["a"]), [[1, 0]])
        o = Provider(CATALOG["openai"], "gpt-x", api_key="o", embed_model="text-embedding-3-small")
        body = {"data": [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}]}
        with mock.patch.object(providers.httpx, "post", return_value=res(200, body)):
            self.assertEqual(o.embed(["a", "b"]), [[1, 0], [0, 1]])
        self.assertFalse(Provider(CATALOG["anthropic"], "c", api_key="k").can_embed)

    def test_rejected_key_is_an_auth_error(self):
        p = Provider(CATALOG["openai"], "gpt-x", api_key="bad")
        with mock.patch.object(providers.httpx, "post", return_value=res(401, {"error": {"message": "Incorrect API key"}})):
            with self.assertRaises(ProviderError) as ctx:
                p.generate("hi")
        self.assertTrue(ctx.exception.auth)
        with mock.patch.object(providers.httpx, "get", return_value=res(400, {"error": {"message": "API key not valid"}})):
            with self.assertRaises(ProviderError) as ctx:
                Provider(CATALOG["gemini"], "", api_key="bad").list_models()
        self.assertTrue(ctx.exception.auth)


class FallbackTest(unittest.TestCase):
    def test_cloud_failure_falls_back_to_local_and_marks_key(self):
        cloud = mock.Mock(cloud=True, label="Claude")
        cloud.generate.side_effect = ProviderError("401", auth=True)
        local = mock.Mock(cloud=False, label="Local")
        local.generate.return_value = '{"from": "local"}'
        with mock.patch.object(llm, "cloud", return_value=cloud), mock.patch.object(llm, "local", return_value=local), \
                mock.patch.object(llm, "_key_rejected") as rejected:
            self.assertEqual(llm.generate_json("x"), {"from": "local"})
        rejected.assert_called_once()

    def test_no_engine_returns_none(self):
        with mock.patch.object(llm, "cloud", return_value=None), mock.patch.object(llm, "local", return_value=None):
            self.assertIsNone(llm.generate_json("x"))
            self.assertIsNone(llm.embed(["x"]))
            self.assertEqual(llm.describe()["mode"], "RULES")

    def test_keys_are_encrypted(self):
        from app.platform import ai_settings
        token = ai_settings.encrypt("sk-secret-1234")
        self.assertNotIn("sk-secret", token)
        self.assertEqual(ai_settings.decrypt(token), "sk-secret-1234")
        self.assertIsNone(ai_settings.decrypt("garbage"))


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.hits = KnowledgeIndex(DOCS).search("PS5 Pro SSD storage size", k=2)

    def _llm(self, *replies):
        return mock.patch.object(llm, "generate_json", side_effect=list(replies))

    def test_quote_and_number_checks(self):
        self.assertTrue(verifier.quote_in_source("ships with a 2TB SSD", DOCS[0]["official_statement"]))
        self.assertFalse(verifier.quote_in_source("comes with a 4TB SSD and free games", DOCS[0]["official_statement"]))
        self.assertTrue(verifier.numbers_conflict("The PS5 Pro has a 1TB SSD", "ships with a 2TB SSD"))
        self.assertFalse(verifier.numbers_conflict("disc drive costs $79.99", "retails at $79.99"))

    def test_invented_quote_is_rejected(self):
        reply = {"source_index": 0, "source_says": "The PS5 Pro includes 4TB of storage for free", "relation": "SUPPORTS",
                 "confidence": 0.9, "analysis": "Matches."}
        with mock.patch.object(verifier, "_second_opinion_on", return_value=False), self._llm(reply):
            v = verifier.verify("The PS5 Pro includes 4TB of storage", self.hits)
        self.assertTrue(v.needs_review)
        self.assertNotEqual(v.method, "LLM")
        self.assertIn("isn't in the official source", v.review_reason)

    def test_supports_with_wrong_figures_becomes_misleading(self):
        reply = {"source_index": 0, "source_says": "The PS5 Pro ships with a 2TB SSD.", "relation": "SUPPORTS",
                 "confidence": 0.9, "analysis": "Matches."}
        with mock.patch.object(verifier, "_second_opinion_on", return_value=False), self._llm(reply):
            v = verifier.verify("The PS5 Pro ships with a 1TB SSD", self.hits)
        self.assertEqual((v.verdict, v.needs_review, v.method), ("MISLEADING", True, "LLM"))
        self.assertEqual(v.source_quote, "The PS5 Pro ships with a 2TB SSD.")

    def test_second_opinion_disagreement_needs_review(self):
        a = {"source_index": 0, "source_says": "ships with a 2TB SSD", "relation": "SUPPORTS", "confidence": 0.9}
        b = dict(a, relation="CONTRADICTS")
        with mock.patch.object(verifier, "_second_opinion_on", return_value=True), self._llm(a, b):
            v = verifier.verify("The PS5 Pro ships with a 2TB SSD", self.hits)
        self.assertTrue(v.needs_review)
        self.assertLessEqual(v.confidence, 0.5)
        self.assertIn("disagreed", v.review_reason)

    def test_no_evidence_never_asks_the_ai(self):
        hits = KnowledgeIndex(DOCS).search("GTA 6 release date delayed", k=2)
        with mock.patch.object(llm, "generate_json") as gen:
            v = verifier.verify("GTA 6 release date delayed again", hits)
        gen.assert_not_called()
        self.assertEqual(v.verdict, "UNVERIFIED_SPECULATION")


class HybridSearchTest(unittest.TestCase):
    def test_meaning_finds_a_fact_with_no_shared_words(self):
        index = KnowledgeIndex(DOCS)
        index.vectors, index.model = [[1.0, 0.0], [0.0, 1.0]], "openai/text-embedding-3-small"
        # "how much does the add-on cost" shares no keywords with the price clause, but means it
        with mock.patch.object(llm, "embed", return_value=("openai/text-embedding-3-small", [[0.1, 0.99]])):
            hits = index.search("how much is the add-on", k=1)
        self.assertEqual(hits[0].doc["id"], "k2")
        self.assertGreater(hits[0].similarity, 0.9)
        self.assertTrue(verifier.has_evidence(hits))

    def test_keyword_only_without_embeddings(self):
        index = KnowledgeIndex(DOCS)
        self.assertEqual(index.search("disc drive price", k=1)[0].doc["id"], "k2")


if __name__ == "__main__":
    unittest.main()
