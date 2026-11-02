"""Plans, subscriptions, usage metering, quotas and invoices.

Payments are not collected yet: invoices are issued "net 30" with status OPEN. A payment
provider (Stripe / Razorpay) plugs in later by marking invoices PAID from its webhooks.

Model
- New workspaces get a TRIAL_DAYS trial of TRIAL_PLAN. When it ends without a plan,
  usage that costs money (analyses, posting replies) is blocked until an admin picks a plan.
- Plans are billed in advance for the period. Comment overage is billed in arrears on the
  next invoice. Switching plans mid-period credits the unused part of the old plan.
- Quotas: video analyses and posted replies are hard limits; comments and AI calls are soft
  (comments over quota are billed as overage; AI calls are fair-use).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional, Tuple

from app.core import config
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.platform.notifications import notify

METRICS = {
    # metric           plan column       label                 hard limit
    "VIDEO_ANALYZED": ("video_quota", "Video analyses", True),
    "COMMENT_INGESTED": ("comment_quota", "Comments analyzed", False),
    "AI_CALL": ("llm_quota", "AI drafts & checks", False),
    "REPLY_POSTED": ("reply_quota", "Replies posted", True),
}
COMMENT_OVERAGE_PER_1000 = Decimal("2.00")   # fallback; real rates live in plan_price.overage_per_1000
DEFAULT_CURRENCY = "USD"
NET_DAYS = 30
TAX = {"IN_GST_18": (Decimal("0.18"), "GST 18%")}   # other profiles: tax not collected yet


class QuotaError(Exception):
    status_code = 402


@dataclass
class Period:
    start: datetime
    end: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def add_interval(start: datetime, interval: str) -> datetime:
    """Calendar month/year, clamped to the last day (31 Jan + 1 month = 28/29 Feb)."""
    months = 12 if interval == "YEAR" else 1
    m = start.month - 1 + months
    year, month = start.year + m // 12, m % 12 + 1
    for day in (start.day, 30, 29, 28):
        try:
            return start.replace(year=year, month=month, day=day)
        except ValueError:
            continue
    raise ValueError("unreachable")


def tax_for(tax_profile: Optional[str], subtotal: Decimal) -> Tuple[Decimal, str]:
    rate, label = TAX.get(tax_profile or "", (Decimal("0"), "Tax (not collected)"))
    return money(subtotal * rate), label


def proration_credit(price: Decimal, period: Period, at: datetime) -> Decimal:
    total = (period.end - period.start).total_seconds()
    left = max(0.0, (period.end - at).total_seconds())
    return money(price * Decimal(left / total)) if total > 0 else Decimal("0.00")


def overage_lines(usage: Dict[str, int], plan: Dict) -> List[Dict]:
    lines = []
    quota = plan["comment_quota"]
    extra = usage.get("COMMENT_INGESTED", 0) - quota if quota >= 0 else 0
    if extra > 0:
        rate = Decimal(str(plan.get("overage_per_1000") or COMMENT_OVERAGE_PER_1000))
        blocks = Decimal(extra) / Decimal(1000)
        lines.append({"description": f"Comment overage: {extra:,} over the {quota:,} included",
                      "quantity": money(blocks), "unit_price": rate, "amount": money(blocks * rate)})
    return lines


def effective_status(sub: Dict, now: Optional[datetime] = None) -> str:
    now = now or _now()
    if sub["status"] == "TRIALING" and sub.get("trial_ends_at") and sub["trial_ends_at"] <= now:
        return "TRIAL_EXPIRED"
    return sub["status"]


# ----------------------------------------------------------------------------- reads

def priced_currencies() -> List[str]:
    return [r["currency"] for r in fetch_all("SELECT DISTINCT currency FROM plan_price ORDER BY currency")]


def billing_currency(currency: Optional[str], priced: Optional[List[str]] = None) -> str:
    """The currency we can actually bill in: the requested one if plans are priced in it, else USD."""
    priced = priced if priced is not None else priced_currencies()
    code = (currency or "").upper()
    return code if code in priced else DEFAULT_CURRENCY


def workspace_currency(tenant_id: str) -> str:
    """INR for India-based workspaces; USD for every country without its own price list."""
    row = fetch_one("""SELECT c.currency FROM tenant t LEFT JOIN country_config c ON c.country_code = t.hq_country
                       WHERE t.id = %s""", (tenant_id,))
    return billing_currency(row["currency"] if row else None)


def plans(currency: Optional[str] = None) -> List[Dict]:
    code = billing_currency(currency)
    rows = fetch_all("""SELECT p.*, pp.currency AS price_currency, pp.monthly_price AS price_monthly,
                               pp.yearly_price AS price_yearly, pp.overage_per_1000
                        FROM plan p JOIN plan_price pp ON pp.plan_id = p.id AND pp.currency = %s
                        WHERE p.active ORDER BY p.sort_order, pp.monthly_price""", (code,))
    return [_plan(r) for r in rows if r["id"] in ("STARTER", "PROFESSIONAL", "ENTERPRISE")]


def _plan(r: Dict) -> Dict:
    return {"id": r["id"], "name": r["name"], "tagline": r.get("tagline"), "currency": r["price_currency"],
            "monthlyPrice": float(r["price_monthly"]), "yearlyPrice": float(r["price_yearly"]),
            "overagePer1000": float(r["overage_per_1000"]),
            "features": r.get("features") or [], "highlighted": bool(r.get("highlighted")),
            "quotas": {"videos": r["video_quota"], "comments": r["comment_quota"], "aiCalls": r["llm_quota"],
                       "replies": r["reply_quota"], "seats": r["seat_limit"]}}


def _subscription(tenant_id: str) -> Dict:
    sub = fetch_one("""SELECT s.*, p.name AS plan_name, p.video_quota, p.comment_quota, p.llm_quota, p.reply_quota,
                              p.seat_limit, pp.monthly_price, pp.yearly_price, pp.overage_per_1000
                       FROM subscription s JOIN plan p ON p.id = s.plan_id
                       JOIN plan_price pp ON pp.plan_id = s.plan_id AND pp.currency = COALESCE(s.currency, 'USD')
                       WHERE s.tenant_id = %s""", (tenant_id,))
    if not sub:
        raise QuotaError("This workspace has no subscription. Contact support.")
    return sub


def usage_in(tenant_id: str, period: Period) -> Dict[str, int]:
    rows = fetch_all("""SELECT metric_type, sum(quantity) AS n FROM usage_event
                        WHERE tenant_id = %s AND recorded_at >= %s AND recorded_at < %s GROUP BY 1""",
                     (tenant_id, period.start, period.end))
    return {r["metric_type"]: int(r["n"]) for r in rows}


def seats_used(tenant_id: str) -> int:
    row = fetch_one("""SELECT (SELECT count(*) FROM tenant_user WHERE tenant_id = %s AND active)
                            + (SELECT count(*) FROM workspace_invitation WHERE tenant_id = %s AND status = 'PENDING'
                                 AND expires_at > now()) AS n""", (tenant_id, tenant_id))
    return int(row["n"])


def summary(tenant_id: str) -> Dict:
    roll_periods(tenant_id)
    sub = _subscription(tenant_id)
    period = Period(sub["current_period_start"], sub["current_period_end"])
    used = usage_in(tenant_id, period)
    meters = []
    for metric, (col, label, hard) in METRICS.items():
        meters.append(_meter(metric, label, used.get(metric, 0), sub[col], hard))
    meters.append(_meter("SEATS", "Team members", seats_used(tenant_id), sub["seat_limit"], True))
    status = effective_status(sub)
    return {
        "plan": {"id": sub["plan_id"], "name": sub["plan_name"], "currency": sub["currency"],
                 "price": float(sub["yearly_price"] if sub["billing_interval"] == "YEAR" else sub["monthly_price"]),
                 "interval": sub["billing_interval"]},
        "status": status,
        "trialEndsAt": sub["trial_ends_at"].isoformat() if sub.get("trial_ends_at") else None,
        "periodStart": period.start.isoformat(), "periodEnd": period.end.isoformat(),
        "meters": meters,
        "upcoming": upcoming_invoice(tenant_id, sub, used) if status == "ACTIVE" else None,
        "paymentsConnected": False,
    }


def _meter(metric: str, label: str, used: int, quota: int, hard: bool) -> Dict:
    unlimited = quota is None or quota < 0
    return {"metric": metric, "label": label, "used": used, "quota": None if unlimited else quota,
            "percent": None if unlimited or quota == 0 else round(min(1.5, used / quota), 3), "hardLimit": hard}


def upcoming_invoice(tenant_id: str, sub: Dict, used: Dict[str, int]) -> Dict:
    price = money(sub["yearly_price"] if sub["billing_interval"] == "YEAR" else sub["monthly_price"])
    lines = [{"description": f"{sub['plan_name']} plan, next {sub['billing_interval'].lower()}",
              "quantity": 1, "unit_price": price, "amount": price}]
    lines += overage_lines(used, sub)
    subtotal = money(sum(l["amount"] for l in lines))
    tax, label = tax_for(_tax_profile(tenant_id), subtotal)
    return {"date": sub["current_period_end"].isoformat(), "subtotal": float(subtotal), "tax": float(tax),
            "taxLabel": label, "total": float(subtotal + tax),
            "lines": [{**l, "quantity": float(l["quantity"]), "unit_price": float(l["unit_price"]),
                       "amount": float(l["amount"])} for l in lines]}


def _tax_profile(tenant_id: str) -> Optional[str]:
    row = fetch_one("""SELECT c.tax_profile FROM tenant t LEFT JOIN country_config c ON c.country_code = t.hq_country
                       WHERE t.id = %s""", (tenant_id,))
    return row["tax_profile"] if row else None


# ----------------------------------------------------------------------------- writes

def start_trial(cur, tenant_id: str, currency: str = DEFAULT_CURRENCY, now: Optional[datetime] = None) -> None:
    now = now or _now()
    ends = now + timedelta(days=config.TRIAL_DAYS)
    cur.execute("""INSERT INTO subscription (tenant_id, plan_id, status, current_period_start, current_period_end,
                       billing_interval, trial_ends_at, currency)
                   VALUES (%s, %s, 'TRIALING', %s, %s, 'MONTH', %s, %s)""",
                (tenant_id, config.TRIAL_PLAN, now, ends, ends, billing_currency(currency)))


def check_quota(tenant_id: str, metric: str, quantity: int = 1) -> None:
    """Raise QuotaError when the action isn't allowed (trial over, or hard limit reached)."""
    sub = _subscription(tenant_id)
    status = effective_status(sub)
    if status == "TRIAL_EXPIRED":
        raise QuotaError("Your free trial has ended. An admin can pick a plan under Settings → Billing.")
    if status == "CANCELED":
        raise QuotaError("This workspace's subscription is canceled. An admin can pick a plan under Settings → Billing.")
    col, label, hard = METRICS[metric]
    quota = sub[col]
    if not hard or quota < 0:
        return
    used = usage_in(tenant_id, Period(sub["current_period_start"], sub["current_period_end"])).get(metric, 0)
    if used + quantity > quota:
        raise QuotaError(f"You've used all {quota:,} {label.lower()} in your plan this period. "
                         f"An admin can upgrade under Settings → Billing.")


