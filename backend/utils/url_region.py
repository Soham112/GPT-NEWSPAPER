"""
URL Region Inference Utility

Provides heuristics to infer geographic region from URLs for filtering purposes.
"""
from urllib.parse import urlparse

GENERIC_TLDS = {
    "com", "org", "net", "io", "ai", "info", "biz", "co", "tv", "me", "news"
}

# Common non-US country-code TLDs
NON_US_CC_TLDS = {
    "uk", "co.uk", "de", "fr", "se", "fi", "no", "dk",
    "eu", "nl", "be", "ch", "es", "it", "pt",
    "ca", "mx", "br", "ar", "cl",
    "sa", "ae", "qa", "kw", "tr", "il",
    "in", "jp", "kr", "cn", "hk", "sg",
    "au", "nz", "za"
}


def infer_region_from_url(url: str) -> str:
    """
    Very rough heuristic:
    - returns 'NON_US' if URL clearly points to a non-US ccTLD
    - returns 'US' if TLD or subdomain suggests US (.us, .gov, .edu)
    - returns 'UNKNOWN' for generic .com/.net/.org/etc.
    """
    if not url:
        return "UNKNOWN"

    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "UNKNOWN"

    # strip port if present
    if ":" in host:
        host = host.split(":", 1)[0]

    # Strong US signals
    if host.endswith(".us") or host.endswith(".gov") or host.endswith(".edu"):
        return "US"

    parts = host.split(".")
    if len(parts) >= 3:
        # Handle multi-part TLDs like .co.uk
        last_two = ".".join(parts[-2:])
        if last_two in NON_US_CC_TLDS:
            return "NON_US"

    # Simple ccTLD detection: last label of length 2
    tld = parts[-1]
    if len(tld) == 2 and tld != "us":
        return "NON_US"

    # Generic TLDs => region unknown
    if tld in GENERIC_TLDS:
        return "UNKNOWN"

    # Default fallback
    return "UNKNOWN"


def is_us_allowed(url: str, target_region: str = "US") -> bool:
    """
    Decide whether this URL should be included for a US-focused query.
    For now:
    - If target_region == 'US':
        * Block URLs clearly NON_US
        * Allow US and UNKNOWN
    """
    region = infer_region_from_url(url)
    if target_region == "US":
        if region == "NON_US":
            return False
        return True
    # For other regions, just allow everything for now
    return True

