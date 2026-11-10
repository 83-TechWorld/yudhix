// Builds Yudhix-Demo.pptx from scenes.py and the screenshots recorded by record_demo.py (out/shots/*.png).
// Each app scene becomes a slide with its screenshot, title, caption and key points; its narration goes
// into the speaker notes, so presenting the deck follows the same script as the video.
//
//   node build_deck.js          (after: python record_demo.py)
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const SHOTS = path.join(HERE, "out", "shots");
const OUT = path.join(HERE, "Yudhix-Demo.pptx");
const SCENES = JSON.parse(execFileSync("python3", ["-c", "import json, scenes; print(json.dumps(scenes.SCENES))"], { cwd: HERE }));
const byId = Object.fromEntries(SCENES.map((s, i) => [s.id, { ...s, n: i + 1 }]));

// Palette: night ink + Yudhix indigo, with the verdict colours as accents.
const INK = "0F1020", INK_2 = "1B1D33", INDIGO = "6366F1", INDIGO_SOFT = "E0E7FF", WHITE = "FFFFFF";
const TEXT = "18181B", MUTED = "52525B", LINE = "E4E4E7", PAPER = "F6F6FA";
const OK = "16A34A", WARN = "D97706", BAD = "DC2626";
const HEAD = "Calibri", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Yudhix product demo";
pres.author = "Yudhix";
pres.company = "Yudhix";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

const W = 13.333, H = 7.5, M = 0.6;
const footer = (dark) => [
  { text: { text: "Yudhix · truth-first social intelligence", options: { x: M, y: H - 0.45, w: 6, h: 0.3, fontSize: 10, color: dark ? "8B8DB0" : "A1A1AA", fontFace: BODY } } },
];

// ---- Layouts (frames). Content is composed per slide on top of them.
pres.defineSlideMaster({
  title: "DARK", background: { color: INK },
  objects: [...footer(true)],
  slideNumber: { x: W - 1.0, y: H - 0.45, w: 0.5, h: 0.3, fontSize: 10, color: "8B8DB0", fontFace: BODY },
});
pres.defineSlideMaster({
  title: "LIGHT", background: { color: WHITE },
  objects: [...footer(false),
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.45, w: W - 2 * M, h: 0.9, fontSize: 36, bold: true,
      color: TEXT, fontFace: HEAD, valign: "top", align: "left", margin: 0 }, text: "" } }],
  slideNumber: { x: W - 1.0, y: H - 0.45, w: 0.5, h: 0.3, fontSize: 10, color: "A1A1AA", fontFace: BODY },
});
for (const side of ["LEFT", "RIGHT"]) {
  const tx = side === "LEFT" ? 9.15 : M;
  pres.defineSlideMaster({
    title: `SHOT_${side}`, background: { color: PAPER },
    objects: [...footer(false),
      { placeholder: { options: { name: "title", type: "title", x: tx, y: 2.05, w: 3.6, h: 1.25, fontSize: 32, bold: true,
        color: TEXT, fontFace: HEAD, valign: "top", align: "left", margin: 0 }, text: "" } }],
    slideNumber: { x: W - 1.0, y: H - 0.45, w: 0.5, h: 0.3, fontSize: 10, color: "A1A1AA", fontFace: BODY },
  });
}

// ---- Building blocks
function badge(slide, x, y, n, size = 0.5) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: size, h: size, rectRadius: 0.1, fill: { color: INDIGO },
    line: { color: INDIGO }, objectName: `badge ${n}` });
  slide.addText(String(n), { x, y, w: size, h: size, align: "center", valign: "middle", fontSize: size > 0.6 ? 22 : 16,
    bold: true, color: WHITE, margin: 0, isTextBox: true });
}

function logo(slide, x, y) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.55, h: 0.55, rectRadius: 0.12, fill: { color: INDIGO },
    line: { color: INDIGO }, objectName: "logo mark" });
  slide.addText("Y", { x, y, w: 0.55, h: 0.55, align: "center", valign: "middle", fontSize: 22, bold: true, color: WHITE,
    margin: 0, isTextBox: true });
  slide.addText("Yudhix", { x: x + 0.7, y, w: 2.5, h: 0.55, valign: "middle", fontSize: 22, bold: true, color: WHITE,
    margin: 0, isTextBox: true });
}

function shot(slide, id, x, y, w) {
  const h = w * 9 / 16;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.08, y: y - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.12,
    fill: { color: WHITE }, line: { color: LINE, width: 0.75 },
    shadow: { type: "outer", color: "000000", opacity: 0.18, blur: 14, offset: 4, angle: 90 }, objectName: `frame ${id}` });
  const file = path.join(SHOTS, `${id}.png`);
  if (fs.existsSync(file)) {
    slide.addImage({ path: file, x, y, w, h, altText: `Screenshot: ${byId[id] ? byId[id].title : id}` });
  } else {
    slide.addText(`Screenshot missing: run record_demo.py (${id})`, { x, y, w, h, align: "center", valign: "middle",
      fontSize: 14, color: MUTED, isTextBox: true });
  }
}

