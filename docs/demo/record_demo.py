"""Record the narrated demo video from the running app.

For every scene in scenes.py it:
  1. speaks the narration with the macOS voice (`say`) and measures how long it takes,
  2. drives the real app in a browser (Playwright) with a visible cursor, highlights and a caption,
     stretching the scene to the length of its narration,
  3. joins picture and voice per scene, then all scenes into one video with a subtitle track.
It also saves one screenshot per app scene for the slide deck.

Run (development stack on :4200, demo workspace):
    ../../services/yudhix-sense/.venv/bin/python prepare_demo.py
    <python with playwright> record_demo.py                 # all scenes
    <python with playwright> record_demo.py claims inbox    # only some scenes (others reuse earlier clips)

Settings (environment): DEMO_URL (http://localhost:4200), DEMO_USER / DEMO_PASSWORD, DEMO_VOICE (Samantha),
DEMO_RATE (172 words per minute).
Output: out/yudhix-demo.mp4, out/yudhix-demo.srt, out/shots/*.png
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from scenes import SCENES

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CLIPS, AUDIO, SHOTS, RAW = OUT / "clips", OUT / "audio", OUT / "shots", OUT / "raw"
BASE = os.getenv("DEMO_URL", "http://localhost:4200")
USER = os.getenv("DEMO_USER", "admin@sony.com")
PASSWORD = os.getenv("DEMO_PASSWORD", "sony_admin_2026")
WORKSPACE = os.getenv("DEMO_WORKSPACE", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
VOICE = os.getenv("DEMO_VOICE", "Samantha")
RATE = os.getenv("DEMO_RATE", "172")
VIEW = {"width": 1600, "height": 900}
LEAD_IN, TAIL = 0.35, 0.6  # silence before and after each scene's narration
FADE = 0.3

# A visible cursor with a click ripple, a highlight ring, and a caption: Playwright videos show none of these.
OVERLAY_JS = r"""
(() => {
  if (window.__demo) return; window.__demo = true;
  const css = `
    #demo-cursor{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;
      transform:translate(800px,450px);transition:transform .05s linear;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
    .demo-ripple{position:fixed;z-index:2147483646;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;
      border:3px solid #6366f1;pointer-events:none;animation:demo-r .55s ease-out forwards}
    @keyframes demo-r{to{transform:scale(3.4);opacity:0}}
    #demo-ring{position:fixed;z-index:2147483640;pointer-events:none;border-radius:14px;border:3px solid #6366f1;
      box-shadow:0 0 0 6px rgba(99,102,241,.22),0 0 0 9999px rgba(15,16,32,.28);transition:all .35s ease;opacity:0}
    #demo-caption{position:fixed;left:32px;bottom:28px;z-index:2147483645;pointer-events:none;display:flex;gap:12px;
      align-items:center;padding:12px 18px 12px 12px;border-radius:14px;background:rgba(15,16,32,.88);color:#fff;
      font:500 15px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.25);
      opacity:0;transform:translateY(8px);transition:all .45s ease}
    #demo-caption b{display:block;font-size:17px;font-weight:650}
    #demo-caption i{font-style:normal;opacity:.75}
    #demo-caption .n{width:34px;height:34px;border-radius:10px;background:#6366f1;display:grid;place-items:center;
      font-weight:700;font-size:15px}`;
  const add = () => {
    if (document.getElementById('demo-cursor')) return;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    const c = document.createElement('div'); c.id = 'demo-cursor';
    c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2l15 11-6.5 1.2L9 21z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.body.appendChild(c);
    const r = document.createElement('div'); r.id = 'demo-ring'; document.body.appendChild(r);
    if (window.__caption) {
      const cap = document.createElement('div'); cap.id = 'demo-caption';
      cap.innerHTML = `<span class="n">${window.__caption.n}</span><span><b>${window.__caption.title}</b><i>${window.__caption.text}</i></span>`;
      document.body.appendChild(cap);
      setTimeout(() => { cap.style.opacity = 1; cap.style.transform = 'none'; }, 350);
    }
  };
  document.addEventListener('mousemove', e => {
    const c = document.getElementById('demo-cursor'); if (c) c.style.transform = `translate(${e.clientX}px,${e.clientY}px)`;
  }, true);
  document.addEventListener('mousedown', e => {
    const d = document.createElement('div'); d.className = 'demo-ripple';
    d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; document.body.appendChild(d);
    setTimeout(() => d.remove(), 600);
  }, true);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
  window.__demoRing = (sel, on) => {
    const ring = document.getElementById('demo-ring'); if (!ring) return false;
    if (!on) { ring.style.opacity = 0; return true; }
    let el = null;
    for (const s of sel.split(',')) { try { el = document.querySelector(s.trim()); } catch (e) {} if (el) break; }
    if (!el) return false;
    const b = el.getBoundingClientRect(), p = 8;
    Object.assign(ring.style, {left: (b.left - p) + 'px', top: (b.top - p) + 'px', width: (b.width + 2*p) + 'px',
                                height: (b.height + 2*p) + 'px', opacity: 1});
    return true;
  };
  window.__demoScroll = (dy) => {
    const cands = [document.scrollingElement, ...document.querySelectorAll('main, .main, .content, [class*=scroll]')];
    const el = cands.find(e => e && e.scrollHeight > e.clientHeight + 10 &&
      (e === document.scrollingElement || ['auto','scroll'].includes(getComputedStyle(e).overflowY)));
    (el || document.scrollingElement).scrollBy({top: dy, behavior: 'auto'});
  };
  window.__demoCaption = (show) => { const c = document.getElementById('demo-caption'); if (c) c.style.display = show ? '' : 'none'; };
})();
"""


def card_html(scene: dict, n: int) -> str:
    c = scene["card"]
    steps = "".join(f'<li><span>{i}</span>{s}</li>' for i, s in enumerate(c.get("steps", []), start=1))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
      *{{box-sizing:border-box;margin:0}}
      html{{background:#0f1020;height:100%}}
      body{{width:100vw;min-height:100vh;height:100%;overflow:hidden;background-color:#0f1020;color:#fff;position:relative;
        font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;
        background-image:radial-gradient(900px 600px at 85% 15%,rgba(99,102,241,.38),transparent 60%),
                         radial-gradient(700px 500px at 5% 100%,rgba(16,185,129,.16),transparent 60%)}}
      .wrap{{position:absolute;inset:0;padding:110px 120px;display:flex;flex-direction:column;justify-content:center;gap:28px;
        animation:in .9s cubic-bezier(.2,.7,.2,1) both}}
      @keyframes in{{from{{opacity:0;transform:translateY(24px)}}}}
      .logo{{display:flex;align-items:center;gap:14px;font-size:26px;font-weight:700;position:absolute;top:70px;left:120px}}
      .logo i{{width:46px;height:46px;border-radius:13px;background:#6366f1;display:grid;place-items:center;font-style:normal;font-size:24px}}
      .eyebrow{{text-transform:uppercase;letter-spacing:.18em;font-size:18px;color:#a5b4fc;font-weight:600}}
      h1{{font-size:76px;line-height:1.05;font-weight:750;letter-spacing:-.025em;max-width:1200px}}
      p{{font-size:26px;line-height:1.45;color:#c7c9e0;max-width:1150px}}
      ol{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(5,1fr);gap:18px;margin-top:20px}}
      li{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:26px 22px;
        font-size:23px;line-height:1.3;font-weight:600;animation:in .7s both}}
      {"".join(f"li:nth-child({i}){{animation-delay:{0.35 + i * 0.35:.2f}s}}" for i in range(1, 6))}
      li span{{display:grid;place-items:center;width:44px;height:44px;border-radius:12px;background:#6366f1;margin-bottom:18px;font-size:20px}}
    </style></head><body><div class="logo"><i>Y</i>Yudhix</div><div class="wrap">
      <div class="eyebrow">{c['eyebrow']}</div><h1>{c['headline']}</h1>
      {f"<p>{c['sub']}</p>" if c.get('sub') else ""}{f"<ol>{steps}</ol>" if steps else ""}
    </div></body></html>"""


