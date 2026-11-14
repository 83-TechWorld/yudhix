"""Unit tests: no database or Keycloak needed. Data functions are replaced with fixed numbers."""
import unittest
from datetime import date, datetime, timezone
from unittest import mock

from fastapi.testclient import TestClient

from app import auth, build, catalog, data, main, pdf
from app.auth import Principal, Workspace

NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)
A, B = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
USER = Principal("sub-1", "ceo@example.com", "Casey CEO")
WS = [Workspace(A, "Acme Audio", "admin", False, "PROFESSIONAL"), Workspace(B, "Beta Games (Demo)", "analyst", True, "ENTERPRISE")]


def counts(total, pos, neg, misinfo=0, ai=0):
    return {"total": total, "positive": pos, "negative": neg, "neutral": total - pos - neg, "misinfo_negative": misinfo,
            "ai_read": ai, "unread": 0, "p1": 0, "likes": 0}


FAKE = {
    "comments": lambda ids, w: {A: {"YOUTUBE": counts(200, 40, 80, misinfo=30, ai=20), "AMAZON": counts(20, 18, 1, ai=20)},
                                B: {"YOUTUBE": counts(100, 50, 10, ai=100)}} if w.key != "prev" else {},
    "trend": lambda ids, w: [{"bucket": date(2026, 10, 1), "grain": "month", "positive": 5, "negative": 3, "neutral": 2}],
    "claims": lambda ids, w: {A: {"videos": 3, "total": 10, "correct": 5, "misleading": 3, "false": 1, "unverified": 1,
                                  "needsReview": 2, "byAi": 6, "byRules": 2, "byHuman": 1, "seeded": 1, "accuracy": 0.6,
                                  "views": 500_000, "viewsMisleading": 300_000, "videosMisleading": 2}},
    "risky_videos": lambda ids, w: [{"ws": A, "videoId": "v1", "title": "Is it worth it? <b>", "channel": "Chan",
                                     "views": None, "accuracy": 0.4, "misleading": 3, "claims": 4, "negativeComments": 12}],
    "products": lambda ids, w: [{"ws": A, "id": "p1", "name": "Acme Buds ★ Pro", "category": None,
                                 "youtube": {"total": 50, "positive": 10, "negative": 30},
                                 "amazon": {"total": 20, "positive": 18, "negative": 1}, "rating": 4.4,
                                 "ratingsCount": 1200, "listings": 1}],
    "replies": lambda ids, w: {A: {"total": 10, "draft": 1, "in_review": 6, "approved": 0, "posted": 3, "rejected": 0,
                                   "sla_breached": 5, "reviewHours": 3.5, "postHours": 20.0, "improved": 2,
                                   "unchanged": 1, "worsened": 1, "pending": 0}},
    "ideas": lambda ids: {"byWorkspace": {A: {"NEW": 3, "PLANNED": 1}},
                          "top": [{"ws": A, "title": "Longer battery", "topic": "battery", "status": "NEW", "comments": 9, "likes": 40}]},
    "operations": lambda ids, w: {
        "ai": {B: {"mode": "CLOUD", "provider": "anthropic", "model": "claude-sonnet-5-5", "embedModel": None, "status": "VALID"}},
        "jobs": {A: [{"kind": "COMMENTS", "trigger": "SCHEDULE", "runs": 10, "ok": 4, "failed": 6, "active": 0, "avgSeconds": 30,
                      "lastError": 'YouTube comments error 403: {"error": {"code": 403, "message": "quotaExceeded"}}'}]},
        "listings": {A: {"OK": 1, "BLOCKED": 1}},
        "knowledge": {A: {"facts": 10, "documents": 1, "embedded": 4, "syncedAt": None, "oldestCheck": None,
                          "latestCheck": None, "staleVideos": 2, "watchEnabled": True, "watchHours": 6},
                      B: {"facts": 0, "documents": 0, "embedded": 0, "syncedAt": None, "oldestCheck": None,
                          "latestCheck": NOW, "staleVideos": 0, "watchEnabled": False, "watchHours": 6}}},
    "team": lambda ids, w: {"roles": {A: {"admin": 1, "agent": 3}, B: {"analyst": 2}}, "lastSeen": {A: NOW},
                            "plans": {A: {"plan": "PROFESSIONAL", "status": "ACTIVE", "interval": "MONTH", "renews": None,
                                          "trialEnds": None}}, "usage": {}},
}


class FakeData:
    def __enter__(self):
        self.patches = [mock.patch.object(data, name, fn) for name, fn in FAKE.items()]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()


def blocks(report, section, kind):
    return [b for s in report["sections"] if s["id"] == section for b in s["blocks"] if b["type"] == kind]


class CatalogTest(unittest.TestCase):
    def test_audience_defaults_and_custom_order(self):
        self.assertEqual(catalog.sections_for("technology", None), catalog.AUDIENCES["technology"]["sections"])
        # custom picks keep the audience's order, extras follow in catalog order, unknown ids dropped
        self.assertEqual(catalog.sections_for("executive", ["team", "risks", "summary", "nope"]), ["summary", "risks", "team"])
        self.assertEqual(catalog.sections_for("executive", ["nope"]), catalog.AUDIENCES["executive"]["sections"])

    def test_windows(self):
        w = catalog.window("30d", NOW)
        self.assertEqual((w.end - w.start).days, 30)
        self.assertEqual(w.previous.end, w.start)
        self.assertIsNone(catalog.window("all", NOW).previous)
        self.assertEqual(catalog.window("bogus", NOW).key, catalog.DEFAULT_PERIOD)