function sceneSlide(id, side) {
  const s = byId[id];
  const slide = pres.addSlide({ masterName: `SHOT_${side}`, sectionTitle: "Product tour" });
  const tx = side === "LEFT" ? 9.15 : M;
  const sx = side === "LEFT" ? M : W - M - 8.3;
  shot(slide, id, sx, (H - 8.3 * 9 / 16) / 2 - 0.1, 8.3);
  badge(slide, tx, 1.35, s.n);
  slide.addText(s.title, { placeholder: "title" });
  const oneLine = s.title.length <= 16; // ~16 characters fit one line at 32pt in this column
  const cy = oneLine ? 2.75 : 3.35;
  slide.addText(s.caption, { x: tx, y: cy, w: 3.6, h: 0.75, fontSize: 16, italic: true, color: INDIGO, margin: 0,
    valign: "top", isTextBox: true });
  slide.addText((s.points || []).map((p, i, a) => ({ text: p, options: { bullet: { indent: 16 }, breakLine: i < a.length - 1 } })),
    { x: tx, y: cy + 0.9, w: 3.6, h: 2.2, fontSize: 15, color: TEXT, valign: "top", margin: 0, paraSpaceAfter: 8, isTextBox: true });
  slide.addNotes(s.narration);
  return slide;
}

// ---- 1. Title
pres.addSection({ title: "Opening" });
{
  const s = byId.intro;
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  logo(slide, M, 0.55);
  slide.addText(s.card.eyebrow.toUpperCase(), { x: M, y: 2.0, w: 6, h: 0.4, fontSize: 14, bold: true, charSpacing: 4,
    color: "A5B4FC", margin: 0, isTextBox: true });
  slide.addText(s.card.headline, { x: M, y: 2.45, w: 5.9, h: 2.1, fontSize: 44, bold: true, color: WHITE, margin: 0,
    valign: "top", fontFace: HEAD, isTextBox: true });
  slide.addText(s.card.sub.replace(/ · /g, "\n"), { x: M, y: 4.2, w: 5.6, h: 1.4, fontSize: 16, color: "C7C9E0", margin: 0,
    valign: "top", paraSpaceAfter: 4, isTextBox: true });
  shot(slide, "impact", 6.85, 1.75, 5.9);
  slide.addNotes(s.narration);
}

// ---- 2. The problem, with the demo video's own numbers
{
  const slide = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Opening" });
  slide.addText("One wrong claim, thousands of angry comments", { placeholder: "title" });
  const stats = [
    { big: "3 of 4", label: "claims in the video are disputed", color: BAD },
    { big: "2.7k", label: "comments under it", color: INDIGO },
    { big: "597", label: "negative comments to answer", color: WARN },
  ];
  const cw = 3.75, gap = 0.4, x0 = M;
  stats.forEach((st, i) => {
    const x = x0 + i * (cw + gap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.75, w: cw, h: 2.6, rectRadius: 0.15, fill: { color: PAPER },
      line: { color: LINE, width: 0.75 }, objectName: `stat ${i + 1}` });
    slide.addText(st.big, { x: x + 0.35, y: 2.0, w: cw - 0.7, h: 1.2, fontSize: 60, bold: true, color: st.color, margin: 0,
      fontFace: HEAD, isTextBox: true });
    slide.addText(st.label, { x: x + 0.35, y: 3.25, w: cw - 0.7, h: 0.8, fontSize: 16, color: MUTED, margin: 0,
      valign: "top", isTextBox: true });
  });
  slide.addText([
    { text: "Without Yudhix, a brand can't tell ", options: {} },
    { text: "which comments react to misinformation", options: { bold: true } },
    { text: " and which point to a real product problem, so it either stays silent or answers everyone the same way.", options: {} },
  ], { x: M, y: 4.75, w: 11.9, h: 1.0, fontSize: 18, color: TEXT, margin: 0, valign: "top", isTextBox: true });
  slide.addText("Example: “PlayStation Explains Why it’s Ending Physical Discs”, analyzed in the demo workspace.",
    { x: M, y: 5.85, w: 11.9, h: 0.4, fontSize: 12, italic: true, color: "A1A1AA", margin: 0, isTextBox: true });
  slide.addNotes("Set the scene with a real example from the demo workspace before showing the product.");
}

