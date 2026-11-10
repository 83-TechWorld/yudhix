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


class AmazonTest(unittest.TestCase):
    def test_parse_url(self):
        from app.truth import amazon
        self.assertEqual(amazon.parse_url("https://www.amazon.in/Sony-PS5/dp/B08FV5GC28/ref=sr_1_1?x=1"),
                         ("amazon.in", "B08FV5GC28", "https://www.amazon.in/dp/B08FV5GC28"))
        self.assertEqual(amazon.parse_url("amazon.co.uk/gp/product/b08h97nyb9")[1], "B08H97NYB9")
        self.assertEqual(amazon.parse_url("https://www.amazon.com/product-reviews/B0CL5KNB9M/")[0], "amazon.com")
        for bad in ("https://www.flipkart.com/dp/B08FV5GC28", "https://www.amazon.in/s?k=ps5", ""):
            with self.assertRaises(amazon.AmazonError):
                amazon.parse_url(bad)

    def test_parse_product_page(self):
        from app.truth import amazon
        html = open(os.path.join(os.path.dirname(__file__), "fixtures", "amazon_in_product.html")).read()
        listing = amazon.parse_page(html, "amazon.in", "B08FV5GC28", "u")
        self.assertEqual((listing.title, listing.rating, listing.ratings_count), ("PlayStation 5 console", 4.5, 715))
        self.assertEqual(len(listing.reviews), 3)
        r = listing.reviews[0]
        self.assertEqual((r.review_id, r.rating, r.date, r.helpful_votes, r.verified, r.country),
                         ("R1L6QTXL1JHBOL", 5.0, "2021-02-09", 2, True, "India"))
        self.assertTrue(r.title.startswith("One of the Best Consoles"))
        self.assertTrue(r.body.startswith("First of all"))
        self.assertNotIn("double tap", r.body)

    def test_small_parsers(self):
        from app.truth import amazon
        self.assertEqual(amazon._date("Reviewed in the United States on March 3, 2025"), "2025-03-03")
        self.assertEqual(amazon._helpful("One person found this helpful"), 1)
        self.assertEqual(amazon._helpful("1,234 people found this helpful"), 1234)
        self.assertEqual([amazon.sentiment_for(x) for x in (5, 3, 1.0, None)], ["POSITIVE", "NEUTRAL", "NEGATIVE", None])
        self.assertTrue(amazon.is_robot_check("<html>Enter the characters you see below. Sorry, we just need to make sure you're not a robot. captcha</html>"))

    def test_channel_split(self):
        from app.truth import product_view
        rows = [{"platform": "YOUTUBE", "like_count": 10, "reply_count": 0, "sentiment": "NEGATIVE", "topics": ["PRICE"]},
                {"platform": "YOUTUBE", "like_count": 0, "reply_count": 0, "sentiment": "POSITIVE", "topics": []},
                {"platform": "AMAZON", "like_count": 3, "reply_count": 0, "sentiment": "POSITIVE", "topics": ["QUALITY"]}]
        out = product_view.split(rows)
        self.assertEqual(out["YOUTUBE"]["sentiment"], {"positive": 1, "neutral": 0, "negative": 1})
        self.assertEqual((out["AMAZON"]["comments"], out["AMAZON"]["positiveShare"]), (1, 1.0))
        self.assertEqual(out["YOUTUBE"]["topics"][0]["topic"], "PRICE")
        self.assertIn("Amazon", product_view._headline(out))
