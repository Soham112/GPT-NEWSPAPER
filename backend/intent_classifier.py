"""
Intent Classifier - Automatically detects user query intent for routing.

This module provides automatic intent detection for user questions so that:
- ICP-related questions only return ICP output (no Market Insights card).
- Non-ICP questions still return Market Insights / Trends / Opportunities / Risks.
- The frontend no longer has to pass `use_case` or `include_insights` explicitly.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryIntent:
    """Detected intent from a user query."""
    use_case: Optional[str]  # "industry" | "funding" | "icp_companies" | "icp_profiles" | None
    include_insights: bool  # whether to run InsightsAgent
    region: Optional[str] = "US"  # default to US for now
    # LEADERSHIP_MODE START
    is_leadership_query: bool = False  # whether this is a leadership / executives lookup
    company: Optional[str] = None  # extracted company name for leadership queries
    # LEADERSHIP_MODE END


ICP_KEYWORDS = [
    "icp", "ideal customer profile", "ideal buyer", "buyer profile",
    "decision maker", "titles", "roles", "leaders", "who is responsible",
    "who buys", "who would buy", "who owns procurement", "who owns purchase",
    "responsible for", "actual leaders", "icp titles",
]

ICP_COMPANY_KEYWORDS = [
    "buyer companies", "ideal buyers", "which companies would buy",
    "target companies", "ideal buyer companies", "find ideal buyer",
    "ideal buyer companies", "companies for", "buyer companies for",
]

FUNDING_KEYWORDS = [
    "funding", "raised", "raise", "venture capital", "vc",
    "seed round", "series a", "series b", "series c",
]

# LEADERSHIP_MODE START
LEADERSHIP_KEYWORDS = [
    "leadership", "board of directors", "board", "executives",
    "ceo", "chief executive", "founder", "co-founder", 
    "cto", "cfo", "coo", "cro", "vp ops", "vp operations",
    "president", "chairman", "chairwoman", "director"
]


def _looks_like_company_name(raw_query: str) -> bool:
    """
    Heuristic to detect whether the query likely contains a company/entity name.

    We keep this intentionally conservative – it's okay to miss some cases, but we
    don't want to flip Leadership Mode on for generic questions.
    """
    if not raw_query:
        return False

    # Simple lexical hints that strongly suggest a company
    company_suffixes = [
        " inc",
        " inc.",
        " corp",
        " corp.",
        " corporation",
        " ltd",
        " ltd.",
        " llc",
        " gmbh",
        " plc",
        " technologies",
        " labs",
        " systems",
        " holdings",
        " group",
        " company",
    ]
    q_lower = raw_query.lower()
    if any(suffix in q_lower for suffix in company_suffixes):
        return True

    # Look for at least one token with an internal capital letter (e.g. "Salesforce", "OpenAI")
    import re

    tokens = re.findall(r"\b[^\s]+\b", raw_query)
    for tok in tokens:
        if any(c.isupper() for c in tok[1:]) and not tok.isupper():
            return True

    # Fallback: consider multi-word Title Case phrases as potential company names
    title_case_tokens = [t for t in tokens if t.istitle()]
    if len(title_case_tokens) >= 2:
        return True

    return False


def _is_leadership_query(raw_query: str, lowered: str) -> bool:
    """Detect whether the query is explicitly about leadership / executives for an entity."""
    if not raw_query:
        return False

    has_leadership_keyword = any(kw in lowered for kw in LEADERSHIP_KEYWORDS)
    if not has_leadership_keyword:
        return False
    
    # If we have a leadership keyword, we assume it's a leadership query
    # We don't strictly enforce company name check here to be more aggressive
    # as per the "HARD OVERRIDE" requirement.
    return True
# LEADERSHIP_MODE END

def extract_company_name_from_query(query: str) -> Optional[str]:
    """
    Extract potential company name from query for leadership mode.
    
    Simple heuristic:
    - Look for capitalized 2-word spans, e.g. "First Solar", "Silicon Ranch"
    - Fall back to last capitalized span
    """
    if not query:
        return None
        
    import re
    
    # Remove leadership keywords to isolate company name
    cleaned = query
    for kw in LEADERSHIP_KEYWORDS:
        cleaned = re.sub(re.escape(kw), "", cleaned, flags=re.IGNORECASE)
    
    cleaned = cleaned.strip()
    if not cleaned:
        return None
        
    # Look for capitalized words (potential company names)
    # This regex matches consecutive capitalized words (e.g. "First Solar")
    # or single capitalized words if that's all we have.
    # We prioritize multi-word capitalized phrases.
    
    # Find all capitalized phrases
    matches = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', cleaned)
    
    if matches:
        # Return the longest match as it's likely the full company name
        return max(matches, key=len)
        
    # Fallback: if no capitalized words found (maybe user typed all lowercase),
    # return the cleaned query as best guess if it's short enough
    if len(cleaned.split()) <= 4:
        return cleaned.strip()
        
    return None


def detect_query_intent(query: str) -> QueryIntent:
    """
    Detect the intent of a user query to automatically route to appropriate agents.
    
    Args:
        query: The user's query string
        
    Returns:
        QueryIntent with detected use_case, include_insights, and region
    """
    raw_query = query or ""
    q = raw_query.lower()

    # Basic region detection (keep simple for now)
    region = "US"
    if any(term in q for term in ["europe", "eu ", " eu,", "european", "uk ", "united kingdom"]):
        region = "EU"
    elif any(term in q for term in ["middle east", "gcc", "saudi", "ksa"]):
        region = "MENA"

    # LEADERSHIP HARD OVERRIDE
    if any(kw in q for kw in LEADERSHIP_KEYWORDS):
        return QueryIntent(
            use_case="icp_profiles",
            include_insights=False,
            region=region,
            is_leadership_query=True,
            company=extract_company_name_from_query(raw_query),
        )

    # Funding first: explicit "raised VC" questions
    if any(k in q for k in FUNDING_KEYWORDS):
        return QueryIntent(
            use_case="funding",
            include_insights=True,
            region=region,
            is_leadership_query=False,
        )

    # ICP: profiles vs companies
    # Check for ICP profile keywords first (titles, leaders, responsible)
    if any(word in q for word in ["title", "titles", "role", "roles", "leader", "leaders", "founder", "ceo", "cfo", "cro", "vp", "vp ops", "head of", "decision maker", "who is responsible", "responsible for", "actual leaders", "icp titles"]):
        # If combined with ICP keywords, definitely profiles
        if any(k in q for k in ICP_KEYWORDS) or "icp " in q:
            return QueryIntent(
                use_case="icp_profiles",
                include_insights=False,
                region=region,
                is_leadership_query=_is_leadership_query(raw_query, q),
            )
        # Even without explicit ICP word, if asking about titles/leaders/responsible, treat as profiles
        if any(phrase in q for phrase in ["who is responsible for buying", "who owns procurement", "who owns purchase", "who makes the decision", "responsible for"]):
            return QueryIntent(
                use_case="icp_profiles",
                include_insights=False,
                region=region,
                is_leadership_query=_is_leadership_query(raw_query, q),
            )

    # Check for ICP company keywords
    if any(k in q for k in ICP_COMPANY_KEYWORDS) or "which companies" in q or "what companies" in q or "find ideal buyer" in q:
        return QueryIntent(
            use_case="icp_companies",
            include_insights=False,
            region=region,
            is_leadership_query=False,
        )

    # Generic ICP keywords (without specific profile/company indicators)
    if any(k in q for k in ICP_KEYWORDS) or "icp " in q:
        # If the question talks about titles/roles/leaders, treat as icp_profiles
        if any(word in q for word in ["title", "titles", "role", "roles", "leader", "leaders", "founder", "ceo", "cfo", "cro", "vp", "vp ops", "head of", "decision maker", "who is responsible", "responsible for", "actual leaders"]):
            return QueryIntent(
                use_case="icp_profiles",
                include_insights=False,
                region=region,
                is_leadership_query=_is_leadership_query(raw_query, q),
            )

        # Fallback: treat generic ICP question as profiles and hide insights
        return QueryIntent(
            use_case="icp_profiles",
            include_insights=False,
            region=region,
            is_leadership_query=_is_leadership_query(raw_query, q),
        )

    # Pure "who are the buyers / who would buy" even without ICP word
    if any(phrase in q for phrase in ["who would buy", "who buys", "buyers for", "buy this technology", "find ideal buyer"]) or "ideal buyers" in q:
        return QueryIntent(
            use_case="icp_companies",
            include_insights=False,
            region=region,
            is_leadership_query=False,
        )

    # Default: treat as industry-level, keep insights on
    return QueryIntent(
        use_case="industry",
        include_insights=True,
        region=region,
        is_leadership_query=_is_leadership_query(raw_query, q),
    )

