"""Turns the numbers into a report: sections made of a few block types that both the web preview
and the PDF know how to draw.

Block types
  kpis      {items: [{label, value, sub?, delta?: {text, tone}, tone?}]}
  findings  {items: [{tone: good|warn|bad|info, text}]}
  table     {columns: [{label, align}], rows: [[cell, ...]], empty?}
  bars      {title, rows: [{label, sub?, negative, neutral, positive}]}   sentiment split per row
  trend     {title, grain, points: [{label, negative, neutral, positive}]}
  note      {text}

Every sentence is written from the numbers by fixed rules. No AI writes report text, so nothing in a
report can be made up.
"""
from datetime import datetime, timezone
from functools import cached_property
from typing import Dict, List, Optional

from app import catalog, data
from app.auth import ROLE_LABELS, Principal, Workspace
from app.catalog import Window

TONES = ("good", "warn", "bad", "info")


# ---- formatting -------------------------------------------------------------------------------

def num(n: Optional[float]) -> str:
    if n is None:
        return "–"
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 10_000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return f"{int(round(n)):,}"


def pct(part: float, whole: float) -> str:
    return f"{round(100 * part / whole)}%" if whole else "–"


def ratio(part: float, whole: float) -> Optional[float]:
    return part / whole if whole else None


def net(c: Dict) -> Optional[int]:
    """Net sentiment: % positive minus % negative, from -100 to +100."""
    t = c.get("total", 0)
    return round(100 * (c.get("positive", 0) - c.get("negative", 0)) / t) if t else None


def neg_share(c: Dict) -> Optional[float]:
    """% of comments that are negative, or None when there are none."""
    t = c.get("total", 0)
    return 100 * c.get("negative", 0) / t if t else None


def in_period(w: Window) -> str:
    """"in the last 90 days", or "yet" for all time."""
    return "yet" if w.start is None else f"in the {w.label.lower()}"


def signed(n: Optional[float]) -> str:
    if n is None:
        return "–"
    n = int(round(n))
    return f"+{n}" if n > 0 else str(n)


def hours(h: Optional[float]) -> str:
    if h is None:
        return "–"
    if h < 1:
        return f"{max(1, round(h * 60))} min"
    if h < 48:
        return f"{h:.1f} h".replace(".0 h", " h")
    return f"{h / 24:.1f} days".replace(".0 days", " days")


def when(d: Optional[datetime]) -> str:
    return d.strftime("%d %b %Y") if d else "–"


def delta(cur: Optional[float], prev: Optional[float], unit: str = "", higher_is_good: bool = True,
          as_pct: bool = False) -> Optional[Dict]:
    """"+12% vs previous period", toned by whether the move is good."""
    if cur is None or prev is None:
        return None
    if as_pct:
        if not prev:
            return None
        change = round(100 * (cur - prev) / prev)
        text = f"{signed(change)}% vs previous period"
    else:
        change = round(cur - prev)
        text = f"{signed(change)}{unit} vs previous period"
    if change == 0:
        return {"text": "No change vs previous period", "tone": "info"}
    good = (change > 0) == higher_is_good
    return {"text": text, "tone": "good" if good else "bad"}


def kpi(label: str, value: str, sub: Optional[str] = None, d: Optional[Dict] = None, tone: str = "info") -> Dict:
    return {"label": label, "value": value, "sub": sub, "delta": d, "tone": tone}


def col(label: str, align: str = "left") -> Dict:
    return {"label": label, "align": align}


def add(a: Dict, b: Dict) -> Dict:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


# ---- context: data loaded once, only when a section asks for it ---------------------------------

class Ctx:
    def __init__(self, workspaces: List[Workspace], w: Window):
        self.workspaces = workspaces
        self.ids = [x.id for x in workspaces]
        self.names = {x.id: x.name for x in workspaces}
        self.w = w
        self.multi = len(workspaces) > 1

    @cached_property
    def comments(self):
        return data.comments(self.ids, self.w)

    @cached_property
    def comments_prev(self):
        return data.comments(self.ids, self.w.previous) if self.w.previous else None

    @cached_property
    def trend(self):
        return data.trend(self.ids, self.w)

    @cached_property
    def claims(self):
        return data.claims(self.ids, self.w)

    @cached_property
    def risky(self):
        return data.risky_videos(self.ids, self.w)

    @cached_property
    def products(self):
        return data.products(self.ids, self.w)

    @cached_property
    def replies(self):
        return data.replies(self.ids, self.w)

    @cached_property
    def replies_prev(self):
        return data.replies(self.ids, self.w.previous) if self.w.previous else None

    @cached_property
    def ideas(self):
        return data.ideas(self.ids)

    @cached_property
    def ops(self):
        return data.operations(self.ids, self.w)

    @cached_property
    def team(self):
        return data.team(self.ids, self.w)

    # totals
    def ws_comments(self, ws: str, source: Optional[Dict] = None) -> Dict:
        total: Dict = {}
        for c in (source if source is not None else self.comments).get(ws, {}).values():
            total = add(total, c)
        return total

    def all_comments(self, source: Optional[Dict] = None) -> Dict:
        total: Dict = {}
        for ws in self.ids:
            total = add(total, self.ws_comments(ws, source))
        return total

    def channel(self, platform: str) -> Dict:
        total: Dict = {}
        for ws in self.ids:
            total = add(total, self.comments.get(ws, {}).get(platform, {}))
        return total

    def all_claims(self) -> Dict:
        total: Dict = {}
        for c in self.claims.values():
            total = add(total, {k: v for k, v in c.items() if isinstance(v, int)})
        return total

    def all_replies(self, source: Optional[Dict] = None) -> Dict:
        total: Dict = {}
        for r in (source if source is not None else self.replies).values():
            total = add(total, {k: v for k, v in r.items() if isinstance(v, int)})
        return total

    def ws_label(self, ws: str) -> str:
        return self.names.get(ws, "Workspace")


