"""What a report can contain: audiences (who it is for), sections and periods.

An audience is a preset: a title, a one-line purpose and the sections it starts with. People can
add or remove sections, so every section works on its own.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

SECTIONS: Dict[str, Dict[str, str]] = {
    "summary": {"title": "Executive summary",
                "description": "Headline numbers across the selected workspaces, with what changed and why it matters."},
    "workspaces": {"title": "Workspace comparison",
                   "description": "Each workspace side by side: audience mood, claim accuracy, response and ideas."},
    "sentiment": {"title": "Audience sentiment",
                  "description": "How the mood of comments and reviews moved over the period, and by channel."},
    "truth": {"title": "Creator claims and misinformation",
              "description": "What creators said about your products, how much of it was wrong, and the videos that matter most."},
    "products": {"title": "Products across channels",
                 "description": "Each product's YouTube comments and Amazon reviews, with ratings."},
    "care": {"title": "Customer response",
             "description": "Replies drafted, reviewed and posted, time to respond, and whether people changed their minds."},
    "growth": {"title": "Product ideas from customers",
               "description": "Requests and suggestions found in comments, and where each one stands."},
    "operations": {"title": "Platform and AI operations",
                   "description": "AI engine per workspace, how comments and claims were read, job reliability, data freshness."},
    "team": {"title": "Team, plan and usage",
             "description": "Who has access, the plan each workspace is on, and usage in the period."},
    "risks": {"title": "Risks and recommended actions",
              "description": "What needs attention, ranked, with a suggested next step for each."},
}

AUDIENCES: Dict[str, Dict] = {
    "executive": {
        "label": "Executive", "for": "CEO, leadership, board",
        "title": "Executive brand report",
        "description": "Brand health, misinformation exposure, product perception and how well the team responds.",
        "sections": ["summary", "risks", "workspaces", "sentiment", "truth", "products", "care"],
    },
    "technology": {
        "label": "Technology", "for": "CTO, engineering, IT",
        "title": "Technology and operations report",
        "description": "AI engines and their accuracy guards, pipeline reliability, data freshness, access and usage.",
        "sections": ["summary", "operations", "risks", "team", "workspaces"],
    },
    "product": {
        "label": "Product", "for": "CPO, product managers",
        "title": "Product insight report",
        "description": "What customers say about each product on every channel, the ideas they raise and claims that shape opinion.",
        "sections": ["summary", "products", "growth", "sentiment", "truth"],
    },
    "care": {
        "label": "Customer care", "for": "Head of support, community, social",
        "title": "Customer response report",
        "description": "Response volume, review speed, SLA and how many replies turned a negative opinion around.",
        "sections": ["summary", "care", "sentiment", "workspaces", "risks"],
    },
}

PERIODS = {
    "30d": {"label": "Last 30 days", "days": 30, "grain": "day"},
    "90d": {"label": "Last 90 days", "days": 90, "grain": "week"},
    "12m": {"label": "Last 12 months", "days": 365, "grain": "month"},
    "all": {"label": "All time", "days": None, "grain": "month"},
}
DEFAULT_PERIOD = "90d"


@dataclass(frozen=True)
class Window:
    key: str
    label: str
    start: Optional[datetime]   # None = no lower bound
    end: datetime
    grain: str

    @property
    def previous(self) -> Optional["Window"]:
        """The same length of time just before this one (for "vs previous period")."""
        if self.start is None:
            return None
        return Window(self.key, "previous period", self.start - (self.end - self.start), self.start, self.grain)

    @property
    def lower(self) -> datetime:
        return self.start or datetime(1970, 1, 1, tzinfo=timezone.utc)


def window(key: str, now: Optional[datetime] = None) -> Window:
    p = PERIODS.get(key) or PERIODS[DEFAULT_PERIOD]
    key = key if key in PERIODS else DEFAULT_PERIOD
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(days=p["days"]) if p["days"] else None
    return Window(key, p["label"], start, end, p["grain"])


def sections_for(audience: str, requested: Optional[List[str]]) -> List[str]:
    """Requested sections in the catalog's order, or the audience's defaults."""
    if requested:
        chosen = [s for s in requested if s in SECTIONS]
        if chosen:
            base = AUDIENCES.get(audience, AUDIENCES["executive"])["sections"]
            # keep the audience's order for its own sections, then any extras in catalog order
            ordered = [s for s in base if s in chosen] + [s for s in SECTIONS if s in chosen and s not in base]
            return ordered
    return list(AUDIENCES.get(audience, AUDIENCES["executive"])["sections"])


def options() -> Dict:
    return {
        "audiences": [{"id": k, "label": v["label"], "for": v["for"], "title": v["title"],
                       "description": v["description"], "sections": v["sections"]} for k, v in AUDIENCES.items()],
        "sections": [{"id": k, **v} for k, v in SECTIONS.items()],
        "periods": [{"id": k, "label": v["label"]} for k, v in PERIODS.items()],
        "defaultPeriod": DEFAULT_PERIOD,
    }
