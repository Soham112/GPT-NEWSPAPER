from tavily import TavilyClient
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

    def _filter_sources(self, sources: list, domains: list = None) -> list:
        """Filter sources: drop home/topic pages, duplicates by host, items without title/description."""
        filtered = []
        seen_urls = set()
        seen_hosts = set()
        
        for source in sources:
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
    
    def discover_sources(self, topic: str, domains: list = None, window: str = "week", n: int = 10) -> list:
        """
        XLR8 Research: Discover sources using Tavily with advanced search.
        Returns top n unique sources after filtering.
        """
        sources, _ = self.search_tavily(topic, window, domains, max_results=16)
        
        # Fallback to month if <3 sources
        if len(sources) < 3 and window == "week":
            self._jittered_sleep()
            sources, _ = self.search_tavily(topic, "month", domains, max_results=16)
        
        # Return top n
        return sources[:n]
    
    def search_sources(self, topic: str, domains: list = None, time_range: str = "week", k: int = 5) -> list:
        """
        Alias for discover_sources (backward compatibility).
        """
        return self.discover_sources(topic, domains, time_range, k)

    def search_tavily(
        self,
        query: str,
        time_range: str = TAVILY_DEFAULT_TIME_RANGE,
        domains: list = None,
        max_results: int = 16,
    ):
        """Search Tavily with time range and domain filters (XLR8 Research)."""
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
            
            # Filter sources (removes duplicates, home pages, items without title/description)
            sources = self._filter_sources(sources, domains)
            
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
    ):
        """Search with fallback: week -> month if insufficient results."""
        sources, image = self.search_tavily(query, time_range, domains)
        
        # Fallback to month if insufficient sources
        if len(sources) < MIN_SOURCES_REQUIRED and time_range == TAVILY_DEFAULT_TIME_RANGE:
            self._jittered_sleep()
            sources, image = self.search_tavily(
                query, TAVILY_FALLBACK_TIME_RANGE, domains
            )
        
        return sources, image

    def run(self, article: dict):
        """Original run method for HTML workflow."""
        query = article.get("query", "")
        domains = article.get("domains")
        time_range = article.get("time_range", TAVILY_DEFAULT_TIME_RANGE)
        
        sources, image = self.search_with_fallback(query, domains, time_range)
        
        article["sources"] = sources
        article["image"] = image
        article["time_range_used"] = time_range
        
        return article