// ---- 3. How it works
{
  const s = byId.how;
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  slide.addText(s.card.eyebrow.toUpperCase(), { x: M, y: 0.9, w: 6, h: 0.4, fontSize: 14, bold: true, charSpacing: 4,
    color: "A5B4FC", margin: 0, isTextBox: true });
  slide.addText(s.card.headline, { x: M, y: 1.35, w: 12, h: 1.0, fontSize: 40, bold: true, color: WHITE, margin: 0,
    fontFace: HEAD, isTextBox: true });
  const n = s.card.steps.length, gap = 0.3, cw = (W - 2 * M - gap * (n - 1)) / n;
  const details = ["Transcript, details and comments", "Against your own knowledge base", "Sentiment, topic and intent",
    "Which claim caused which comment", "AI drafts, human approval"];
  s.card.steps.forEach((step, i) => {
    const x = M + i * (cw + gap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.0, w: cw, h: 3.0, rectRadius: 0.15, fill: { color: INK_2 },
      line: { color: "2E3150", width: 0.75 }, objectName: `step ${i + 1}` });
    badge(slide, x + 0.3, 3.3, i + 1, 0.55);
    slide.addText(step, { x: x + 0.3, y: 4.05, w: cw - 0.6, h: 1.0, fontSize: 17, bold: true, color: WHITE, margin: 0,
      valign: "top", isTextBox: true });
    slide.addText(details[i], { x: x + 0.3, y: 5.15, w: cw - 0.6, h: 0.7, fontSize: 13, color: "A9ABC8", margin: 0,
      valign: "top", isTextBox: true });
  });
  slide.addNotes(s.narration);
}

// ---- 4-14. Product tour: screenshot slides, alternating sides
pres.addSection({ title: "Product tour" });
["analyze", "videos", "claims", "impact", "growth", "inbox", "approvals", "ideas", "knowledge", "ai", "schedule"]
  .forEach((id, i) => sceneSlide(id, i % 2 === 0 ? "LEFT" : "RIGHT"));

// ---- 15. Trust: how hallucinations are kept out
pres.addSection({ title: "Trust" });
{
  const slide = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Trust" });
  slide.addText("Built so the AI can't make things up", { placeholder: "title" });
  const rows = [
    ["No evidence, no AI", "If nothing in your knowledge base matches, the claim is marked unverified without asking the model.", MUTED],
    ["Quotes are checked", "The AI must copy the source sentence it relied on, and that sentence must really be in your document.", OK],
    ["Figures compared by code", "Prices, sizes and dates are matched by the system, never trusted to the model.", INDIGO],
    ["Second opinion", "With cloud AI every claim is read twice; when the two readings disagree, a person reviews it.", WARN],
    ["People have the last word", "Anyone with edit rights can set a verdict; re-checks never overwrite it.", BAD],
  ];
  rows.forEach(([head, body, color], i) => {
    const y = 1.6 + i * 1.0;
    slide.addShape(pres.shapes.OVAL, { x: M, y: y + 0.05, w: 0.5, h: 0.5, fill: { color }, line: { color }, objectName: `guard ${i + 1}` });
    slide.addText(String(i + 1), { x: M, y: y + 0.05, w: 0.5, h: 0.5, align: "center", valign: "middle", fontSize: 15,
      bold: true, color: WHITE, margin: 0, isTextBox: true });
    slide.addText(head, { x: M + 0.8, y, w: 3.6, h: 0.6, fontSize: 18, bold: true, color: TEXT, valign: "middle", margin: 0, isTextBox: true });
    slide.addText(body, { x: M + 4.5, y, w: 7.6, h: 0.6, fontSize: 15, color: MUTED, valign: "middle", margin: 0, isTextBox: true });
  });
  slide.addNotes("Explain why verdicts can be trusted: evidence first, quotes verified, numbers by code, disagreements to people.");
}

// ---- 16. Close
pres.addSection({ title: "Close" });
{
  const s = byId.outro;
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
  logo(slide, M, 0.55);
  slide.addText(s.card.headline, { x: M, y: 1.7, w: 12, h: 1.6, fontSize: 44, bold: true, color: WHITE, margin: 0,
    valign: "top", fontFace: HEAD, isTextBox: true });
  const steps = [
    ["Pilot", "Analyze your 10 most-watched creator videos"],
    ["Ground it", "Upload your official specs, prices and policies"],
    ["Choose AI", "Local, or your own Claude, ChatGPT or Gemini key"],
  ];
  const cw = 3.75, gap = 0.4;
  steps.forEach(([head, body], i) => {
    const x = M + i * (cw + gap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.75, w: cw, h: 2.0, rectRadius: 0.15, fill: { color: INK_2 },
      line: { color: "2E3150", width: 0.75 }, objectName: `next ${i + 1}` });
    badge(slide, x + 0.3, 4.05, i + 1);
    slide.addText(head, { x: x + 1.0, y: 4.05, w: cw - 1.3, h: 0.5, fontSize: 20, bold: true, color: WHITE, valign: "middle",
      margin: 0, isTextBox: true });
    slide.addText(body, { x: x + 0.3, y: 4.75, w: cw - 0.6, h: 0.8, fontSize: 15, color: "C7C9E0", margin: 0, valign: "top",
      isTextBox: true });
  });
  slide.addText("Next steps", { x: M, y: 3.25, w: 4, h: 0.4, fontSize: 14, bold: true, charSpacing: 4, color: "A5B4FC",
    margin: 0, isTextBox: true });
  slide.addNotes(s.narration);
}

pres.writeFile({ fileName: OUT }).then(() => {
  // pptxgenjs adds folder entries to the zip, which some cloud editors refuse to open.
  try { execFileSync("zip", ["-dq", OUT, "*/"]); } catch (e) { /* none to remove */ }
  console.log(`Wrote ${OUT}`);
});
