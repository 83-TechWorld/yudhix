# Yudhix demo: script, shots and narration

> Generated from `docs/demo/scenes.py` by `make_script.py`. Edit the scenes there, not here.
> The narrated video (`record_demo.py`) and the slide deck (`build_deck.js`) use the same scenes, so all three stay in sync.

## Before you record

- Start the app in development mode (`./yudhix.sh start`) and sign in once at http://localhost:4200 as `admin@sony.com`.
- Use the **PlayStation (Demo)** workspace. The video used throughout is [PTblI6oYfSU](https://www.youtube.com/watch?v=PTblI6oYfSU).
- Browser at 1600 × 900, light theme, zoom 100%, notifications muted.
- Speak slowly: about 150 words a minute. Each scene ends when its narration ends.

## Timeline

| # | Time | Scene | On screen |
|---|---|---|---|
| 1 | 0:00 | Yudhix | Truth-first social intelligence |
| 2 | 0:14 | How it works | Five steps, one pipeline |
| 3 | 0:27 | Analyze a video | Paste a YouTube link |
| 4 | 0:38 | Video library | Every analyzed video at a glance |
| 5 | 0:46 | Truth report | Every claim, checked against official facts |
| 6 | 1:02 | Audience impact | What the comments mean for the product |
| 7 | 1:19 | Product growth | Praise, buying signals and feature requests |
| 8 | 1:30 | Respond in the inbox | Ranked by impact, tagged by cause |
| 9 | 1:44 | Approvals | Nothing is posted without sign-off |
| 10 | 1:52 | Product ideas | Feature requests from every video, in one backlog |
| 11 | 2:03 | Knowledge base | Upload documents · synced with your AI |
| 12 | 2:19 | Bring your own AI | Local, or Claude, ChatGPT, Gemini and more |
| 13 | 2:37 | Always up to date | New comments, checked on a schedule |
| 14 | 2:49 | Yudhix | Truth first |

**Total: about 2:57**

## Scenes

### 1. Yudhix  ·  0:00

*Truth-first social intelligence*

**Title card:** Product demo · **Know which claims hurt your product** · Fact-check creator videos · trace every angry comment to its cause · answer with official facts

**Narration:**

> This is Yudhix, truth-first social intelligence. When a creator says something wrong about your product, thousands of angry comments follow. Yudhix finds which claims are false, which reactions they caused, and what to do about it.

### 2. How it works  ·  0:14

*Five steps, one pipeline*

**Title card:** How it works · **From a video link to the right reply**

1. Analyze a video
2. Fact-check every claim
3. Read the comments with AI
4. Link reactions to claims
5. Reply with official facts

**Narration:**

> It works in five steps. Analyze a video. Fact-check every claim against your own knowledge base. Read the comments with AI. Link each reaction to the claim that caused it. And reply with the official facts.

### 3. Analyze a video  ·  0:27

*Paste a YouTube link*

**Key points:** Paste any YouTube link · Transcript, details and a comment sample pulled automatically · Runs in the background with live progress

**Actions:**

1. Open `/analyze`
2. Pause 1.2 s
3. Type `https://www.youtube.com/watch?v=PTblI6oYfSU` into the link field
4. Pause 0.8 s
5. Highlight `.how-card`

**Narration:**

> Everything starts here. Paste a YouTube link, and Yudhix pulls the transcript, the video details and a sample of comments, then runs the full check in the background.

### 4. Video library  ·  0:38

*Every analyzed video at a glance*

**Key points:** Factual accuracy per video · Disputed claims flagged at a glance · Comment volume and reach

**Actions:**

1. Open `/videos`
2. Pause 1.5 s
3. Point at `a.video >> nth=0`
4. Pause 1.5 s
5. Scroll down slowly (350 px)

**Narration:**

> Every analyzed video lands in this library, with its factual accuracy, disputed claims and comment volume at a glance.

### 5. Truth report  ·  0:46

*Every claim, checked against official facts*

**Key points:** Every claim time-stamped · Verdict quotes your official source word for word · Uncertain answers go to human review

**Actions:**

1. Open `/videos/PTblI6oYfSU?tab=claims`
2. Pause 1.5 s
3. Scroll down slowly (520 px)
4. Highlight `.claim >> nth=0`
5. Highlight `.source >> nth=0`
6. Scroll down slowly (500 px)

**Narration:**

> Open a video to see its truth report. Each claim is time-stamped and gets a verdict: accurate, misleading, false, or unverified. The verdict quotes the exact sentence from your official source, and anything the AI isn't sure about is flagged for a person to review.

### 6. Audience impact  ·  1:02

*What the comments mean for the product*

**Key points:** Sentiment by comments and by reach · Misinformation vs. real product concerns · Topics and trend over time

**Actions:**

1. Open `/videos/PTblI6oYfSU?tab=impact`
2. Pause 2.0 s
3. Scroll down slowly (560 px)
4. Pause 2.5 s
5. Scroll down slowly (520 px)
6. Pause 2.5 s
7. Scroll down slowly (520 px)

**Narration:**

> The audience impact tab shows what the comments mean for the product: sentiment by comments and by reach, how much of the anger comes from misinformation versus real product concerns, which topics people talk about, and how it changes over time.

### 7. Product growth  ·  1:19

*Praise, buying signals and feature requests*

**Key points:** What people love · Buying signals and churn risk · Feature requests grouped into ideas

**Actions:**

1. Open `/videos/PTblI6oYfSU?tab=growth`
2. Pause 2.0 s
3. Scroll down slowly (560 px)
4. Pause 2.5 s
5. Scroll down slowly (600 px)

**Narration:**

> The product growth tab shows the positive side: what people love, who is ready to buy, and the feature requests hidden in the comments, grouped into product ideas.

### 8. Respond in the inbox  ·  1:30

*Ranked by impact, tagged by cause*

**Key points:** Ranked by impact, tagged by root cause · AI drafts that cite the official fact · Deep links from every chart

**Actions:**

1. Open `/inbox?video=PTblI6oYfSU`
2. Pause 1.8 s
3. Click `.list-item >> nth=1`
4. Pause 1.2 s
5. Highlight `.cause-box`
6. Point at `text=Draft with AI`
7. Pause 2.0 s

**Narration:**

> The inbox ranks comments by impact. Each one shows whether it reacts to misinformation or to a real product issue, so the team replies with the right facts. Replies can be drafted by AI, citing the official source.

### 9. Approvals  ·  1:44

*Nothing is posted without sign-off*

**Key points:** Every reply needs sign-off · Approve, reject or edit with reasons · Full audit trail

**Actions:**

1. Open `/approvals`
2. Pause 1.8 s
3. Point at `article.reply >> nth=0`
4. Pause 1.0 s
5. Highlight `article.reply >> nth=0`

**Narration:**

> Every reply goes through an approval step before it is posted, with an audit trail of who approved what.

### 10. Product ideas  ·  1:52

*Feature requests from every video, in one backlog*

**Key points:** Requests from every video, de-duplicated · New → Reviewing → Planned → Shipped · Original comments kept as evidence

**Actions:**

1. Open `/ideas`
2. Pause 2.0 s
3. Click `button.idea >> nth=0`
4. Pause 1.5 s
5. Point at `text=Planned`
6. Pause 2.5 s

**Narration:**

> Feature requests from all videos come together on the ideas page. The product team moves each idea from new, to reviewing, planned and shipped, with the original comments attached as evidence.

### 11. Knowledge base  ·  2:03

*Upload documents · synced with your AI*

**Key points:** Upload PDF, Word, text, Markdown or CSV · Split into clauses the AI can quote · Synced with your AI, nothing lost while offline

**Actions:**

1. Open `/knowledge`
2. Pause 1.5 s
3. Upload `PS5 Product Guide (demo).md`
4. Pause 3.5 s
5. Highlight `.docs`
6. Highlight `y-ai-sync`

**Narration:**

> The knowledge base holds your official facts. Upload a PDF, Word or text document, and Yudhix splits it into clauses it can quote. Your documents stay in your own database, and sync with your AI connection, including anything added while AI was off.

### 12. Bring your own AI  ·  2:19

*Local, or Claude, ChatGPT, Gemini and more*

**Key points:** Local model or Claude, ChatGPT, Gemini and more · Key verified before switching over · Automatic fallback: cloud → local → rules

**Actions:**

1. Open `/settings/ai`
2. Pause 1.8 s
3. Click `text=Cloud AI`
4. Pause 1.0 s
5. Click `text=Claude (Anthropic)`
6. Pause 0.8 s
7. Highlight `.providers`
8. Point at `#ai-key`
9. Pause 2.0 s

**Narration:**

> Each workspace chooses where AI runs: locally on your own server, or with a cloud provider like Claude, ChatGPT or Gemini, using your own key. The key is checked before anything switches over, and if a provider fails, Yudhix falls back to the local model, then to rules.

### 13. Always up to date  ·  2:37

*New comments, checked on a schedule*

**Key points:** Checks every video on a schedule · Reads only the new comments · Alerts when negativity rises or ideas appear

**Actions:**

1. Open `/settings/workspace`
2. Pause 1.5 s
3. Highlight `section:has-text('Check for new comments')`
4. Open `/videos/PTblI6oYfSU?tab=claims`
5. Pause 1.5 s
6. Point at `text=Fetch new comments`
7. Pause 2.5 s

**Narration:**

> And new comments keep coming. Yudhix checks every analyzed video on a schedule, reads only the new comments, and notifies the team when negativity rises or new ideas appear.

### 14. Yudhix  ·  2:49

*Truth first*

**Title card:** Yudhix · **Answer with facts. Learn what customers want.** · Fact-checking · audience impact · replies with approvals · product ideas · your choice of AI

**Narration:**

> Yudhix. Know which claims hurt your product, answer with facts, and learn what your customers want. Thank you for watching.

## Prompt for an AI video or voice tool

Use this if you'd rather produce the video with a tool such as Synthesia, HeyGen, Descript or ElevenLabs:

```text
Create a 4-minute product demo video for Yudhix, a B2B SaaS that fact-checks YouTube creator claims about a brand's products and traces audience comments to the claims that caused them. Tone: calm, confident, product-marketing; no hype. Voice: neutral English, about 150 words per minute. Use the screen recordings in docs/demo/out/clips in this order, one per scene, and the narration below word for word. Each scene lasts as long as its narration plus half a second. Add a lower-third caption per scene (the caption text below), simple cross-fades between scenes, no background music louder than -24 dB. 16:9, 1920x1080.

Scene 1 — Yudhix — caption: "Truth-first social intelligence"
Narration: This is Yudhix, truth-first social intelligence. When a creator says something wrong about your product, thousands of angry comments follow. Yudhix finds which claims are false, which reactions they caused, and what to do about it.

Scene 2 — How it works — caption: "Five steps, one pipeline"
Narration: It works in five steps. Analyze a video. Fact-check every claim against your own knowledge base. Read the comments with AI. Link each reaction to the claim that caused it. And reply with the official facts.

Scene 3 — Analyze a video — caption: "Paste a YouTube link"
Narration: Everything starts here. Paste a YouTube link, and Yudhix pulls the transcript, the video details and a sample of comments, then runs the full check in the background.

Scene 4 — Video library — caption: "Every analyzed video at a glance"
Narration: Every analyzed video lands in this library, with its factual accuracy, disputed claims and comment volume at a glance.

Scene 5 — Truth report — caption: "Every claim, checked against official facts"
Narration: Open a video to see its truth report. Each claim is time-stamped and gets a verdict: accurate, misleading, false, or unverified. The verdict quotes the exact sentence from your official source, and anything the AI isn't sure about is flagged for a person to review.

Scene 6 — Audience impact — caption: "What the comments mean for the product"
Narration: The audience impact tab shows what the comments mean for the product: sentiment by comments and by reach, how much of the anger comes from misinformation versus real product concerns, which topics people talk about, and how it changes over time.

Scene 7 — Product growth — caption: "Praise, buying signals and feature requests"
Narration: The product growth tab shows the positive side: what people love, who is ready to buy, and the feature requests hidden in the comments, grouped into product ideas.

Scene 8 — Respond in the inbox — caption: "Ranked by impact, tagged by cause"
Narration: The inbox ranks comments by impact. Each one shows whether it reacts to misinformation or to a real product issue, so the team replies with the right facts. Replies can be drafted by AI, citing the official source.

Scene 9 — Approvals — caption: "Nothing is posted without sign-off"
Narration: Every reply goes through an approval step before it is posted, with an audit trail of who approved what.

Scene 10 — Product ideas — caption: "Feature requests from every video, in one backlog"
Narration: Feature requests from all videos come together on the ideas page. The product team moves each idea from new, to reviewing, planned and shipped, with the original comments attached as evidence.

Scene 11 — Knowledge base — caption: "Upload documents · synced with your AI"
Narration: The knowledge base holds your official facts. Upload a PDF, Word or text document, and Yudhix splits it into clauses it can quote. Your documents stay in your own database, and sync with your AI connection, including anything added while AI was off.

Scene 12 — Bring your own AI — caption: "Local, or Claude, ChatGPT, Gemini and more"
Narration: Each workspace chooses where AI runs: locally on your own server, or with a cloud provider like Claude, ChatGPT or Gemini, using your own key. The key is checked before anything switches over, and if a provider fails, Yudhix falls back to the local model, then to rules.

Scene 13 — Always up to date — caption: "New comments, checked on a schedule"
Narration: And new comments keep coming. Yudhix checks every analyzed video on a schedule, reads only the new comments, and notifies the team when negativity rises or new ideas appear.

Scene 14 — Yudhix — caption: "Truth first"
Narration: Yudhix. Know which claims hurt your product, answer with facts, and learn what your customers want. Thank you for watching.

```

## Rebuild

```bash
cd docs/demo
python make_script.py                    # this file
../../services/yudhix-sense/.venv/bin/python prepare_demo.py   # reset demo data (dev database)
.venv/bin/python record_demo.py           # narrated video -> out/yudhix-demo.mp4 (setup: see README.md)
node build_deck.js                       # slides -> Yudhix-Demo.pptx
```