# ----------------------------------------------------------------------------- voice

def speak(scene: dict) -> float:
    AUDIO.mkdir(parents=True, exist_ok=True)
    path = AUDIO / f"{scene['id']}.aiff"
    subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", str(path), scene["narration"]], check=True)
    return duration(path)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ----------------------------------------------------------------------------- browser

def login(browser) -> Path:
    state = OUT / "auth.json"
    ctx = browser.new_context(viewport=VIEW)
    page = ctx.new_page()
    page.goto(f"{BASE}/analyze")
    page.wait_for_selector("#username", timeout=30000)
    page.fill("#username", USER)
    page.fill("#password", PASSWORD)
    page.click("#kc-login")
    page.wait_for_url("**/analyze**", timeout=30000)
    page.evaluate(f"localStorage.setItem('yudhix.workspace', '{WORKSPACE}'); localStorage.setItem('yudhix.theme', 'light')")
    ctx.storage_state(path=str(state))
    ctx.close()
    return state


class Scene:
    def __init__(self, page, n: int, scene: dict):
        self.page, self.n, self.scene = page, n, scene
        self.mouse = (VIEW["width"] / 2, VIEW["height"] / 2)

    def goto(self, path: str) -> None:
        self.page.goto(f"{BASE}{path}")
        try:
            self.page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        self.page.wait_for_timeout(500)
        self.page.mouse.move(*self.mouse)

    def move_to(self, selector: str) -> None:
        el = self.page.locator(selector).first
        el.scroll_into_view_if_needed(timeout=5000)
        box = el.bounding_box()
        if not box:
            return
        target = (box["x"] + min(box["width"] / 2, 120), box["y"] + box["height"] / 2)
        self.page.mouse.move(*target, steps=28)
        self.mouse = target

    def run(self, step) -> None:
        kind, *a = step
        p = self.page
        if kind == "goto":
            self.goto(a[0])
        elif kind == "wait":
            p.wait_for_timeout(a[0] * 1000)
        elif kind == "hover":
            self.move_to(a[0])
        elif kind == "click":
            self.move_to(a[0])
            p.wait_for_timeout(250)
            p.mouse.down()
            p.mouse.up()
            p.wait_for_timeout(400)
        elif kind == "type":
            self.move_to(a[0])
            p.click(a[0])
            p.keyboard.type(a[1], delay=32)
        elif kind == "scroll":
            px, secs = a
            frames = max(1, int(secs * 30))
            for _ in range(frames):
                p.evaluate(f"window.__demoScroll({px / frames})")
                p.wait_for_timeout(1000 / 30)
        elif kind == "highlight":
            sel, secs = a
            try:
                p.locator(sel.split(",")[0].strip()).first.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            p.wait_for_timeout(300)
            p.evaluate("([s]) => window.__demoRing(s, true)", [sel])
            p.wait_for_timeout(secs * 1000)
            p.evaluate("window.__demoRing('', false)")
            p.wait_for_timeout(250)
        elif kind == "upload":
            p.set_input_files(a[0], str(HERE / a[1]))
        else:
            raise ValueError(f"Unknown step {kind}")

    def screenshot(self) -> None:
        SHOTS.mkdir(parents=True, exist_ok=True)
        self.page.evaluate("window.__demoCaption(false)")
        self.page.screenshot(path=str(SHOTS / f"{self.scene['id']}.png"))
        self.page.evaluate("window.__demoCaption(true)")