def check_seat(tenant_id: str) -> None:
    sub = _subscription(tenant_id)
    if sub["seat_limit"] >= 0 and seats_used(tenant_id) + 1 > sub["seat_limit"]:
        raise QuotaError(f"Your plan includes {sub['seat_limit']} team members (including pending invites). "
                         f"Upgrade under Settings → Billing to add more.")


def record(tenant_id: str, metric: str, quantity: int = 1, key: Optional[str] = None) -> None:
    """Idempotent usage event (same key = counted once). Warns admins at 80% and 100%."""
    if quantity <= 0:
        return
    with cursor(commit=True) as cur:
        cur.execute("""INSERT INTO usage_event (id, tenant_id, metric_type, quantity, idempotency_key)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (str(uuid.uuid4()), tenant_id, metric, quantity, key or str(uuid.uuid4())))
    try:
        _threshold_alerts(tenant_id, metric)
    except Exception:
        pass


def _threshold_alerts(tenant_id: str, metric: str) -> None:
    sub = _subscription(tenant_id)
    col, label, hard = METRICS[metric]
    quota = sub[col]
    if quota is None or quota <= 0:
        return
    used = usage_in(tenant_id, Period(sub["current_period_start"], sub["current_period_end"])).get(metric, 0)
    for level in (100, 80):
        if used * 100 >= quota * level:
            kind = f"quota{level}:{metric}"[:40]
            sent = fetch_one("""SELECT 1 FROM app_notification WHERE tenant_id = %s AND kind = %s AND created_at >= %s
                                LIMIT 1""", (tenant_id, kind, sub["current_period_start"]))
            if not sent:
                notify(tenant_id, kind, f"{label}: {level}% of your plan used",
                       f"{used:,} of {quota:,} used this period." + (" New ones are blocked until you upgrade."
                                                                    if level == 100 and hard else ""),
                       "/settings/billing", roles=["admin"])
            break


def change_plan(tenant_id: str, actor_id: str, plan_id: str, interval: str) -> Dict:
    if interval not in ("MONTH", "YEAR"):
        raise ValueError("Billing interval must be MONTH or YEAR.")
    plan = fetch_one("SELECT * FROM plan WHERE id = %s AND active", (plan_id,))
    if not plan or plan_id not in ("STARTER", "PROFESSIONAL", "ENTERPRISE"):
        raise ValueError("Unknown plan.")
    old = _subscription(tenant_id)
    now = _now()
    # A paid plan keeps its currency (one invoice never mixes currencies). Otherwise bill in the
    # workspace's local currency: INR for India, USD elsewhere.
    currency = old["currency"] if old["status"] == "ACTIVE" else workspace_currency(tenant_id)
    price_row = fetch_one("SELECT * FROM plan_price WHERE plan_id = %s AND currency = %s", (plan_id, currency))
    if not price_row:
        raise ValueError(f"{plan['name']} isn't available in {currency}.")
    seats = seats_used(tenant_id)
    if plan["seat_limit"] >= 0 and seats > plan["seat_limit"]:
        raise ValueError(f"{plan['name']} includes {plan['seat_limit']} team members and you have {seats} "
                         f"(including pending invites). Remove members first.")
    if old["status"] == "ACTIVE" and old["plan_id"] == plan_id and old["billing_interval"] == interval:
        raise ValueError("You're already on this plan.")

    price = money(price_row["yearly_price"] if interval == "YEAR" else price_row["monthly_price"])
    end = add_interval(now, interval)
    lines = [{"description": f"{plan['name']} plan, {now:%d %b %Y} – {end:%d %b %Y}", "quantity": 1,
              "unit_price": price, "amount": price}]
    if old["status"] == "ACTIVE":
        old_price = money(old["yearly_price"] if old["billing_interval"] == "YEAR" else old["monthly_price"])
        credit = proration_credit(old_price, Period(old["current_period_start"], old["current_period_end"]), now)
        if credit > 0:
            lines.append({"description": f"Credit for unused time on {old['plan_name']}", "quantity": 1,
                          "unit_price": -credit, "amount": -credit})
        lines += overage_lines(usage_in(tenant_id, Period(old["current_period_start"], now)), old)

    with cursor(commit=True) as cur:
        cur.execute("""UPDATE subscription SET plan_id = %s, status = 'ACTIVE', billing_interval = %s,
                              current_period_start = %s, current_period_end = %s, trial_ends_at = NULL,
                              cancel_at_period_end = false, currency = %s, updated_at = now()
                       WHERE tenant_id = %s""", (plan_id, interval, now, end, currency, tenant_id))
        cur.execute("UPDATE tenant SET plan_code = %s, updated_at = now() WHERE id = %s", (plan_id, tenant_id))
        invoice_id = _issue_invoice(cur, tenant_id, Period(now, end), lines, currency)
        append_audit(cur, tenant_id, actor_id, "USER", "PLAN_CHANGED", "SUBSCRIPTION", tenant_id,
                     {"from": old["plan_id"], "from_status": old["status"], "to": plan_id, "interval": interval,
                      "invoice_id": invoice_id})
    notify(tenant_id, "billing", f"Plan changed to {plan['name']}", "A new invoice is available.",
           "/settings/billing", roles=["admin"], exclude=actor_id)
    return summary(tenant_id)


def _issue_invoice(cur, tenant_id: str, period: Period, lines: List[Dict], currency: str) -> str:
    subtotal = money(sum(Decimal(str(l["amount"])) for l in lines))
    if subtotal < 0:  # a downgrade credit larger than the new price carries no negative invoice
        lines.append({"description": "Credit carried forward", "quantity": 1, "unit_price": -subtotal,
                      "amount": -subtotal})
        subtotal = Decimal("0.00")
    tax, label = tax_for(_tax_profile(tenant_id), subtotal)
    invoice_id = str(uuid.uuid4())
    cur.execute("SELECT nextval('invoice_number_seq') AS n")
    row = cur.fetchone()
    number = f"YDX-{_now():%Y}-{(row['n'] if isinstance(row, dict) else row[0]):06d}"
    cur.execute("""INSERT INTO invoice (id, tenant_id, billing_period, subtotal, tax, total, currency, status, number,
                       period_start, period_end, due_at, tax_label, issued_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, %s, %s, %s, %s, now())""",
                (invoice_id, tenant_id, f"{period.start:%Y-%m}", subtotal, tax, subtotal + tax, currency, number,
                 period.start, period.end, _now() + timedelta(days=NET_DAYS), label))
    for l in lines:
        cur.execute("""INSERT INTO invoice_line (invoice_id, description, quantity, unit_price, amount)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (invoice_id, l["description"][:300], l["quantity"], l["unit_price"], l["amount"]))
    return invoice_id


