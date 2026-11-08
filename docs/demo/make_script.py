"""Writes DEMO_SCRIPT.md from scenes.py, so the script, the video and the deck always match.

    python make_script.py            # word-count timing (about 150 words per minute)
    python make_script.py --measured # exact timing from out/audio/*.aiff (after record_demo.py)
"""
import subprocess
import sys
from pathlib import Path

from scenes import SCENES, VIDEO_ID

HERE = Path(__file__).parent
WPM = 150


def seconds(scene) -> float:
    clips = HERE / "out" / "clips.json"
    if "--measured" in sys.argv and clips.exists():
        import json
        meta = json.loads(clips.read_text()).get(scene["id"])
        if meta:
            return meta["length"]
    audio = HERE / "out" / "audio" / f"{scene['id']}.aiff"
    if "--measured" in sys.argv and audio.exists():
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
                             capture_output=True, text=True).stdout.strip()
        return float(out) + 0.6
    return len(scene["narration"].split()) / WPM * 60 + 0.8


def ts(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def describe(step) -> str:
    kind, *args = step
    return {
        "goto": lambda: f"Open `{args[0]}`",
        "wait": lambda: f"Pause {args[0]} s",
        "type": lambda: f"Type `{args[1]}` into the link field",
        "click": lambda: f"Click `{args[0]}`",
        "hover": lambda: f"Point at `{args[0]}`",
        "scroll": lambda: f"Scroll down slowly ({args[0]} px)",
        "highlight": lambda: f"Highlight `{args[0]}`",
        "upload": lambda: f"Upload `{Path(args[1]).name}`",
    }.get(kind, lambda: kind)()


def main() -> None:
    lines = [
        "# Yudhix demo: script, shots and narration",
        "",
        "> Generated from `docs/demo/scenes.py` by `make_script.py`. Edit the scenes there, not here.",
        "> The narrated video (`record_demo.py`) and the slide deck (`build_deck.js`) use the same scenes, so all three stay in sync.",
        "",
        "## Before you record",
        "",
        "- Start the app in development mode (`./yudhix.sh start`) and sign in once at http://localhost:4200 as `admin@sony.com`.",
        "- Use the **PlayStation (Demo)** workspace. The video used throughout is "
        f"[{VIDEO_ID}](https://www.youtube.com/watch?v={VIDEO_ID}).",
        "- Browser at 1600 × 900, light theme, zoom 100%, notifications muted.",
        "- Speak slowly: about 150 words a minute. Each scene ends when its narration ends.",
        "",
        "## Timeline",
        "",
        "| # | Time | Scene | On screen |",
        "|---|---|---|---|",
    ]
    t = 0.0
    starts = []
    for i, s in enumerate(SCENES, start=1):
        starts.append(t)
        lines.append(f"| {i} | {ts(t)} | {s['title']} | {s['caption']} |")
        t += seconds(s)
    lines += ["", f"**Total: about {ts(t)}**", "", "## Scenes", ""]
    for i, (s, start) in enumerate(zip(SCENES, starts), start=1):
        lines += [f"### {i}. {s['title']}  ·  {ts(start)}", "", f"*{s['caption']}*", ""]
        if s["kind"] == "card":
            card = s["card"]
            lines.append(f"**Title card:** {card['eyebrow']} · **{card['headline']}**"
                         + (f" · {card['sub']}" if card.get("sub") else ""))
            if card.get("steps"):
                lines += [""] + [f"{n}. {x}" for n, x in enumerate(card["steps"], start=1)]
        else:
            if s.get("points"):
                lines += ["**Key points:** " + " · ".join(s["points"]), ""]
            lines.append("**Actions:**")
            lines += [""] + [f"{n}. {describe(st)}" for n, st in enumerate(s["steps"], start=1)]
        lines += ["", "**Narration:**", "", f"> {s['narration']}", ""]
    lines += [
        "## Prompt for an AI video or voice tool",
        "",
        "Use this if you'd rather produce the video with a tool such as Synthesia, HeyGen, Descript or ElevenLabs:",
        "",
        "```text",
        "Create a 4-minute product demo video for Yudhix, a B2B SaaS that fact-checks YouTube creator claims about a "
        "brand's products and traces audience comments to the claims that caused them. Tone: calm, confident, "
        "product-marketing; no hype. Voice: neutral English, about 150 words per minute. Use the screen recordings in "
        "docs/demo/out/clips in this order, one per scene, and the narration below word for word. Each scene lasts as "
        "long as its narration plus half a second. Add a lower-third caption per scene (the caption text below), simple "
        "cross-fades between scenes, no background music louder than -24 dB. 16:9, 1920x1080.",
        "",
    ]
    for i, s in enumerate(SCENES, start=1):
        lines.append(f"Scene {i} — {s['title']} — caption: \"{s['caption']}\"")
        lines.append(f"Narration: {s['narration']}")
        lines.append("")
    lines += ["```", "", "## Rebuild", "", "```bash", "cd docs/demo",
              "python make_script.py                    # this file",
              "../../services/yudhix-sense/.venv/bin/python prepare_demo.py   # reset demo data (dev database)",
              ".venv/bin/python record_demo.py           # narrated video -> out/yudhix-demo.mp4 (setup: see README.md)",
              "node build_deck.js                       # slides -> Yudhix-Demo.pptx", "```", ""]
    (HERE / "DEMO_SCRIPT.md").write_text("\n".join(lines))
    print(f"Wrote DEMO_SCRIPT.md ({len(SCENES)} scenes, about {ts(t)})")


if __name__ == "__main__":
    main()
