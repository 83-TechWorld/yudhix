"""The demo, scene by scene: the single source for DEMO_SCRIPT.md, the narrated video and the slide deck.

Each scene has:
  title      shown in the script and as the slide title
  caption    short on-screen label (video lower third, slide subtitle)
  narration  what the voice says; the scene lasts as long as this takes to speak
  kind       "card" (a designed title card) or "app" (the live app)
  steps      what happens on screen, in order (see record_demo.py for the actions)
  shot       for app scenes: when to take the screenshot used in the deck (after which step index)

Edit the narration or steps here, then rebuild: python make_script.py && python record_demo.py
"""

VIDEO_ID = "PTblI6oYfSU"  # "PlayStation Explains Why it's Ending Physical Discs" in the demo workspace
SAMPLE_DOC = "sample/PS5 Product Guide (demo).md"

SCENES = [
    {
        "id": "intro", "kind": "card", "title": "Yudhix", "caption": "Truth-first social intelligence",
        "card": {"eyebrow": "Product demo", "headline": "Know which claims hurt your product",
                 "sub": "Fact-check creator videos · trace every angry comment to its cause · answer with official facts"},
        "narration": "This is Yudhix, truth-first social intelligence. When a creator says something wrong about your "
                     "product, thousands of angry comments follow. Yudhix finds which claims are false, which reactions "
                     "they caused, and what to do about it.",
    },
    {
        "id": "how", "kind": "card", "title": "How it works", "caption": "Five steps, one pipeline",
        "card": {"eyebrow": "How it works", "headline": "From a video link to the right reply",
                 "steps": ["Analyze a video", "Fact-check every claim", "Read the comments with AI",
                           "Link reactions to claims", "Reply with official facts"]},
        "narration": "It works in five steps. Analyze a video. Fact-check every claim against your own knowledge base. "
                     "Read the comments with AI. Link each reaction to the claim that caused it. And reply with the "
                     "official facts.",
    },
    {
        "id": "analyze", "points": ['Paste any YouTube link', 'Transcript, details and a comment sample pulled automatically', 'Runs in the background with live progress'], "kind": "app", "title": "Analyze a video", "caption": "Paste a YouTube link",
        "steps": [("goto", "/analyze"), ("wait", 1.2), ("type", "#url", f"https://www.youtube.com/watch?v={VIDEO_ID}"),
                  ("wait", 0.8), ("highlight", ".how-card", 3.5)],
        "shot": 3,
        "narration": "Everything starts here. Paste a YouTube link, and Yudhix pulls the transcript, the video details "
                     "and a sample of comments, then runs the full check in the background.",
    },
    {
        "id": "videos", "points": ['Factual accuracy per video', 'Disputed claims flagged at a glance', 'Comment volume and reach'], "kind": "app", "title": "Video library", "caption": "Every analyzed video at a glance",
        "steps": [("goto", "/videos"), ("wait", 1.5), ("hover", "a.video >> nth=0"), ("wait", 1.5), ("scroll", 350, 2.5)],
        "shot": 1,
        "narration": "Every analyzed video lands in this library, with its factual accuracy, disputed claims and "
                     "comment volume at a glance.",
    },
    {
        "id": "claims", "points": ['Every claim time-stamped', 'Verdict quotes your official source word for word', 'Uncertain answers go to human review'], "kind": "app", "title": "Truth report", "caption": "Every claim, checked against official facts",
        "steps": [("goto", f"/videos/{VIDEO_ID}?tab=claims"), ("wait", 1.5), ("scroll", 520, 2.5),
                  ("highlight", ".claim >> nth=0", 3.0), ("highlight", ".source >> nth=0", 3.0), ("scroll", 500, 3)],
        "shot": 3,
        "narration": "Open a video to see its truth report. Each claim is time-stamped and gets a verdict: accurate, "
                     "misleading, false, or unverified. The verdict quotes the exact sentence from your official source, "
                     "and anything the AI isn't sure about is flagged for a person to review.",
    },
    {
        "id": "impact", "points": ['Sentiment by comments and by reach', 'Misinformation vs. real product concerns', 'Topics and trend over time'], "kind": "app", "title": "Audience impact", "caption": "What the comments mean for the product",
        "steps": [("goto", f"/videos/{VIDEO_ID}?tab=impact"), ("wait", 2.0), ("scroll", 560, 3), ("wait", 2.5),
                  ("scroll", 520, 3), ("wait", 2.5), ("scroll", 520, 3)],
        "shot": 3,
        "narration": "The audience impact tab shows what the comments mean for the product: sentiment by comments and by "
                     "reach, how much of the anger comes from misinformation versus real product concerns, which topics "
                     "people talk about, and how it changes over time.",
    },
    {
        "id": "growth", "points": ['What people love', 'Buying signals and churn risk', 'Feature requests grouped into ideas'], "kind": "app", "title": "Product growth", "caption": "Praise, buying signals and feature requests",
        "steps": [("goto", f"/videos/{VIDEO_ID}?tab=growth"), ("wait", 2.0), ("scroll", 560, 3), ("wait", 2.5),
                  ("scroll", 600, 3)],
        "shot": 3,
        "narration": "The product growth tab shows the positive side: what people love, who is ready to buy, and the "
                     "feature requests hidden in the comments, grouped into product ideas.",
    },
    {
        "id": "inbox", "points": ['Ranked by impact, tagged by root cause', 'AI drafts that cite the official fact', 'Deep links from every chart'], "kind": "app", "title": "Respond in the inbox", "caption": "Ranked by impact, tagged by cause",
        "steps": [("goto", f"/inbox?video={VIDEO_ID}"), ("wait", 1.8), ("click", ".list-item >> nth=1"), ("wait", 1.2),
                  ("highlight", ".cause-box", 3.0), ("hover", "text=Draft with AI"), ("wait", 2.0)],
        "shot": 4,
        "narration": "The inbox ranks comments by impact. Each one shows whether it reacts to misinformation or to a "
                     "real product issue, so the team replies with the right facts. Replies can be drafted by AI, "
                     "citing the official source.",
    },
    {
        "id": "approvals", "points": ['Every reply needs sign-off', 'Approve, reject or edit with reasons', 'Full audit trail'], "kind": "app", "title": "Approvals", "caption": "Nothing is posted without sign-off",
        "steps": [("goto", "/approvals"), ("wait", 1.8), ("hover", "article.reply >> nth=0"), ("wait", 1.0),
                  ("highlight", "article.reply >> nth=0", 2.5)],
        "shot": 1,
        "narration": "Every reply goes through an approval step before it is posted, with an audit trail of who "
                     "approved what.",
    },
    {
        "id": "ideas", "points": ['Requests from every video, de-duplicated', 'New → Reviewing → Planned → Shipped', 'Original comments kept as evidence'], "kind": "app", "title": "Product ideas", "caption": "Feature requests from every video, in one backlog",
        "steps": [("goto", "/ideas"), ("wait", 2.0), ("click", "button.idea >> nth=0"), ("wait", 1.5),
                  ("hover", "text=Planned"), ("wait", 2.5)],
        "shot": 3,
        "narration": "Feature requests from all videos come together on the ideas page. The product team moves each "
                     "idea from new, to reviewing, planned and shipped, with the original comments attached as evidence.",
    },
    {
        "id": "knowledge", "points": ['Upload PDF, Word, text, Markdown or CSV', 'Split into clauses the AI can quote', 'Synced with your AI, nothing lost while offline'], "kind": "app", "title": "Knowledge base", "caption": "Upload documents · synced with your AI",
        "steps": [("goto", "/knowledge"), ("wait", 1.5), ("upload", "input[type=file]", SAMPLE_DOC), ("wait", 3.5),
                  ("highlight", ".docs", 3.0), ("highlight", "y-ai-sync", 3.5)],
        "shot": 4,
        "narration": "The knowledge base holds your official facts. Upload a PDF, Word or text document, and Yudhix "
                     "splits it into clauses it can quote. Your documents stay in your own database, and sync with your "
                     "AI connection, including anything added while AI was off.",
    },
    {
        "id": "ai", "points": ['Local model or Claude, ChatGPT, Gemini and more', 'Key verified before switching over', 'Automatic fallback: cloud → local → rules'], "kind": "app", "title": "Bring your own AI", "caption": "Local, or Claude, ChatGPT, Gemini and more",
        "steps": [("goto", "/settings/ai"), ("wait", 1.8), ("click", "text=Cloud AI"), ("wait", 1.0),
                  ("click", "text=Claude (Anthropic)"), ("wait", 0.8), ("highlight", ".providers", 3.0),
                  ("hover", "#ai-key"), ("wait", 2.0)],
        "shot": 6,
        "narration": "Each workspace chooses where AI runs: locally on your own server, or with a cloud provider like "
                     "Claude, ChatGPT or Gemini, using your own key. The key is checked before anything switches over, "
                     "and if a provider fails, Yudhix falls back to the local model, then to rules.",
    },
    {
        "id": "schedule", "points": ['Checks every video on a schedule', 'Reads only the new comments', 'Alerts when negativity rises or ideas appear'], "kind": "app", "title": "Always up to date", "caption": "New comments, checked on a schedule",
        "steps": [("goto", "/settings/workspace"), ("wait", 1.5), ("highlight", "section:has-text('Check for new comments')", 4.0),
                  ("goto", f"/videos/{VIDEO_ID}?tab=claims"), ("wait", 1.5), ("hover", "text=Fetch new comments"), ("wait", 2.5)],
        "shot": 3,
        "narration": "And new comments keep coming. Yudhix checks every analyzed video on a schedule, reads only the new "
                     "comments, and notifies the team when negativity rises or new ideas appear.",
    },
    {
        "id": "outro", "kind": "card", "title": "Yudhix", "caption": "Truth first",
        "card": {"eyebrow": "Yudhix", "headline": "Answer with facts. Learn what customers want.",
                 "sub": "Fact-checking · audience impact · replies with approvals · product ideas · your choice of AI"},
        "narration": "Yudhix. Know which claims hurt your product, answer with facts, and learn what your customers "
                     "want. Thank you for watching.",
    },
]
