import re
from typing import Tuple, List


class PiiMasker:
    """
    Scrubs Personal Identifiable Information (PII) before storage and model inference.
    Supports standard international and custom Indian recognizers (Aadhaar, Phone, Email, Order IDs).
    """

    def __init__(self):
        # Regular expressions for high-accuracy regex patterns
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.in_phone_pattern = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b')
        self.us_phone_pattern = re.compile(r'(?:\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}\b')
        self.aadhaar_pattern = re.compile(r'\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b')
        self.order_pattern = re.compile(r'(?:order|ticket|ref|invoice)[\s#:\-]+([A-Za-z0-9]{4,12})', re.IGNORECASE)
        self.mention_pattern = re.compile(r'@\w+')

    def mask(self, text: str) -> Tuple[str, List[str]]:
        if not text:
            return "", []

        detected_entities = []
        masked = text

        if self.email_pattern.search(masked):
            masked = self.email_pattern.sub("<EMAIL>", masked)
            detected_entities.append("EMAIL")

        if self.in_phone_pattern.search(masked):
            masked = self.in_phone_pattern.sub("<PHONE>", masked)
            detected_entities.append("PHONE")
        elif self.us_phone_pattern.search(masked):
            masked = self.us_phone_pattern.sub("<PHONE>", masked)
            detected_entities.append("PHONE")

        if self.aadhaar_pattern.search(masked):
            masked = self.aadhaar_pattern.sub("<GOV_ID>", masked)
            detected_entities.append("GOV_ID")

        if self.order_pattern.search(masked):
            masked = self.order_pattern.sub("order <ORDER_ID>", masked)
            detected_entities.append("ORDER_ID")

        if self.mention_pattern.search(masked):
            masked = self.mention_pattern.sub("<USER>", masked)
            detected_entities.append("USER")

        return masked, list(set(detected_entities))