def roll_periods(tenant_id: str) -> None:
    """Close any finished billing periods: advance the period and invoice the next one in advance,
    plus overage from the period that just ended."""
    for _ in range(24):  # safety bound
        sub = _subscription(tenant_id)
        if sub["status"] != "ACTIVE" or sub["current_period_end"] > _now():
            return
        ended = Period(sub["current_period_start"], sub["current_period_end"])
        nxt = Period(ended.end, add_interval(ended.end, sub["billing_interval"]))
        price = money(sub["yearly_price"] if sub["billing_interval"] == "YEAR" else sub["monthly_price"])
        lines = [{"description": f"{sub['plan_name']} plan, {nxt.start:%d %b %Y} – {nxt.end:%d %b %Y}",
                  "quantity": 1, "unit_price": price, "amount": price}]
        lines += overage_lines(usage_in(tenant_id, ended), sub)
        with cursor(commit=True) as cur:
            if sub["cancel_at_period_end"]:
                cur.execute("UPDATE subscription SET status = 'CANCELED', updated_at = now() WHERE tenant_id = %s",
                            (tenant_id,))
                return
            cur.execute("""UPDATE subscription SET current_period_start = %s, current_period_end = %s, updated_at = now()
                           WHERE tenant_id = %s""", (nxt.start, nxt.end, tenant_id))
            _issue_invoice(cur, tenant_id, nxt, lines, sub["currency"])