def record(browser, state: Path, n: int, scene: dict, voice_len: float) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    tmp = RAW / scene["id"]
    shutil.rmtree(tmp, ignore_errors=True)
    ctx = browser.new_context(viewport=VIEW, record_video_dir=str(tmp), record_video_size=VIEW, storage_state=str(state))
    caption = {"n": n, "title": scene["title"], "text": scene["caption"]}
    ctx.add_init_script(f"window.__caption = {json.dumps(caption)};" if scene["kind"] == "app" else "")
    if scene["kind"] == "app":  # title cards need no cursor
        ctx.add_init_script(OVERLAY_JS)
    t0 = time.monotonic()
    page = ctx.new_page()
    s = Scene(page, n, scene)
    steps = list(scene.get("steps", []))
    if scene["kind"] == "card":
        card = RAW / f"{scene['id']}.html"  # loaded as a file: set_content leaves a grey band in the recording
        card.write_text(card_html(scene, n))
        page.goto(card.as_uri())
        page.wait_for_timeout(150)
    else:
        first = steps.pop(0)
        assert first[0] == "goto", f"{scene['id']}: the first step must be goto"
        s.goto(first[1])
    offset = time.monotonic() - t0
    start = time.monotonic()
    shot_after = scene.get("shot")  # counts the opening goto as step 1
    if scene["kind"] == "app" and shot_after == 1:
        page.wait_for_timeout(800)
        s.screenshot()
    for i, step in enumerate(steps, start=1):
        try:
            s.run(step)
        except Exception as e:
            print(f"   ! {scene['id']} step {step[0]} {step[1:2]}: {type(e).__name__}: {str(e).splitlines()[0][:120]}")
        if shot_after is not None and i == shot_after - 1:
            s.screenshot()
    if scene["kind"] == "app" and not (SHOTS / f"{scene['id']}.png").exists():
        s.screenshot()
    if scene["kind"] == "card":
        page.wait_for_timeout(2600)  # let the entrance animation finish before the deck screenshot
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{scene['id']}.png"))
    target = LEAD_IN + voice_len + TAIL
    spent = time.monotonic() - start
    if spent < target:
        page.wait_for_timeout((target - spent) * 1000)
    length = max(target, time.monotonic() - start)
    video = page.video.path()
    ctx.close()
    return {"video": video, "offset": offset, "length": length}


