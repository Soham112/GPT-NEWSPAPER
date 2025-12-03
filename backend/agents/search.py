from tavily import TavilyClient
import httpx
import os
import time
import random
from backend.config import (
    TAVILY_DEFAULT_TIME_RANGE,
    TAVILY_FALLBACK_TIME_RANGE,
    MIN_SOURCES_REQUIRED,
    DOMAIN_FILTERS,
    LLM_CALL_DELAY_SECONDS,
)
from backend.utils.url_region import is_us_allowed

# Lazy initialization of Tavily client
_tavily_client = None

def get_tavily_client():
    """Get or create Tavily client instance."""
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


class SearchAgent:
    def __init__(self):
        pass

    def _jittered_sleep(self):
        """Add jittered sleep to avoid rate limit bursts."""
        delay = random.uniform(*LLM_CALL_DELAY_SECONDS)
        time.sleep(delay)

    def _filter_sources(self, sources: list, domains: list = None, region: str = "US") -> list:
        """
        Filter sources: drop home/topic pages, duplicates by host, items without title/description.
        Also applies region-based URL filtering for US-focused queries.
        """
        # First pass: region filtering (if region is US)
        region_filtered = []
        if region == "US":
            for source in sources:
                url = source.get("url", "")
                # Always allow sources from preferred/bias domains (if domains filter is used)
                # This is particularly important for ICP profile flows where we bias towards
                # company domains and Wikipedia for leadership information.
                is_preferred_domain = False
                if domains:
                    is_preferred_domain = any(d for d in domains if d and d in url)

                if is_preferred_domain or is_us_allowed(url, target_region="US"):
                    region_filtered.append(source)
            
            # Fallback: if region filtering removes everything, use original list
            if region_filtered:
                sources_to_filter = region_filtered
                filtered_out_count = len(sources) - len(region_filtered)
                if filtered_out_count > 0:
                    print(f"[INFO] Region filtering removed {filtered_out_count} non-US sources (kept {len(region_filtered)} sources)")
            else:
                sources_to_filter = sources
                print(f"[WARNING] Region filtering would remove all sources, falling back to original {len(sources)} sources")
        else:
            sources_to_filter = sources
        
        # Second pass: standard filtering (home pages, duplicates, etc.)
        filtered = []
        seen_urls = set()
        seen_hosts = set()
        
        for source in sources_to_filter:
            url = source.get("url", "")
            title = source.get("title", "")
            description = source.get("content", source.get("snippet", ""))
            
            # Skip if no title or description
            if not title or not description:
                continue
            
            # Skip if already seen (exact URL)
            if url in seen_urls:
                continue
            
            # Skip home pages and topic pages
            path = url.rstrip("/").split("/")[-1]
            if not path or path in ["", "index.html", "home"]:
                continue
            
            # Deduplicate by host (keep first occurrence)
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.netloc
                if host in seen_hosts:
                    continue
                seen_hosts.add(host)
            except:
                pass
            
            # Prefer HTTPS
            if url.startswith("http://") and url.replace("http://", "https://") in seen_urls:
                continue
            
            # Apply domain filter if specified
            if domains:
                domain_match = any(domain in url for domain in domains)
                if not domain_match:
                    continue
            
            seen_urls.add(url)
            filtered.append(source)
        
        return filtered
    
    def discover_sources(
        self, 
        topic: str, 
        domains: list = None, 
        window: str = "week", 
        n: int = 10, 
        region: str = "US",
        search_query_override: str = None,
        time_range_override: str = None,
        # LEADERSHIP_MODE START
        leadership_mode: bool = False,
        company: str = None,
        # LEADERSHIP_MODE END
    ) -> list:
        """
        XLR8 Research: Discover sources using Tavily with advanced search.
        Returns top n unique sources after filtering.
        
        Args:
            topic: Search topic (used if search_query_override is not provided)
            domains: Optional domain filters
            window: Time range ("week" or "month") - used if time_range_override is not provided
            n: Number of sources to return
            region: Geographic region for filtering (default "US")
            search_query_override: Optional override for the search query (e.g., for ICP-specific queries)
            time_range_override: Optional override for time range (e.g., "year" or "all_time" for ICP queries)
        """
        # Use override if provided, otherwise use defaults
        search_query = search_query_override if search_query_override is not None else topic
        time_range = time_range_override if time_range_override is not None else window

        # LEADERSHIP_MODE START
        # Leadership Mode: rewrite query, expand time range, and relax US-only bias.
        company_name_for_leadership = None
        if leadership_mode:
            # Extract company name
            import re
            
            # Try to extract a simple company name heuristic from the topic
            raw = topic or ""
            
            # Simple extraction: assume company name is the part before "leadership" or similar keywords
            # or just use the whole topic if it's short
            
            # Remove leadership keywords to isolate company name
            cleaned_topic = raw
            for kw in ["leadership", "board of directors", "board", "executives", "ceo", "cfo", "cto", "president"]:
                cleaned_topic = re.sub(re.escape(kw), "", cleaned_topic, flags=re.IGNORECASE)
            
            company_name_for_leadership = cleaned_topic.strip()
            if not company_name_for_leadership:
                 company_name_for_leadership = raw.strip()

            if company_name_for_leadership:
                # Leadership search override
                search_query = f"{company_name_for_leadership} leadership team board of directors executives CEO CFO CTO"
                
                # Force advanced search parameters
                # search_depth="advanced" is handled in search_tavily
                max_results = 20
                time_range = "year"
                
                # IMPORTANT: REMOVE US FILTER FOR LEADERSHIP
                region = None 

        # LEADERSHIP_MODE END

        # LEADERSHIP_MODE END
        
        # Configure Tavily parameters
        tavily_max_results = 16
        tavily_search_depth = "basic"  # Default
        tavily_time_range = time_range
        tavily_region = region
        
        if leadership_mode:
            tavily_max_results = 20
            tavily_search_depth = "advanced"
            tavily_time_range = "year"
            tavily_region = None  # DO NOT restrict by US for leadership lookups
            
        sources, _ = self.search_tavily(search_query, tavily_time_range, domains, max_results=tavily_max_results, region=tavily_region)
        
        # LEADERSHIP_MODE START
        # Direct fetch of official pages if in leadership mode
        if leadership_mode and company:
            try:
                slug = company.lower().replace(" ", "")
                candidate_urls = [
                    f"https://{slug}.com",
                    f"https://www.{slug}.com",
                    f"https://{slug}.com/about",
                    f"https://{slug}.com/about-us",
                    f"https://{slug}.com/leadership",
                    f"https://{slug}.com/team",
                    f"https://{slug}.com/board-of-directors",
                    f"https://{slug}.com/our-team",
                ]
                
                print(f"[INFO] Leadership mode: Attempting direct fetch of {len(candidate_urls)} candidate URLs for '{company}'")
                
                direct_sources = []
                with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                    for url in candidate_urls:
                        try:
                            resp = client.get(url)
                            if resp.status_code in [200, 301, 302]:
                                # Add as a source
                                direct_sources.append({
                                    "title": f"Official Page: {url}",
                                    "url": url,
                                    "content": "", # Leave empty, scraper will handle it
                                    "snippet": f"Official page for {company}",
                                    "score": 1.0, # High score
                                })
                        except Exception:
                            continue
                
                if direct_sources:
                    print(f"[INFO] Leadership mode: Found {len(direct_sources)} active official pages")
                    # Append to sources (deduplication happens later or we can do it here)
                    # We'll prepend them to ensure they are high priority
                    sources = direct_sources + sources
                    
                    # Deduplicate by URL
                    seen_urls = set()
                    unique_sources = []
                    for s in sources:
                        u = s.get("url", "")
                        if u not in seen_urls:
                            seen_urls.add(u)
                            unique_sources.append(s)
                    sources = unique_sources
                    
            except Exception as e:
                print(f"[ERROR] Leadership mode direct fetch failed: {e}")
        # LEADERSHIP_MODE END
        
        # Fallback logic: only apply if using default time range (not overridden)
        # For ICP/leadership queries with broader time ranges, we don't want to fallback to month
        if (
            len(sources) < 3
            and time_range_override is None
            and window == "week"
            and not leadership_mode
        ):
            self._jittered_sleep()
            sources, _ = self.search_tavily(search_query, "month", domains, max_results=max_results, region=region)

        # LEADERSHIP_MODE START
        # Leadership Mode: prioritise official company domains and canonical leadership paths,
        # then Wikipedia, then high-quality data providers like Crunchbase / Reuters / PitchBook.
        if leadership_mode and company_name_for_leadership:
            company = company_name_for_leadership
            slug = company.lower().replace(" ", "")
            
            # PRIORITY SEARCH LIST (FIRST!)
            priority_urls = [
                f"https://{slug}.com",
                f"https://www.{slug}.com",
                f"https://{slug}.com/about",
                f"https://{slug}.com/about-us",
                f"https://{slug}.com/leadership",
                f"https://{slug}.com/board-of-directors",
                f"https://{slug}.com/en-us/about-us/leadership",
                f"https://{slug}.com/en-us/about-us/board-of-directors",
                f"https://en.wikipedia.org/wiki/{company.replace(' ', '_')}"
            ]

            def _leadership_rank(source):
                url = source.get("url", "") or ""
                # Check priority URLs first
                for i, p_url in enumerate(priority_urls):
                    if url.startswith(p_url):
                        return i - 100 # Ensure these are at the very top
                
                # 0: official company canonical pages (generic match)
                if f"{slug}.com" in url:
                    return 0
                # 1: wikipedia entity page
                if "wikipedia.org" in url:
                    return 1
                # 2: high-quality company / finance data providers
                high_quality_domains = [
                    "crunchbase.com",
                    "pitchbook.com",
                    "reuters.com",
                    "bloomberg.com",
                ]
                if any(d in url for d in high_quality_domains):
                    return 2
                # 3: everything else
                return 3

            # Stable sort by rank while preserving original order within each bucket
            sources = sorted(
                list(enumerate(sources)),
                key=lambda pair: (_leadership_rank(pair[1]), pair[0]),
            )
            sources = [s for _, s in sources]

            # Return top 20 results
            n = 20
        # LEADERSHIP_MODE END

        # Return top n
        return sources[:n]
    
    def search_sources(self, topic: str, domains: list = None, time_range: str = "week", k: int = 5, region: str = "US") -> list:
        """
        Alias for discover_sources (backward compatibility).
        
        Args:
            topic: Search topic
            domains: Optional domain filters
            time_range: Time range ("week" or "month")
            k: Number of sources to return
            region: Geographic region for filtering (default "US")
        """
        return self.discover_sources(topic, domains, time_range, k, region)

    def search_tavily(
        self,
        query: str,
        time_range: str = TAVILY_DEFAULT_TIME_RANGE,
        domains: list = None,
        max_results: int = 16,
        region: str = "US",
    ):
        """
        Search Tavily with time range and domain filters (XLR8 Research).
        
        Args:
            query: Search query
            time_range: Time range ("week" or "month")
            domains: Optional domain filters
            max_results: Maximum results from Tavily
            region: Geographic region for URL filtering (default "US")
        """
        try:
            search_params = {
                "query": query,
                "topic": "news",
                "max_results": max_results,
                "include_images": True,
                "time_range": time_range,
                "search_depth": "advanced",  # XLR8: Advanced search depth
            }
            
            # Add domain filter if provided
            if domains:
                search_params["include_domains"] = domains
            
            client = get_tavily_client()
            results = client.search(**search_params)
            sources = results.get("results", [])
            
            # Filter sources (removes duplicates, home pages, items without title/description, and applies region filtering)
            sources = self._filter_sources(sources, domains, region=region)
            
            # Extract image
            try:
                image = results.get("images", [])[0] if results.get("images") else None
            except:
                image = "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8bmV3c3BhcGVyJTIwbmV3c3BhcGVyJTIwYXJ0aWNsZXxlbnwwfHwwfHw%3D&ixlib=rb-1.2.1&w=1000&q=80"
            
            return sources, image
        except Exception as e:
            print(f"Tavily search error: {e}")
            return [], None

    def search_with_fallback(
        self,
        query: str,
        domains: list = None,
        time_range: str = TAVILY_DEFAULT_TIME_RANGE,
        region: str = "US",
    ):
        """
        Search with fallback: week -> month if insufficient results.
        
        Args:
            query: Search query
            domains: Optional domain filters
            time_range: Time range ("week" or "month")
            region: Geographic region for URL filtering (default "US")
        """
        sources, image = self.search_tavily(query, time_range, domains, region=region)
        
        # Fallback to month if insufficient sources
        if len(sources) < MIN_SOURCES_REQUIRED and time_range == TAVILY_DEFAULT_TIME_RANGE:
            self._jittered_sleep()
            sources, image = self.search_tavily(
                query, TAVILY_FALLBACK_TIME_RANGE, domains, region=region
            )
        
        return sources, image

    def run(self, article: dict):
        """Original run method for HTML workflow."""
        query = article.get("query", "")
        domains = article.get("domains")
        time_range = article.get("time_range", TAVILY_DEFAULT_TIME_RANGE)
        region = article.get("region", "US")  # Default to US for backward compatibility
        
        sources, image = self.search_with_fallback(query, domains, time_range, region=region)
        
        article["sources"] = sources
        article["image"] = image
        article["time_range_used"] = time_range
        
        return article