def turnaround(r: Dict) -> Optional[float]:
    judged = r.get("improved", 0) + r.get("unchanged", 0) + r.get("worsened", 0)
    return ratio(r.get("improved", 0), judged)


def wrong(c: Dict) -> int:
    return c.get("misleading", 0) + c.get("false", 0)


# ---- risks: one list, used by the risks section and the summary -------------------------------

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def risks(ctx: Ctx) -> List[Dict]:
    out: List[Dict] = []

    def r(sev, ws, risk, action):
        out.append({"severity": sev, "ws": ws, "workspace": ctx.ws_label(ws) if ws else "All", "risk": risk,
                    "action": action})

    for ws in ctx.ids:
        c = ctx.ws_comments(ws)
        cl = ctx.claims.get(ws, {})
        rep = ctx.replies.get(ws, {})
        ops_ai = ctx.ops["ai"].get(ws)
        kn = ctx.ops["knowledge"].get(ws, {})
        listings = ctx.ops["listings"].get(ws, {})

        if cl.get("viewsMisleading", 0) >= 100_000:
            r("High", ws, f"Videos with misleading or false claims reached {num(cl['viewsMisleading'])} views.",
              "Open the worst videos, publish corrections from your official sources and contact the creators.")
        elif wrong(cl):
            r("Medium", ws, f"{wrong(cl)} creator claim{'s' if wrong(cl) != 1 else ''} about your products "
                            f"{'were' if wrong(cl) != 1 else 'was'} misleading or false.",
              "Reply with the official fact on those videos and track whether opinion turns.")
        if c.get("negative", 0) >= 10 and ratio(c.get("misinfo_negative", 0), c["negative"]) and \
                c["misinfo_negative"] / c["negative"] >= 0.25:
            r("High", ws, f"{pct(c['misinfo_negative'], c['negative'])} of negative comments trace back to wrong "
                          f"creator claims.",
              "Prioritise correcting those claims: it is the cheapest way to win back opinion.")
        n = net(c)
        if n is not None and c.get("total", 0) >= 20 and n <= -20:
            r("High", ws, f"Audience mood is clearly negative (net sentiment {signed(n)}).",
              "Read the top negative themes in Products and Inbox, and answer the most-liked complaints first.")
        if rep.get("sla_breached"):
            r("High" if rep["sla_breached"] >= 5 else "Medium", ws,
              f"{rep['sla_breached']} repl{'ies are' if rep['sla_breached'] != 1 else 'y is'} past the response deadline.",
              "Clear the Approvals queue or add an approver.")
        if rep.get("in_review", 0) >= 5:
            r("Medium", ws, f"{rep['in_review']} replies are waiting for review.", "Ask approvers to clear the queue.")
        if cl.get("needsReview"):
            r("Medium", ws, f"{cl['needsReview']} claim verdict{'s' if cl['needsReview'] != 1 else ''} need a person to check them.",
              "Open each flagged claim, compare it with the evidence and confirm or override the verdict.")
        for j in ctx.ops["jobs"].get(ws, []):
            if j["runs"] >= 5 and j["failed"] / j["runs"] >= 0.2:
                label = JOB_LABELS.get(j["kind"], j["kind"].title())
                cause, action = explain_error(j["kind"], j.get("lastError"))
                r("High" if j["failed"] / j["runs"] >= 0.5 else "Medium", ws,
                  f"{label} ({TRIGGER_LABELS.get(j['trigger'], j['trigger']).lower()}) failed {j['failed']} of "
                  f"{j['runs']} times.{' Most recent cause: ' + cause + '.' if cause else ''}", action)
        if listings.get("BLOCKED") or listings.get("FAILED"):
            bad = listings.get("BLOCKED", 0) + listings.get("FAILED", 0)
            r("Medium", ws, f"{bad} Amazon listing{'s' if bad != 1 else ''} could not be read.",
              "Retry later, or set AMAZON_REVIEWS_API_KEY to read reviews through the provider.")
        if c.get("total", 0) >= 50 and ratio(c.get("ai_read", 0), c["total"]) is not None \
                and c["ai_read"] / c["total"] < 0.5:
            engine = "local AI" if not ops_ai or ops_ai.get("mode") != "CLOUD" else "cloud AI"
            r("Low", ws, f"Only {pct(c['ai_read'], c['total'])} of comments were read by AI; the rest by keyword rules ({engine}).",
              "Connect a cloud AI in Settings > AI, or re-analyze to read the remaining comments.")
        if cl.get("total") and not kn.get("facts"):
            r("Medium", ws, "Claims are being checked without any official documents in the knowledge base.",
              "Upload product guides and policies in Knowledge so claims are checked against your sources.")
        elif kn.get("facts") and kn.get("embedded", 0) < kn["facts"]:
            missing = kn["facts"] - kn.get("embedded", 0)
            r("Low", ws, f"{missing} knowledge fact{'s are' if missing != 1 else ' is'} not yet synced with the AI.",
              "Run Sync in Knowledge so fact search uses every document.")
        if kn.get("staleVideos"):
            r("Low", ws, f"{kn['staleVideos']} video{'s have' if kn['staleVideos'] != 1 else ' has'} verdicts made before the knowledge base changed.",
              "Re-check claims on those videos.")
        if kn.get("watchEnabled") is False:
            r("Low", ws, "Automatic checks for new comments are turned off.", "Turn them on in the comment schedule.")
        if not c.get("total") and not cl.get("videos"):
            r("Low", ws, "No comments or analyzed videos yet." if ctx.w.start is None else
              f"No comments or analyzed videos {in_period(ctx.w)}.",
              "Analyze recent videos and add Amazon listings to start tracking.")
    out.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], x["workspace"]))
    return out


