"""Drafts brand-safe text: replies to commenters and clarification notes to creators.

Every draft is a starting point. Nothing is sent without a human approving it.
"""
from typing import Dict, List, Optional

from app.core import llm


def creator_note(channel_title: str, video_title: str, claims: List[Dict], brand_name: str) -> Dict[str, str]:
    """A polite note asking the creator to add context, citing official sources."""
    subject = f"Clarification on a few points in \"{_trim(video_title, 70)}\""
    bullets = "\n".join(
        f"- At {c.get('timestamp_start')}: \"{_trim(c.get('creator_quote', ''), 140)}\"\n"
        f"  Official position ({c.get('document_title') or c.get('official_citation') or 'brand documentation'}"
        f"{', ' + c['clause_ref'] if c.get('clause_ref') else ''}): {_trim(c.get('official_statement') or c.get('fact_check_analysis', ''), 260)}"
        for c in claims)

    prompt = f"""Write a short, warm, respectful email from {brand_name}'s communications team to the YouTube
creator "{channel_title}" about their video "{video_title}". Thank them for covering the product. Politely point out
the points below where official documentation says something different, and ask whether they would consider a
pinned comment or an on-screen note. Do not accuse, threaten or mention legal action. Under 220 words. Plain text only.

Points:
{bullets}
"""
    body = llm.generate_text(prompt)
    if not body:
        body = (
            f"Hi {channel_title} team,\n\n"
            f"Thank you for covering our products in \"{video_title}\". We appreciate the attention you bring "
            f"to what matters to players.\n\n"
            f"We noticed a few points where our official documentation says something different, and we wanted "
            f"to share the sources in case they're useful:\n\n{bullets}\n\n"
            f"Would you consider adding a pinned comment or an on-screen note with this context? Happy to provide "
            f"more detail or connect you with our product team.\n\n"
            f"Thanks again,\n{brand_name} Communications"
        )
    return {"subject": subject, "body": body}


def reply_draft(comment_text: str, sentiment: str, claim: Optional[Dict], brand_name: str,
                fallback: Optional[str] = None) -> str:
    """Draft a public reply. If the comment reacts to a misleading claim, cite the official fact."""
    if claim and claim.get("verdict") in ("MISLEADING", "FALSE", "UNVERIFIED_SPECULATION"):
        fact = claim.get("official_statement") or claim.get("fact_check_analysis") or ""
        source = claim.get("document_title") or claim.get("official_citation") or "our official documentation"
        prompt = f"""Write a brief, friendly public reply (max 60 words) from {brand_name}'s support team to this
YouTube comment. The commenter is reacting to a claim that our official documentation contradicts. Acknowledge their
concern, state the official fact simply, and mention the source by name. No marketing language, no blame.

Comment: "{comment_text}"
Official fact: "{fact}"
Source: "{source}"
"""
        text = llm.generate_text(prompt)
        if text:
            return text.strip().strip('"')
        return (f"We completely understand the concern. To clarify: {_trim(fact, 200)} "
                f"(Source: {source}). Happy to answer any questions.")

    if fallback:
        return fallback
    if (sentiment or "").upper() == "NEGATIVE":
        return ("We're sorry to hear this. Please share a few details with our support team so we can look "
                "into it and make it right.")
    if (sentiment or "").upper() == "POSITIVE":
        return "Thank you so much for the kind words. We're really glad you're enjoying it!"
    return "Thanks for sharing your thoughts. We're listening, and we pass feedback like this to our product team."


def _trim(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"
