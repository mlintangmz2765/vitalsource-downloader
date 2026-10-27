"""Page selection parsing and navigation planning (pure Python, no browser)."""
import itertools


def parse_page_spec(spec):
    """Parses a --pages value into a sorted list of unique 1-based page numbers.

    Accepts forms like "5", "1-10", "3,7-9" (whitespace tolerated). Returns None for
    "all" / empty, meaning the whole book. Raises ValueError on malformed input so a
    typo never silently turns into a full-book download.
    """
    if spec is None or not str(spec).strip() or str(spec).strip().lower() == "all":
        return None

    pages = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, _, hi_s = part.partition("-")
            lo, hi = _to_page_number(lo_s, part), _to_page_number(hi_s, part)
            if hi < lo:
                raise ValueError(f"Invalid page range '{part}': end is before start")
            pages.update(range(lo, hi + 1))
        else:
            pages.add(_to_page_number(part, part))

    if not pages:
        return None
    return sorted(pages)


def _to_page_number(text, context):
    text = text.strip()
    if not text.isdigit():
        raise ValueError(f"Invalid page selection '{context}': expected a number")
    number = int(text)
    if number < 1:
        raise ValueError(f"Invalid page selection '{context}': pages start at 1")
    return number


def describe_pages(pages):
    """Compresses a sorted page list into a human-readable form, e.g. '3, 7-9'."""
    if not pages:
        return ""
    chunks = []
    start = prev = pages[0]
    for page in pages[1:]:
        if page == prev + 1:
            prev = page
            continue
        chunks.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = page
    chunks.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(chunks)


def navigation_steps(targets, limit=None):
    """Yields (page_number, action) for each target page, in order.

    action is "jump" when the reader must be moved directly to that page (the first
    page, and any page that does not immediately follow the previous one) and "next"
    when a single Next click reaches it. targets may be an infinite iterator (e.g.
    itertools.count(1)) for an open-ended capture; limit caps the number of steps.
    """
    previous = None
    for count, page in enumerate(targets):
        if limit is not None and count >= limit:
            return
        if previous is not None and page == previous + 1:
            yield page, "next"
        else:
            yield page, "jump"
        previous = page


def all_pages(total=None):
    """Targets for a whole-book capture: an exact range if the total is known, else open-ended."""
    return range(1, total + 1) if total else itertools.count(1)