def explain_error(kind: str, error: Optional[str]):
    """A failed job's error in plain words, and what to do about it. Raw API errors are never shown."""
    e = (error or "").lower()
    code = next((c for c in ("404", "403", "401", "429", "400", "500", "503") if c in e), None)
    if kind == "AMAZON":
        if "robot" in e or "captcha" in e or "blocked" in e:
            return ("Amazon showed a robot check", "Retry later, or set AMAZON_REVIEWS_API_KEY to read reviews "
                                                   "through the provider.")
        return ("Amazon page could not be read" if e else None,
                "Open the listing, check the link still works and run the check again.")
    if code == "404":
        return ("YouTube says the video is gone or its comments are turned off",
                "Remove deleted or private videos from tracking; nothing is wrong with the key.")
    if code in ("403", "429") or "quota" in e:
        return ("YouTube refused the request (daily quota used up or key not allowed)",
                "Check the YouTube API key's quota in Google Cloud Console, or check comments less often.")
    if code in ("401", "400") and "key" in e:
        return ("the YouTube API key was rejected", "Replace the YouTube API key in the service settings.")
    if "timeout" in e or "timed out" in e:
        return ("the request timed out", "Usually temporary; it runs again on the next schedule.")
    first = (error or "").strip().splitlines()[0][:90].rstrip(" {:") if error else ""
    return (first or None, "Open the job log in the video page and run it again.")


JOB_LABELS = {"ANALYZE": "Video analysis", "COMMENTS": "New-comment checks", "FACTS": "Claim re-checks",
              "AMAZON": "Amazon review checks"}
TRIGGER_LABELS = {"USER": "Started by a person", "SCHEDULE": "Scheduled"}


# ---- sections ---------------------------------------------------------------------------------

def s_summary(ctx: Ctx, audience: str) -> List[Dict]:
    c, p = ctx.all_comments(), (ctx.all_comments(ctx.comments_prev) if ctx.comments_prev is not None else None)
    cl = ctx.all_claims()
    rep = ctx.all_replies()
    rep_prev = ctx.all_replies(ctx.replies_prev) if ctx.replies_prev is not None else None
    ta = turnaround(rep)

    if audience == "technology":
        jobs = [j for ws in ctx.ids for j in ctx.ops["jobs"].get(ws, [])]
        runs, ok, failed = sum(j["runs"] for j in jobs), sum(j["ok"] for j in jobs), sum(j["failed"] for j in jobs)
        cloud = sum(1 for ws in ctx.ids if (ctx.ops["ai"].get(ws) or {}).get("mode") == "CLOUD")
        facts = sum(k["facts"] for k in ctx.ops["knowledge"].values())
        embedded = sum(k["embedded"] for k in ctx.ops["knowledge"].values())
        guarded = cl.get("byAi", 0) + cl.get("byRules", 0) + cl.get("byHuman", 0) + cl.get("seeded", 0)
        items = [
            kpi("Workspaces", num(len(ctx.ids)), f"{cloud} on cloud AI · {len(ctx.ids) - cloud} on local AI"),
            kpi("Pipeline runs", num(runs), f"{pct(ok, runs)} succeeded · {failed} failed",
                tone="bad" if runs and failed / runs >= 0.2 else "good" if runs else "info"),
            kpi("Comments read by AI", pct(c.get("ai_read", 0), c.get("total", 0)),
                f"{num(c.get('ai_read', 0))} of {num(c.get('total', 0))}; the rest by keyword rules"),
            kpi("Claims checked", num(cl.get("total", 0)),
                f"{pct(cl.get('byAi', 0), guarded)} by AI with evidence · {cl.get('byHuman', 0)} by a person"),
            kpi("Needs a person", num(cl.get("needsReview", 0)), "claim verdicts flagged by the accuracy guards",
                tone="warn" if cl.get("needsReview") else "good"),
            kpi("Knowledge facts", num(facts), f"{pct(embedded, facts)} synced for AI search"),
        ]
    else:
        n, n_prev = net(c), (net(p) if p else None)
        items = [
            kpi("Comments and reviews", num(c.get("total", 0)),
                f"across {len(ctx.ids)} workspace{'s' if len(ctx.ids) != 1 else ''}",
                delta(c.get("total", 0), p.get("total", 0) if p else None, as_pct=True)),
            kpi("Net sentiment", signed(n), "% positive minus % negative",
                delta(n, n_prev, " pts"), tone="good" if (n or 0) > 10 else "bad" if (n or 0) < -10 else "info"),
            kpi("Negative share", pct(c.get("negative", 0), c.get("total", 0)),
                f"{num(c.get('negative', 0))} negative",
                delta(neg_share(c), neg_share(p) if p else None, " pts", higher_is_good=False)),
            kpi("Creator claims wrong", pct(wrong(cl), cl.get("total", 0)),
                f"{wrong(cl)} of {cl.get('total', 0)} claims in {cl.get('videos', 0)} videos",
                tone="bad" if cl.get("total") and wrong(cl) / cl["total"] >= 0.25 else "info"),
            kpi("Negativity from misinformation", pct(c.get("misinfo_negative", 0), c.get("negative", 0)),
                "negative comments linked to a wrong claim"),
            kpi("Replies posted", num(rep.get("posted", 0)),
                f"turnaround rate {f'{round(100 * ta)}%' if ta is not None else '–'}",
                delta(rep.get("posted", 0), rep_prev.get("posted", 0) if rep_prev else None)),
        ]
    return [{"type": "kpis", "items": items}, {"type": "findings", "items": findings(ctx, audience)}]