class BuildTest(unittest.TestCase):
    def build(self, audience="executive", sections=None, workspaces=WS):
        with FakeData():
            return build.build(USER, workspaces, audience, "90d", sections, now=NOW)

    def test_every_section_builds_for_every_audience(self):
        for aud in catalog.AUDIENCES:
            r = self.build(aud, list(catalog.SECTIONS))
            self.assertEqual(len(r["sections"]), len(catalog.SECTIONS))
            for s in r["sections"]:
                self.assertTrue(s["blocks"], s["id"])

    def test_summary_numbers(self):
        k = {i["label"]: i for i in blocks(self.build(), "summary", "kpis")[0]["items"]}
        self.assertEqual(k["Comments and reviews"]["value"], "320")
        self.assertEqual(k["Net sentiment"]["value"], "+5")       # (108 - 91) / 320
        self.assertEqual(k["Creator claims wrong"]["value"], "40%")  # 4 of 10
        self.assertEqual(k["Replies posted"]["value"], "3")

    def test_risks_are_ranked_and_plain(self):
        rows = blocks(self.build(), "risks", "table")[0]["rows"]
        self.assertEqual(rows[0][0], "High")
        self.assertEqual([r[0] for r in rows], sorted([r[0] for r in rows], key=build.SEVERITY_ORDER.get))
        text = " ".join(" ".join(r) for r in rows)
        self.assertIn("300K views", text)
        self.assertIn("past the response deadline", text)
        self.assertIn("daily quota", text)           # the 403 is explained ...
        self.assertNotIn('"error"', text)             # ... and the raw JSON never shown
        self.assertIn("Automatic checks for new comments are turned off", text)

    def test_single_workspace_hides_workspace_columns(self):
        r = self.build(sections=["risks", "truth"], workspaces=WS[:1])
        for t in blocks(r, "risks", "table") + blocks(r, "truth", "table"):
            self.assertNotIn("Workspace", [c["label"] for c in t["columns"]])

    def test_unknown_views_are_not_zero(self):
        row = blocks(self.build(sections=["truth"]), "truth", "table")[0]["rows"][0]
        self.assertIn("–", row)

    def test_technology_summary_is_technical(self):
        r = self.build("technology")
        labels = [i["label"] for i in blocks(r, "summary", "kpis")[0]["items"]]
        self.assertIn("Pipeline runs", labels)
        engines = blocks(r, "operations", "table")[0]["rows"]
        self.assertIn("Anthropic claude-sonnet-5-5", [row[1] for row in engines])

    def test_explain_error(self):
        self.assertIn("gone", build.explain_error("COMMENTS", "YouTube comments error 404: {...}")[0])
        self.assertIn("robot", build.explain_error("AMAZON", "AmazonBlocked: robot check")[0])
        self.assertEqual(build.explain_error("COMMENTS", None)[0], None)


class PdfTest(unittest.TestCase):
    def test_renders_a_pdf_with_odd_characters(self):
        with FakeData():
            r = build.build(USER, WS, "executive", "90d", list(catalog.SECTIONS), now=NOW)
        out = pdf.render(r)
        self.assertTrue(out.startswith(b"%PDF"))
        self.assertGreater(len(out), 5000)

    def test_text_is_safe_for_helvetica(self):
        self.assertEqual(pdf.safe("a <b> & ★ → 😀"), "a &lt;b&gt; &amp; * &gt; ")


class ApiTest(unittest.TestCase):
    def setUp(self):
        main.app.dependency_overrides[auth.principal] = lambda: USER
        self.client = TestClient(main.app)
        self.mine = mock.patch.object(auth, "my_workspaces", lambda user: WS)
        self.mine.start()

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.mine.stop()

    def test_needs_sign_in(self):
        main.app.dependency_overrides.clear()
        self.assertEqual(TestClient(main.app).get("/api/v1/reports/options").status_code, 401)

    def test_options_list_my_workspaces(self):
        with mock.patch.object(main, "my_workspaces", lambda user: WS):
            body = self.client.get("/api/v1/reports/options").json()
        self.assertEqual([w["id"] for w in body["workspaces"]], [A, B])
        self.assertEqual({a["id"] for a in body["audiences"]}, set(catalog.AUDIENCES))

    def test_refuses_other_workspaces(self):
        r = self.client.post("/api/v1/reports/preview", json={"workspaceIds": [A, "33333333-3333-3333-3333-333333333333"]})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.post("/api/v1/reports/preview", json={"workspaceIds": []}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/reports/preview",
                                          json={"workspaceIds": [A], "period": "5y"}).status_code, 400)

    def test_preview_and_pdf(self):
        with FakeData():
            r = self.client.post("/api/v1/reports/preview", json={"workspaceIds": [A, B], "audience": "care"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["audience"]["id"], "care")
            p = self.client.post("/api/v1/reports/pdf", json={"workspaceIds": [A], "audience": "product"})
        self.assertEqual(p.status_code, 200)
        self.assertEqual(p.headers["content-type"], "application/pdf")
        self.assertIn('filename="Yudhix-Product-report-Acme-Audio-', p.headers["content-disposition"])
        self.assertTrue(p.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