def invoices(tenant_id: str) -> List[Dict]:
    roll_periods(tenant_id)
    rows = fetch_all("""SELECT * FROM invoice WHERE tenant_id = %s ORDER BY issued_at DESC""", (tenant_id,))
    return [_invoice(r) for r in rows]


def invoice(tenant_id: str, invoice_id: str) -> Optional[Dict]:
    r = fetch_one("SELECT * FROM invoice WHERE tenant_id = %s AND id = %s", (tenant_id, invoice_id))
    if not r:
        return None
    out = _invoice(r)
    out["lines"] = [{"description": l["description"], "quantity": float(l["quantity"]),
                     "unitPrice": float(l["unit_price"]), "amount": float(l["amount"])}
                    for l in fetch_all("SELECT * FROM invoice_line WHERE invoice_id = %s ORDER BY id", (invoice_id,))]
    t = fetch_one("""SELECT t.name, t.hq_country, c.country_name FROM tenant t
                     LEFT JOIN country_config c ON c.country_code = t.hq_country WHERE t.id = %s""", (tenant_id,))
    out["billTo"] = {"name": t["name"], "country": t["country_name"] or t["hq_country"]}
    return out


def _invoice(r: Dict) -> Dict:
    iso = lambda v: v.isoformat() if v else None  # noqa: E731
    return {"id": str(r["id"]), "number": r.get("number") or str(r["id"])[:8].upper(), "status": r["status"],
            "currency": r["currency"], "subtotal": float(r["subtotal"]), "tax": float(r["tax"]),
            "taxLabel": r.get("tax_label") or "Tax", "total": float(r["total"]), "issuedAt": iso(r["issued_at"]),
            "dueAt": iso(r.get("due_at")), "periodStart": iso(r.get("period_start")),
            "periodEnd": iso(r.get("period_end")), "paidAt": iso(r.get("paid_at"))}