def tech_findings(ctx: Ctx) -> List[Dict]:
    """Findings for a technology audience: reliability, AI coverage, accuracy guards, data freshness."""
    out: List[Dict] = []
    jobs = [j for ws in ctx.ids for j in ctx.ops["jobs"].get(ws, [])]
    done = sum(j["ok"] + j["failed"] for j in jobs)
    ok = sum(j["ok"] for j in jobs)
    if done:
        manual = [j for j in jobs if j["trigger"] == "USER"]
        m_done = sum(j["ok"] + j["failed"] for j in manual)
        rate = ok / done
        text = f"Pipeline success rate {round(100 * rate)}% over {num(done)} runs"
        if m_done:
            text += f"; runs started by people succeeded {pct(sum(j['ok'] for j in manual), m_done)} of the time"
        out.append({"tone": "good" if rate >= 0.9 else "warn" if rate >= 0.7 else "bad", "text": text + "."})
    c = ctx.all_comments()
    if c.get("total"):
        share = c.get("ai_read", 0) / c["total"]
        out.append({"tone": "good" if share >= 0.8 else "warn",
                    "text": f"AI read {pct(c.get('ai_read', 0), c['total'])} of {num(c['total'])} comments; the rest "
                            f"were classified by keyword rules, which miss sarcasm and product ideas."})
    cl = ctx.all_claims()
    if cl.get("total"):
        out.append({"tone": "warn" if cl.get("needsReview") else "good",
                    "text": f"{num(cl['total'])} claims checked; {cl.get('needsReview', 0)} flagged by the accuracy guards "
                            f"for a person, {cl.get('byHuman', 0)} confirmed or overridden by a person."})
    cloud = [ws for ws in ctx.ids if (ctx.ops["ai"].get(ws) or {}).get("mode") == "CLOUD"]
    out.append({"tone": "info", "text": (
        f"{len(cloud)} of {len(ctx.ids)} workspace{'s' if len(ctx.ids) != 1 else ''} use a cloud AI; the others run on "
        f"the local model, so no workspace text leaves your infrastructure for them.")})
    facts = sum(k["facts"] for k in ctx.ops["knowledge"].values())
    embedded = sum(k["embedded"] for k in ctx.ops["knowledge"].values())
    if facts:
        out.append({"tone": "good" if embedded >= facts else "warn",
                    "text": f"Knowledge base: {num(facts)} official facts, {pct(embedded, facts)} indexed for AI fact search."})
    top = [x for x in risks(ctx) if x["severity"] == "High"]
    if top:
        out.append({"tone": "bad", "text": f"{len(top)} high-priority risk{'s need' if len(top) != 1 else ' needs'} "
                                           f"attention. Top: {top[0]['risk']}"})
    return out[:6]


