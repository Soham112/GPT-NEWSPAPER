"""
Leadership scraper utilities - HTML fallback for extracting leadership names/titles.
"""

# LEADERSHIP_MODE START
import re
from typing import List, Dict

import httpx
from bs4 import BeautifulSoup


LEADERSHIP_TITLE_KEYWORDS = [
    "chief",
    "ceo",
    "cfo",
    "coo",
    "cto",
    "cio",
    "cro",
    "president",
    "vice president",
    "vp",
    "director",
    "head of",
    "officer",
    "chair",
    "founder",
]


def _construct_candidate_urls(company_name: str) -> List[str]:
    base = (company_name or "").strip().lower().replace(" ", "").replace(".", "")
    if not base:
        return []

    candidates = [
        f"https://{base}.com",
        f"https://www.{base}.com",
        f"https://{base}.com/about",
        f"https://{base}.com/about-us",
        f"https://{base}.com/leadership",
        f"https://{base}.com/our-leadership",
        f"https://{base}.com/management",
        f"https://{base}.com/management-team",
        f"https://{base}.com/en-us/about-us",
        f"https://{base}.com/en-us/about-us/leadership",
        f"https://{base}.com/en-us/about-us/board-of-directors",
    ]
    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _looks_like_human_name(text: str) -> bool:
    # Reject cookie banners, marketing text, etc.
    lowered = text.lower()
    reject_terms = [
        "cookies", "learn more", "privacy", "technology", "innovation", "mission",
        "subscribe", "newsletter", "contact", "about us", "careers", "investors",
        "read more", "click here", "all rights reserved", "copyright"
    ]
    if any(term in lowered for term in reject_terms):
        return False
        
    # Reject long paragraphs
    if len(text.split()) > 20:
        return False

    # Simple heuristic: 2–5 tokens, each starting with capital letter.
    # Accept patterns like "Mark Widmar", "Michael Ahearn"
    tokens = re.findall(r"\b[A-Z][a-z]+\b", text.strip())
    if not (2 <= len(tokens) <= 5):
        return False
    
    return True


def _looks_like_leadership_title(text: str) -> bool:
    lowered = text.lower()
    # Only accept titles containing specific keywords
    valid_title_parts = ["chief", "officer", "director", "president", "vice", "vp", "head", "chair"]
    if not any(part in lowered for part in valid_title_parts):
        return False
        
    return any(kw in lowered for kw in LEADERSHIP_TITLE_KEYWORDS)


def _extract_leaders_from_soup(url: str, soup: BeautifulSoup) -> List[Dict[str, str]]:
    leaders: List[Dict[str, str]] = []

    # Candidate elements: headings, strong tags, and obvious "card" containers
    name_candidates = []
    for tag_name in ["h1", "h2", "h3", "h4", "strong", "b"]:
        for el in soup.find_all(tag_name):
            text = (el.get_text(separator=" ", strip=True) or "").strip()
            if _looks_like_human_name(text):
                name_candidates.append(el)

    # Some sites use divs/spans with "leader" or "executive" classes
    for el in soup.find_all(["div", "span", "p"], class_=re.compile(r"(leader|executive|management|name|title)", re.I)):
        text = (el.get_text(separator=" ", strip=True) or "").strip()
        if _looks_like_human_name(text):
            name_candidates.append(el)

    seen_pairs = set()

    for name_el in name_candidates:
        name_text = (name_el.get_text(separator=" ", strip=True) or "").strip()
        if not _looks_like_human_name(name_text):
            continue

        title_text = ""

        # Look at siblings first
        sib = name_el.find_next_sibling()
        sibling_hops = 0
        while sib is not None and sibling_hops < 3 and not title_text:
            candidate = (sib.get_text(separator=" ", strip=True) or "").strip()
            if _looks_like_leadership_title(candidate):
                title_text = candidate
                break
            sib = sib.find_next_sibling()
            sibling_hops += 1

        # If not found in siblings, look slightly above/below in the DOM
        if not title_text:
            parent = name_el.parent
            if parent is not None:
                # Check parent's other children
                for child in parent.children:
                    if child == name_el:
                        continue
                    if hasattr(child, "get_text"):
                        candidate = (child.get_text(separator=" ", strip=True) or "").strip()
                        if _looks_like_leadership_title(candidate):
                            title_text = candidate
                            break
                
                # If still not found, check parent text if it's short enough
                if not title_text:
                    candidate = (parent.get_text(separator=" ", strip=True) or "").strip()
                    # Avoid using the entire massive block; just validate that some leadership token is present.
                    if _looks_like_leadership_title(candidate) and len(candidate) <= 120:
                         # Try to extract just the title part if possible, otherwise skip if it's too messy
                         # For now, we'll be conservative and skip if it contains the name itself to avoid duplication
                         if name_text not in candidate:
                             title_text = candidate

        if not title_text:
            continue

        if not _looks_like_leadership_title(title_text):
            continue

        key = (name_text.lower(), title_text.lower())
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        leaders.append(
            {
                "name": name_text,
                "title": title_text,
                "source": url,
            }
        )

    return leaders


def fetch_leadership_pages(company_name: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Best-effort HTML fallback to extract leadership names/titles from official pages.
    Returns:
        {
          "leaders": [
            {"name": "...", "title": "...", "source": "url"},
            ...
          ],
          "checked_urls": ["...", ...]
        }
    """
    leaders: List[Dict[str, str]] = []
    checked_urls: List[str] = []

    candidate_urls = _construct_candidate_urls(company_name)
    if not candidate_urls:
        return {"leaders": [], "checked_urls": []}

    for url in candidate_urls:
        checked_urls.append(url)
        try:
            resp = httpx.get(url, timeout=5.0, follow_redirects=True)
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            continue

        page_leaders = _extract_leaders_from_soup(url, soup)
        if page_leaders:
            leaders.extend(page_leaders)

    # Deduplicate leaders across all pages
    deduped: List[Dict[str, str]] = []
    seen = set()
    for leader in leaders:
        key = (leader.get("name", "").lower(), leader.get("title", "").lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(leader)

    return {"leaders": deduped, "checked_urls": checked_urls}

# LEADERSHIP_MODE END


