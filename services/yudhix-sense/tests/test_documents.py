"""Knowledge documents: reading files and splitting them into clause-sized facts. No DB needed."""
import io
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.truth import documents  # noqa: E402


def docx(paragraphs):
    """A minimal .docx: [(style or None, text)]."""
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(
        f'<w:p>{f"<w:pPr><w:pStyle w:val=\"{st}\"/></w:pPr>" if st else ""}<w:r><w:t>{t}</w:t></w:r></w:p>'
        for st, t in paragraphs)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<w:document {w}><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


class DocumentTest(unittest.TestCase):
    def test_file_types(self):
        self.assertEqual(documents.file_type("Policy.PDF"), "pdf")
        with self.assertRaises(documents.DocumentError):
            documents.file_type("photo.png")

    def test_chunks_respect_the_limit_and_drop_crumbs(self):
        text = "Short.\n\n" + " ".join(f"Sentence number {i} about the warranty terms." for i in range(60))
        chunks = documents.chunk_text(text, limit=300)
        self.assertTrue(all(len(c) <= 300 for c in chunks))
        self.assertGreater(len(chunks), 3)
        self.assertNotIn("Short.", chunks)  # under MIN_CHARS on its own, merged into the next chunk
        self.assertTrue(chunks[0].startswith("Short."))

    def test_markdown_headings_become_titles(self):
        sections, _ = documents.read_sections("md", b"# Warranty\nThe console has a one year limited warranty from purchase.\n"
                                                    b"# Storage\nThe PS5 Pro ships with a 2TB SSD that can be expanded.")
        facts = documents.to_facts("PS5 Guide", sections)
        self.assertEqual([f.title for f in facts], ["PS5 Guide · Warranty", "PS5 Guide · Storage"])
        self.assertEqual([f.clause_ref for f in facts], ["§1", "§2"])

    def test_docx_headings(self):
        data = docx([("Heading1", "Disc drive"), (None, "The detachable disc drive retails at $79.99 in the United States."),
                     ("Heading1", "Online"), (None, "Discs play offline after a one-time pairing with the console online.")])
        facts = documents.to_facts("Hardware FAQ", documents.read_sections("docx", data)[0])
        self.assertEqual(len(facts), 2)
        self.assertEqual(facts[0].title, "Hardware FAQ · Disc drive")
        self.assertIn("$79.99", facts[0].statement)

    def test_csv_facts(self):
        data = b"Title,Statement,Category,Clause\nPrice,The disc drive costs $79.99 in the US.,Pricing,PR-3\nEmpty,,,\n"
        facts = documents.csv_facts(data)
        self.assertEqual(len(facts), 1)
        self.assertEqual((facts[0].category, facts[0].clause_ref), ("Pricing", "PR-3"))
        with self.assertRaises(documents.DocumentError):
            documents.csv_facts(b"name,text\na,b\n")

    def test_bad_upload_is_rejected_before_the_database(self):
        with self.assertRaises(documents.DocumentError):
            documents.upload("t", "u", "a.txt", "not base64!!")
        with self.assertRaises(documents.DocumentError):
            documents.upload("t", "u", "a.pdf", "aGVsbG8=")  # "hello" is not a PDF


if __name__ == "__main__":
    unittest.main()
