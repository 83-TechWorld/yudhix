"""Upload documents into the knowledge base: PDF, Word (.docx), text, Markdown and CSV.

A document is split into clause-sized facts (a heading's paragraphs, up to ~700 characters), so
retrieval returns the exact clause and the quote check can match it word for word. Each fact keeps
the document title, its section or page as the clause reference, and the file name as the source.
CSV files are read as ready-made facts (columns: title, statement, category, clause, source).

The extracted text is stored in this database. Nothing depends on a copy at an AI provider.
"""
import base64
import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

from app.core.database import append_audit, cursor, fetch_all

MAX_BYTES = 10 * 1024 * 1024
MAX_FACTS = 2000
CHUNK_CHARS = 700
MIN_CHARS = 40
TYPES = {"pdf", "docx", "txt", "md", "csv"}


class DocumentError(Exception):
    pass


@dataclass
class Section:
    heading: str
    text: str
    page: Optional[int] = None


@dataclass
class Fact:
    title: str
    statement: str
    clause_ref: Optional[str]
    category: Optional[str] = None
    source: Optional[str] = None


# ----------------------------------------------------------------------------- reading files

def file_type(filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in TYPES:
        raise DocumentError("Upload a PDF, Word (.docx), text, Markdown or CSV file.")
    return ext


def read_sections(kind: str, data: bytes) -> Tuple[List[Section], Optional[int]]:
    """(sections, pages)."""
    if kind == "pdf":
        return _pdf(data)
    if kind == "docx":
        return _docx(data), None
    return _text(data.decode("utf-8", errors="replace"), markdown=kind == "md"), None


def _pdf(data: bytes) -> Tuple[List[Section], int]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            reader.decrypt("")
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception as e:
        raise DocumentError(f"Couldn't read this PDF ({type(e).__name__}). Is it password-protected?") from e
    sections = [Section("", text, page=i) for i, text in enumerate(pages, start=1) if text.strip()]
    if not sections:
        raise DocumentError("This PDF has no text layer (it may be a scan). Export it with text, or paste the facts.")
    return sections, len(pages)


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx(data: bytes) -> List[Section]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
        raise DocumentError("Couldn't read this Word file. Save it as .docx and try again.") from e
    sections, current = [], Section("", "")
    for p in root.iter(f"{_W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()
        if not text:
            continue
        style = p.find(f"{_W}pPr/{_W}pStyle")
        is_heading = style is not None and (style.get(f"{_W}val") or "").lower().startswith(("heading", "title"))
        if is_heading:
            if current.text.strip():
                sections.append(current)
            current = Section(text, "")
        else:
            current.text += text + "\n\n"
    if current.text.strip():
        sections.append(current)
    return sections


def _text(text: str, markdown: bool) -> List[Section]:
    sections, current = [], Section("", "")
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*)", line) if markdown else None
        if m:
            if current.text.strip():
                sections.append(current)
            current = Section(m.group(1).strip(), "")
        else:
            current.text += line + "\n"
    if current.text.strip():
        sections.append(current)
    return sections


# ----------------------------------------------------------------------------- splitting into facts

def to_facts(doc_title: str, sections: List[Section]) -> List[Fact]:
    facts: List[Fact] = []
    for s_no, s in enumerate(sections, start=1):
        chunks = chunk_text(s.text)
        for c_no, chunk in enumerate(chunks, start=1):
            ref = f"p.{s.page}" if s.page else f"§{s_no}"
            if len(chunks) > 1:
                ref += f".{c_no}"
            title = f"{doc_title} · {s.heading}" if s.heading else (f"{doc_title} · page {s.page}" if s.page else doc_title)
            facts.append(Fact(title=title[:255], statement=chunk, clause_ref=ref[:100]))
    return facts


def chunk_text(text: str, limit: int = CHUNK_CHARS) -> List[str]:
    """Paragraphs merged up to `limit` characters; long paragraphs split at sentence ends."""
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text or "")]
    pieces: List[str] = []
    for p in paras:
        if not p:
            continue
        if len(p) <= limit:
            pieces.append(p)
            continue
        sentence, buf = re.split(r"(?<=[.!?])\s+", p), ""
        for s in sentence:
            if buf and len(buf) + len(s) + 1 > limit:
                pieces.append(buf)
                buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            pieces.append(buf)
    chunks, buf = [], ""
    for piece in pieces:
        if buf and len(buf) + len(piece) + 1 > limit:
            chunks.append(buf)
            buf = piece
        else:
            buf = f"{buf} {piece}".strip()
    if buf:
        chunks.append(buf)
    return [c for c in chunks if len(c) >= MIN_CHARS]


