import re
import unicodedata
import uuid


def slugify(text: str) -> str:
    """
    Converts a string like 'Allan's Tech Team!' to 'allans-tech-team'.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", text)
    return slug or str(uuid.uuid4())[:8]