def findings(ctx: Ctx, audience: str) -> List[Dict]:
    if audience == "technology":
        return tech_findings(ctx)
    out: List[Dict] = []
    c = ctx.all_comments()
    p = ctx.all_comments(ctx.comments_prev) if ctx.comments_prev is not None else None
    n = net(c)
    if n is not None:
        if p and p.get("total", 0) >= 20 and net(p) is not None:
            move = n - net(p)
            if abs(move) >= 5:
                out.append({"tone": "good" if move > 0 else "bad",
                            "text": f"Audience mood {'improved' if move > 0 else 'worsened'} from {signed(net(p))} to "
                                    f"{signed(n)} net sentiment compared with the previous period."})
            else:
                out.append({"tone": "info", "text": f"Audience mood held steady at {signed(n)} net sentiment."})
        else:
            out.append({"tone": "good" if n > 10 else "bad" if n < -10 else "info",
                        "text": f"{num(c['total'])} comments and reviews, {pct(c['positive'], c['total'])} positive and "
                                f"{pct(c['negative'], c['total'])} negative (net {signed(n)})."})
    if ctx.multi:
        ranked = [(net(ctx.ws_comments(ws)), ws) for ws in ctx.ids if ctx.ws_comments(ws).get("total", 0) >= 20]
        ranked = [x for x in ranked if x[0] is not None]
        if len(ranked) >= 2:
            ranked.sort()
            lo, hi = ranked[0], ranked[-1]
            if hi[0] - lo[0] >= 10:
                out.append({"tone": "info", "text": f"{ctx.ws_label(hi[1])} has the warmest audience ({signed(hi[0])}); "
                                                    f"{ctx.ws_label(lo[1])} the coolest ({signed(lo[0])})."})
    if c.get("negative", 0) >= 10 and c.get("misinfo_negative"):
        out.append({"tone": "warn", "text": f"{pct(c['misinfo_negative'], c['negative'])} of negative comments trace "
                                            f"back to misleading or false creator claims, not to the products themselves."})
    yt, az = ctx.channel("YOUTUBE"), ctx.channel("AMAZON")
    if yt.get("total", 0) >= 10 and az.get("total", 0) >= 5:
        gap = (net(az) or 0) - (net(yt) or 0)
        if abs(gap) >= 20:
            better, worse = ("Amazon buyers", "YouTube viewers") if gap > 0 else ("YouTube viewers", "Amazon buyers")
            out.append({"tone": "info", "text": f"{better} are noticeably more positive than {worse} "
                                                f"(net {signed(max(net(az), net(yt)))} vs {signed(min(net(az), net(yt)))}): "
                                                f"perception on video differs from experience after purchase."})
    rep = ctx.all_replies()
    ta = turnaround(rep)
    if ta is not None:
        out.append({"tone": "good" if ta >= 0.5 else "warn",
                    "text": f"{round(100 * ta)}% of answered negative comments turned neutral or positive after a reply."})
    open_ideas = sum(v for ws in ctx.ideas["byWorkspace"].values() for k, v in ws.items() if k in ("NEW", "REVIEWING"))
    if open_ideas and audience in ("executive", "product"):
        out.append({"tone": "info", "text": f"{open_ideas} product idea{'s' if open_ideas != 1 else ''} from customers "
                                            f"{'are' if open_ideas != 1 else 'is'} waiting for a decision."})
    top = [x for x in risks(ctx) if x["severity"] == "High"]
    if top:
        out.append({"tone": "bad", "text": f"{len(top)} high-priority risk{'s need' if len(top) != 1 else ' needs'} "
                                           f"attention. Top: {top[0]['risk']}"})
    if not out:
        out.append({"tone": "info", "text": "Not enough activity in this period to draw conclusions yet."})
    return out[:6]


def s_risks(ctx: Ctx, audience: str) -> List[Dict]:
    items = risks(ctx)
    if not items:
        return [{"type": "findings", "items": [{"tone": "good", "text": "Nothing needs attention right now."}]}]
    cols = [col("Priority"), col("Risk"), col("Recommended action")]
    if ctx.multi:
        cols.insert(1, col("Workspace"))
    rows = [[x["severity"], *([x["workspace"]] if ctx.multi else []), x["risk"], x["action"]] for x in items[:12]]
    return [{"type": "table", "columns": cols, "rows": rows, "severityColumn": 0}]


def s_workspaces(ctx: Ctx, audience: str) -> List[Dict]:
    rows, bars = [], []
    for ws in ctx.ids:
        c, cl, rep = ctx.ws_comments(ws), ctx.claims.get(ws, {}), ctx.replies.get(ws, {})
        open_ideas = sum(v for k, v in ctx.ideas["byWorkspace"].get(ws, {}).items() if k in ("NEW", "REVIEWING"))
        acc = cl.get("accuracy")
        rows.append([ctx.ws_label(ws), num(c.get("total", 0)), signed(net(c)), pct(c.get("negative", 0), c.get("total", 0)),
                     f"{wrong(cl)} / {cl.get('total', 0)}", f"{round(acc * 100)}%" if acc is not None and acc <= 1 else
                     (f"{round(acc)}%" if acc is not None else "–"),
                     num(rep.get("posted", 0)), num(open_ideas)])
        if c.get("total"):
            bars.append({"label": ctx.ws_label(ws), "sub": f"{num(c['total'])} comments",
                         "negative": c.get("negative", 0), "neutral": c.get("neutral", 0), "positive": c.get("positive", 0)})
    blocks = [{"type": "table", "columns": [
        col("Workspace"), col("Comments", "right"), col("Net", "right"), col("Negative", "right"),
        col("Wrong claims", "right"), col("Accuracy", "right"), col("Replies posted", "right"), col("Open ideas", "right")],
        "rows": rows}]
    if bars:
        blocks.append({"type": "bars", "title": "Sentiment by workspace", "rows": bars})
    return blocks


def _bucket_label(b, grain: str) -> str:
    if grain == "day":
        return b.strftime("%d %b")
    if grain == "week":
        return "Wk " + b.strftime("%d %b")
    if grain == "quarter":
        return f"Q{(b.month - 1) // 3 + 1} {b.year}"
    return b.strftime("%b %Y")