def csv_facts(data: bytes) -> List[Fact]:
    text = data.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise DocumentError("The CSV is empty.")
    cols = {k.lower().strip(): k for k in rows[0].keys() if k}
    if "statement" not in cols or "title" not in cols:
        raise DocumentError("The CSV needs at least the columns: title, statement (optional: category, clause, source).")
    get = lambda r, name: (r.get(cols[name]) or "").strip() if name in cols else ""  # noqa: E731
    facts = [Fact(get(r, "title")[:255], get(r, "statement"), get(r, "clause")[:100] or None,
                  get(r, "category")[:100] or None, get(r, "source")[:255] or None)
             for r in rows if get(r, "title") and len(get(r, "statement")) >= 10]
    if not facts:
        raise DocumentError("No rows with a title and a statement of at least 10 characters.")
    return facts


# ----------------------------------------------------------------------------- store

def upload(tenant_id: str, actor: str, filename: str, content_base64: str, title: Optional[str] = None,
           category: Optional[str] = None) -> Dict:
    filename = (filename or "document").strip()[-255:]
    kind = file_type(filename)
    try:
        data = base64.b64decode(content_base64, validate=True)
    except ValueError as e:
        raise DocumentError("The file didn't arrive intact. Try again.") from e
    if not data:
        raise DocumentError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise DocumentError("Files up to 10 MB. Split larger documents.")
    digest = hashlib.sha256(data).hexdigest()
    doc_title = (title or re.sub(r"[_-]+", " ", filename.rsplit(".", 1)[0])).strip()[:200] or "Document"
    category = (category or "General").strip()[:100] or "General"

    pages = None
    if kind == "csv":
        facts = csv_facts(data)
    else:
        sections, pages = read_sections(kind, data)
        facts = to_facts(doc_title, sections)
    if not facts:
        raise DocumentError("No text long enough to use as a fact was found in this file.")
    if len(facts) > MAX_FACTS:
        raise DocumentError(f"This file would make {len(facts)} facts; the limit is {MAX_FACTS} per file.")

    with cursor(commit=True) as cur:
        cur.execute("SELECT filename FROM knowledge_document WHERE tenant_id = %s AND sha256 = %s", (tenant_id, digest))
        same = cur.fetchone()
        if same:
            raise DocumentError(f"This file is already in the knowledge base (as {same['filename']}).")
        cur.execute(
            """INSERT INTO knowledge_document (tenant_id, filename, title, category, file_type, size_bytes, sha256,
                   pages, uploaded_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (tenant_id, filename, doc_title, category, kind, len(data), digest, pages, actor))
        doc = dict(cur.fetchone())
        for i, f in enumerate(facts):
            cur.execute(
                """INSERT INTO product_knowledge (tenant_id, document_title, category, clause_ref, official_statement,
                       citation_source, document_id, chunk_index)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (tenant_id, f.title, f.category or category, f.clause_ref, f.statement, (f.source or filename)[:255],
                 doc["id"], i))
        append_audit(cur, tenant_id, actor, "USER", "KNOWLEDGE_DOCUMENT_UPLOADED", "KNOWLEDGE", str(doc["id"]),
                     {"filename": filename, "facts": len(facts), "sha256": digest})
    return _doc(doc, len(facts))


def list_documents(tenant_id: str) -> List[Dict]:
    return [_doc(r, int(r["facts"])) for r in fetch_all(
        """SELECT d.*, (SELECT count(*) FROM product_knowledge k WHERE k.document_id = d.id) AS facts
           FROM knowledge_document d WHERE d.tenant_id = %s ORDER BY d.created_at DESC""", (tenant_id,))]


def delete_document(tenant_id: str, actor: str, document_id: str) -> bool:
    with cursor(commit=True) as cur:
        cur.execute("DELETE FROM knowledge_document WHERE tenant_id = %s AND id = %s RETURNING filename",
                    (tenant_id, document_id))
        row = cur.fetchone()
        if row:
            append_audit(cur, tenant_id, actor, "USER", "KNOWLEDGE_DOCUMENT_DELETED", "KNOWLEDGE", document_id,
                         {"filename": row["filename"]})
    return bool(row)


def _doc(r: Dict, facts: int) -> Dict:
    return {"id": str(r["id"]), "filename": r["filename"], "title": r["title"], "category": r["category"],
            "fileType": r["file_type"], "sizeBytes": r["size_bytes"], "pages": r.get("pages"), "facts": facts,
            "createdAt": r["created_at"].isoformat() if r.get("created_at") else None}
