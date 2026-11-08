# Demo kit

Everything for presenting Yudhix, built from one scene list (`scenes.py`) so the script, the video and the slides always match.

| File | What it is |
|---|---|
| `DEMO_SCRIPT.md` | The demo, scene by scene: timeline, what to click, key points and the narration word for word. Also a ready-made prompt for AI video tools (Synthesia, HeyGen, Descript, ElevenLabs). |
| `Yudhix-Demo.pptx` | 16-slide deck with real screenshots. The narration is in the speaker notes. |
| `out/yudhix-demo.mp4` | The narrated video (about 3 minutes, 1080p) with a subtitle track; `out/yudhix-demo.srt` has the subtitles. Not committed; rebuild it below. |
| `scenes.py` | The single source: scene titles, captions, key points, narration and the clicks the recorder performs. |

## Rebuild after changing the app or the narration

Needs the development stack running (`./yudhix.sh start`, app on http://localhost:4200), macOS (for the `say` voice), ffmpeg and Node.

```bash
cd docs/demo
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium ffmpeg   # once
npm install                                                              # once (pptxgenjs)

../../services/yudhix-sense/.venv/bin/python prepare_demo.py   # reset demo data: sample document, replies awaiting approval
.venv/bin/python record_demo.py                                # voice + screen recording -> out/yudhix-demo.mp4 (+ screenshots)
python3 make_script.py --measured                              # DEMO_SCRIPT.md with the real timings
node build_deck.js                                             # Yudhix-Demo.pptx from the new screenshots
```

Re-record only some scenes: `.venv/bin/python record_demo.py claims inbox` (the video is re-joined from all clips).

Voice and pace: `DEMO_VOICE=Rishi` (Indian English), `DEMO_VOICE=Daniel` (British) or the default `Samantha` (US); `DEMO_RATE=165` speaks slower. List voices with `say -v '?'`.
For a studio-quality voice, generate audio per scene in ElevenLabs from the narration in `DEMO_SCRIPT.md`, save it as `out/audio/<scene id>.aiff`, and adapt `speak()` in `record_demo.py` to use those files.