def s_sentiment(ctx: Ctx, audience: str) -> List[Dict]:
    blocks: List[Dict] = []
    pts = ctx.trend
    if pts:
        grain = pts[0]["grain"]
        blocks.append({"type": "trend", "title": f"Comments and reviews per {grain}", "grain": grain,
                       "points": [{"label": _bucket_label(x["bucket"], grain), "negative": x["negative"],
                                   "neutral": x["neutral"], "positive": x["positive"]} for x in pts]})
    rows = []
    for platform, label, noun in (("YOUTUBE", "YouTube", "comments"), ("AMAZON", "Amazon", "reviews")):
        c = ctx.channel(platform)
        if c.get("total"):
            rows.append({"label": label, "sub": f"{num(c['total'])} {noun} · net {signed(net(c))}",
                         "negative": c["negative"], "neutral": c["neutral"], "positive": c["positive"]})
    if rows:
        blocks.append({"type": "bars", "title": "By channel", "rows": rows})
    if not blocks:
        blocks.append({"type": "note", "text": f"No comments or reviews were written {in_period(ctx.w)}."})
    else:
        blocks.append({"type": "note", "text": "Counted by the date each comment or review was written. "
                                               "Amazon review sentiment comes from the star rating."})
    return blocks


def s_truth(ctx: Ctx, audience: str) -> List[Dict]:
    cl = ctx.all_claims()
    if not cl.get("videos"):
        return [{"type": "note", "text": f"No videos were analyzed {in_period(ctx.w)}."}]
    blocks = [{"type": "kpis", "items": [
        kpi("Videos analyzed", num(cl["videos"]),
            f"{num(cl['views'])} total views" if cl.get("views") else "view counts not recorded"),
        kpi("Claims checked", num(cl.get("total", 0))),
        kpi("Correct", num(cl.get("correct", 0)), pct(cl.get("correct", 0), cl.get("total", 0)), tone="good"),
        kpi("Misleading", num(cl.get("misleading", 0)), pct(cl.get("misleading", 0), cl.get("total", 0)),
            tone="warn" if cl.get("misleading") else "info"),
        kpi("False", num(cl.get("false", 0)), pct(cl.get("false", 0), cl.get("total", 0)),
            tone="bad" if cl.get("false") else "info"),
        kpi("Views on videos with wrong claims", num(cl["viewsMisleading"]) if cl.get("views") else "–",
            f"{cl.get('videosMisleading', 0)} video{'s' if cl.get('videosMisleading', 0) != 1 else ''}",
            tone="bad" if cl.get("viewsMisleading", 0) >= 100_000 else "info"),
    ]}]
    if ctx.risky:
        cols = [col("Video"), col("Channel"), col("Views", "right"), col("Wrong / claims", "right"),
                col("Negative comments", "right")]
        if ctx.multi:
            cols.insert(1, col("Workspace"))
        rows = [[v["title"], *([ctx.ws_label(v["ws"])] if ctx.multi else []), v["channel"] or "–", num(v["views"]) if v["views"] else "–",
                 f"{v['misleading']} / {v['claims']}", num(v["negativeComments"])] for v in ctx.risky]
        blocks.append({"type": "table", "title": "Videos that matter most", "columns": cols, "rows": rows})
    checked = cl.get("byAi", 0) + cl.get("byRules", 0) + cl.get("byHuman", 0) + cl.get("seeded", 0)
    if checked:
        blocks.append({"type": "note", "text": (
            f"How verdicts were reached: {pct(cl.get('byAi', 0), checked)} by AI against your official documents, "
            f"{pct(cl.get('byRules', 0), checked)} by rules, {pct(cl.get('byHuman', 0), checked)} confirmed by a person, "
            f"{pct(cl.get('seeded', 0), checked)} from sample data. An AI verdict needs a quote from your sources; "
            f"without one the claim is marked for a person to review.")})
    return blocks


def s_products(ctx: Ctx, audience: str) -> List[Dict]:
    items = ctx.products
    if not items:
        return [{"type": "note", "text": "No products set up in the selected workspaces."}]
    cols = [col("Product"), col("YouTube comments", "right"), col("YouTube net", "right"),
            col("Amazon reviews", "right"), col("Amazon net", "right"), col("Rating", "right")]
    if ctx.multi:
        cols.insert(1, col("Workspace"))
    rows, bars = [], []
    for p in items[:ctx_rows()]:
        yt, az = p["youtube"], p["amazon"]
        rows.append([p["name"], *([ctx.ws_label(p["ws"])] if ctx.multi else []), num(yt["total"]), signed(net(yt)),
                     num(az["total"]), signed(net(az)),
                     f"{p['rating']}/5 ({num(p['ratingsCount'])})" if p["rating"] is not None else "–"])
        both = add(yt, az)
        if both.get("total"):
            bars.append({"label": p["name"], "sub": f"{num(both['total'])} comments and reviews",
                         "negative": both["negative"], "positive": both["positive"],
                         "neutral": both["total"] - both["negative"] - both["positive"]})
    blocks = [{"type": "table", "columns": cols, "rows": rows}]
    if bars:
        blocks.append({"type": "bars", "title": "Sentiment by product, all channels", "rows": bars[:8]})
    blocks.append({"type": "note", "text": "Ratings are the listing's current Amazon average. Videos count only when "
                                           "they are linked to a product."})
    return blocks