# ----------------------------------------------------------------------------- video

def encode(scene: dict, rec: dict) -> Path:
    CLIPS.mkdir(parents=True, exist_ok=True)
    out = CLIPS / f"{scene['id']}.mp4"
    L = rec["length"]
    delay = int(LEAD_IN * 1000)
    vf = (f"[0:v]tpad=stop_mode=clone:stop_duration=10,fps=30,scale=1920:1080:flags=lanczos,format=yuv420p,"
          f"fade=t=in:st=0:d={FADE},fade=t=out:st={L - FADE:.3f}:d={FADE}[v];"
          f"[1:a]adelay={delay}|{delay},apad,aformat=sample_rates=48000:channel_layouts=stereo[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{rec['offset']:.3f}", "-i", str(rec["video"]),
                    "-i", str(AUDIO / f"{scene['id']}.aiff"), "-filter_complex", vf, "-map", "[v]", "-map", "[a]",
                    "-t", f"{L:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "160k",
                    str(out)], check=True)
    return out


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def subtitles(timeline) -> Path:
    """One cue per sentence, timed by its share of the scene's spoken length."""
    cues, n = [], 1
    for scene, start, voice_len in timeline:
        sentences = [s for s in re.split(r"(?<=[.!?:])\s+", scene["narration"]) if s]
        total = sum(len(s) for s in sentences) or 1
        t = start + LEAD_IN
        for s in sentences:
            d = voice_len * len(s) / total
            cues.append(f"{n}\n{srt_time(t)} --> {srt_time(t + d)}\n{s}\n")
            t += d
            n += 1
    path = OUT / "yudhix-demo.srt"
    path.write_text("\n".join(cues))
    return path


def main() -> None:
    only = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)
    meta_path = OUT / "clips.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome") if shutil.which("google-chrome") or Path(
            "/Applications/Google Chrome.app").exists() else pw.chromium.launch()
        state = login(browser)
        for n, scene in enumerate(SCENES, start=1):
            if only and scene["id"] not in only:
                continue
            voice_len = speak(scene)
            print(f"{n:>2}. {scene['title']:<24} voice {voice_len:5.1f}s", flush=True)
            rec = record(browser, state, n, scene, voice_len)
            encode(scene, rec)
            meta[scene["id"]] = {"voice": voice_len, "length": rec["length"]}
            meta_path.write_text(json.dumps(meta, indent=1))
        browser.close()

    missing = [s["id"] for s in SCENES if not (CLIPS / f"{s['id']}.mp4").exists() or s["id"] not in meta]
    if missing:
        print(f"Recorded. Not joining yet; missing clips: {', '.join(missing)}")
        return
    timeline, t = [], 0.0
    with open(OUT / "concat.txt", "w") as f:
        for scene in SCENES:
            clip = CLIPS / f"{scene['id']}.mp4"
            f.write(f"file '{clip}'\n")
            length = duration(clip)
            timeline.append((scene, t, meta[scene["id"]]["voice"]))
            t += length
    joined = OUT / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "concat.txt"),
                    "-c", "copy", str(joined)], check=True)
    srt = subtitles(timeline)
    final = OUT / "yudhix-demo.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(joined), "-i", str(srt), "-map", "0", "-map", "1",
                    "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
                    "-movflags", "+faststart", str(final)], check=True)
    joined.unlink()
    print(f"\nDone: {final} ({t / 60:.1f} min), subtitles {srt}, screenshots {SHOTS}")


if __name__ == "__main__":
    main()