def ctx_rows() -> int:
    from app import config
    return config.TABLE_ROWS


def s_care(ctx: Ctx, audience: str) -> List[Dict]:
    r, prev = ctx.all_replies(), (ctx.all_replies(ctx.replies_prev) if ctx.replies_prev is not None else None)
    review_h = [x["reviewHours"] for x in ctx.replies.values() if x.get("reviewHours") is not None]
    post_h = [x["postHours"] for x in ctx.replies.values() if x.get("postHours") is not None]
    ta = turnaround(r)
    blocks = [{"type": "kpis", "items": [
        kpi("Replies drafted", num(r.get("total", 0)), None,
            delta(r.get("total", 0), prev.get("total", 0) if prev else None)),
        kpi("Posted", num(r.get("posted", 0)), pct(r.get("posted", 0), r.get("total", 0)) + " of drafts"),
        kpi("Waiting for review", num(r.get("in_review", 0)), f"{r.get('draft', 0)} still drafts",
            tone="warn" if r.get("in_review", 0) >= 5 else "info"),
        kpi("Past deadline", num(r.get("sla_breached", 0)), "open replies past their SLA",
            tone="bad" if r.get("sla_breached") else "good"),
        kpi("Review time", hours(sum(review_h) / len(review_h) if review_h else None), "submitted → approved, average"),
        kpi("Turnaround rate", f"{round(100 * ta)}%" if ta is not None else "–",
            f"{r.get('improved', 0)} improved · {r.get('unchanged', 0)} unchanged · {r.get('worsened', 0)} worsened",
            tone="good" if ta is not None and ta >= 0.5 else "info"),
    ]}]
    if ctx.multi:
        rows = []
        for ws in ctx.ids:
            x = ctx.replies.get(ws, {})
            t = turnaround(x)
            rows.append([ctx.ws_label(ws), num(x.get("total", 0)), num(x.get("posted", 0)), num(x.get("in_review", 0)),
                         num(x.get("sla_breached", 0)), hours(x.get("reviewHours")), hours(x.get("postHours")),
                         f"{round(100 * t)}%" if t is not None else "–"])
        blocks.append({"type": "table", "columns": [
            col("Workspace"), col("Drafted", "right"), col("Posted", "right"), col("In review", "right"),
            col("Past deadline", "right"), col("Review time", "right"), col("Time to post", "right"),
            col("Turnaround", "right")], "rows": rows})
    blocks.append({"type": "note", "text": "Turnaround rate: of the replies whose outcome is known, the share where "
                                           "the person's next comment was more positive than the first."})
    return blocks


IDEA_LABELS = {"NEW": "New", "REVIEWING": "Reviewing", "PLANNED": "Planned", "SHIPPED": "Shipped", "DECLINED": "Declined"}


def s_growth(ctx: Ctx, audience: str) -> List[Dict]:
    totals: Dict[str, int] = {}
    for ws in ctx.ideas["byWorkspace"].values():
        totals = add(totals, ws)
    if not totals:
        return [{"type": "note", "text": "No product ideas found in comments yet. Ideas appear after videos are "
                                         "analyzed with AI."}]
    blocks = [{"type": "kpis", "items": [kpi(IDEA_LABELS[k], num(totals.get(k, 0)),
                                             tone="warn" if k == "NEW" and totals.get(k) else "info")
                                         for k in ("NEW", "REVIEWING", "PLANNED", "SHIPPED")]}]
    if ctx.ideas["top"]:
        cols = [col("Idea"), col("Status"), col("Comments", "right"), col("Likes", "right")]
        if ctx.multi:
            cols.insert(1, col("Workspace"))
        blocks.append({"type": "table", "title": "Most requested", "columns": cols, "rows": [
            [i["title"], *([ctx.ws_label(i["ws"])] if ctx.multi else []), IDEA_LABELS.get(i["status"], i["status"]),
             num(i["comments"]), num(i["likes"])] for i in ctx.ideas["top"]]})
    blocks.append({"type": "note", "text": "Ideas are current, not limited to the period: each one is a running "
                                           "theme that collects comments over time."})
    return blocks


def _engine(a: Optional[Dict]) -> str:
    if not a or a.get("mode") != "CLOUD":
        return "Local AI (Ollama)"
    name = (a.get("provider") or "cloud").title().replace("Openai", "OpenAI").replace("Deepseek", "DeepSeek")
    status = "" if (a.get("status") or "VALID") in ("VALID", "OK", "ACTIVE") else f" ({a['status'].lower()})"
    return f"{name} {a.get('model') or ''}".strip() + status


def s_operations(ctx: Ctx, audience: str) -> List[Dict]:
    rows = []
    for ws in ctx.ids:
        c, cl = ctx.ws_comments(ws), ctx.claims.get(ws, {})
        kn = ctx.ops["knowledge"].get(ws, {})
        li = ctx.ops["listings"].get(ws, {})
        checked = cl.get("byAi", 0) + cl.get("byRules", 0) + cl.get("byHuman", 0) + cl.get("seeded", 0)
        watch = ("Off" if kn.get("watchEnabled") is False else
                 f"Every {kn.get('watchHours') or 6} h, last {when(kn['latestCheck'])}" if kn.get("latestCheck") else
                 f"Every {kn.get('watchHours') or 6} h, not run yet")
        rows.append([ctx.ws_label(ws), _engine(ctx.ops["ai"].get(ws)),
                     pct(c.get("ai_read", 0), c.get("total", 0)),
                     f"{pct(cl.get('byAi', 0), checked)} AI · {pct(cl.get('byHuman', 0), checked)} person" if checked else "–",
                     num(cl.get("needsReview", 0)),
                     f"{num(kn['facts'])} ({pct(kn.get('embedded', 0), kn['facts'])} synced)" if kn.get("facts") else "None",
                     f"{li.get('OK', 0)} ok · {li.get('BLOCKED', 0) + li.get('FAILED', 0)} failing" if li else "–",
                     watch])
    blocks = [{"type": "table", "title": "AI and data per workspace", "columns": [
        col("Workspace"), col("AI engine"), col("Comments read by AI", "right"), col("Claim verdicts"),
        col("Needs a person", "right"), col("Knowledge facts", "right"), col("Amazon listings"),
        col("New-comment checks")], "rows": rows}]
    jrows = []
    for ws in ctx.ids:
        for j in sorted(ctx.ops["jobs"].get(ws, []), key=lambda x: -x["runs"]):
            done = j["ok"] + j["failed"]
            jrows.append([*([ctx.ws_label(ws)] if ctx.multi else []), JOB_LABELS.get(j["kind"], j["kind"].title()),
                          TRIGGER_LABELS.get(j["trigger"], j["trigger"] or "–"), num(j["runs"]),
                          pct(j["ok"], done), num(j["failed"]),
                          hours(j["avgSeconds"] / 3600) if j["avgSeconds"] is not None else "–"])
    if jrows:
        cols = [col("Job"), col("Started"), col("Runs", "right"), col("Success", "right"), col("Failed", "right"),
                col("Average time", "right")]
        if ctx.multi:
            cols.insert(0, col("Workspace"))
        blocks.append({"type": "table", "title": "Pipeline reliability", "columns": cols, "rows": jrows})
    blocks.append({"type": "note", "text": (
        "Accuracy guards: an AI verdict must quote the official source; numbers in the claim must match the source; "
        "with a cloud AI a second opinion re-checks each verdict; anything uncertain is marked for a person. "
        "Workspace data stays in your database; with cloud AI only the text being checked is sent to the provider.")})
    return blocks


def s_team(ctx: Ctx, audience: str) -> List[Dict]:
    rows = []
    for ws in ctx.ids:
        roles = ctx.team["roles"].get(ws, {})
        plan = ctx.team["plans"].get(ws, {})
        use = ctx.team["usage"].get(ws, {})
        status = (plan.get("status") or "").replace("_", " ").title() or "–"
        rows.append([ctx.ws_label(ws), (plan.get("plan") or "–").title(), status,
                     num(sum(roles.values())),
                     ", ".join(f"{v} {ROLE_LABELS.get(k, k).lower()}{'s' if v != 1 else ''}" for k, v in
                               sorted(roles.items(), key=lambda x: list(ROLE_LABELS).index(x[0]) if x[0] in ROLE_LABELS else 9)) or "–",
                     when(ctx.team["lastSeen"].get(ws)),
                     num(sum(use.values())) if use else "–"])
    return [{"type": "table", "columns": [
        col("Workspace"), col("Plan"), col("Subscription"), col("Members", "right"), col("Roles"),
        col("Last active"), col("Usage events", "right")], "rows": rows},
        {"type": "note", "text": "Roles are per workspace: admins manage the team and billing, approvers review "
                                 "replies, agents analyze and draft, analysts read only."}]


BUILDERS = {"summary": s_summary, "risks": s_risks, "workspaces": s_workspaces, "sentiment": s_sentiment,
            "truth": s_truth, "products": s_products, "care": s_care, "growth": s_growth,
            "operations": s_operations, "team": s_team}


def build(user: Principal, workspaces: List[Workspace], audience: str, period: str,
          sections: Optional[List[str]] = None, now: Optional[datetime] = None) -> Dict:
    audience = audience if audience in catalog.AUDIENCES else "executive"
    w = catalog.window(period, now)
    ctx = Ctx(workspaces, w)
    meta = catalog.AUDIENCES[audience]
    out_sections = []
    for sid in catalog.sections_for(audience, sections):
        out_sections.append({"id": sid, "title": catalog.SECTIONS[sid]["title"],
                             "description": catalog.SECTIONS[sid]["description"],
                             "blocks": BUILDERS[sid](ctx, audience)})
    return {
        "title": meta["title"],
        "audience": {"id": audience, "label": meta["label"], "for": meta["for"], "description": meta["description"]},
        "period": {"id": w.key, "label": w.label, "from": w.start.isoformat() if w.start else None,
                   "to": w.end.isoformat()},
        "generatedAt": (now or datetime.now(timezone.utc)).isoformat(),
        "preparedBy": {"name": user.name, "email": user.email},
        "workspaces": [{"id": x.id, "name": x.name, "role": x.role, "isDemo": x.is_demo, "plan": x.plan}
                       for x in workspaces],
        "sections": out_sections,
    }
