import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import NotRequired, TypedDict, Dict, Any, List

from langgraph.graph import StateGraph

# Import agent classes
from .agents import (
    CritiqueAgent,
    CuratorAgent,
    DesignerAgent,
    EditorAgent,
    PublisherAgent,
    SearchAgent,
    WriterAgent,
)
from .agents.writer_json import WriterJSONAgent
from .agents.insights import InsightsAgent
from .agents.icp_strategy import ICPStrategyAgent
from .agents.use_case_router import UseCaseRouterAgent
# Caching removed per requirements
from .cost_tracker import cost_tracker
from .config import (
    THREAD_POOL_SIZE,
    MIN_SOURCES_REQUIRED,
    ENABLE_CRITIC_LOOP,
    CRITIC_MIN_SOURCES,
)


class ArticleState(TypedDict, total=False):
    query: str
    sources: NotRequired[list[dict]]
    image: NotRequired[str]
    title: NotRequired[str]
    date: NotRequired[str]
    paragraphs: NotRequired[list[str]]
    summary: NotRequired[str]
    critique: NotRequired[str | None]
    message: NotRequired[str | None]
    html: NotRequired[str]
    path: NotRequired[str]


class MasterAgent:
    def __init__(self):
        self.output_dir = f"outputs/run_{int(time.time())}"
        os.makedirs(self.output_dir, exist_ok=True)

    def _construct_icp_profile_query(self, topic: str) -> str:
        """
        Construct an ICP-specific search query for leadership/executive pages.
        
        Extracts company/industry names from the topic and adds leadership-related keywords
        to target canonical leadership pages rather than recent news.
        
        Examples:
        - "Give me ICP titles and actual leaders relevant to First Solar" 
          -> "First Solar leadership team board of directors CEO"
        - "ICP for solar energy decision makers"
          -> "solar energy companies leadership team board of directors"
        """
        import re
        
        # Remove common ICP-related phrases to extract the core topic
        topic_lower = topic.lower()
        cleaned = topic
        
        # Remove ICP-related phrases
        icp_phrases = [
            "give me icp",
            "icp titles",
            "icp for",
            "actual leaders",
            "relevant to",
            "decision makers",
            "who is responsible",
            "who owns",
            "ideal customer profile",
            "buyer profile",
        ]
        
        for phrase in icp_phrases:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Extract potential company/industry names (capitalized words/phrases)
        # Look for capitalized words that might be company names
        words = cleaned.split()
        company_terms = []
        
        # Collect capitalized words/phrases (likely company or industry names)
        i = 0
        while i < len(words):
            word = words[i]
            # If word starts with capital letter and is not a common stop word
            if word and word[0].isupper() and len(word) > 1:
                # Collect consecutive capitalized words (e.g., "First Solar", "General Motors")
                phrase_parts = [word]
                i += 1
                while i < len(words) and words[i] and words[i][0].isupper():
                    phrase_parts.append(words[i])
                    i += 1
                if phrase_parts:
                    company_terms.append(" ".join(phrase_parts))
            else:
                i += 1
        
        # If we found company/industry terms, construct query with leadership keywords
        if company_terms:
            # Use the first significant company/industry term
            main_term = company_terms[0]
            # Add leadership-related keywords
            query = f"{main_term} leadership team board of directors CEO executives"
        else:
            # Fallback: use cleaned topic with leadership keywords
            if cleaned:
                query = f"{cleaned} leadership team board of directors executives"
            else:
                # Last resort: use original topic with leadership keywords
                query = f"{topic} leadership team board of directors executives"
        
        return query

    def _extract_company_name_from_query(self, topic: str) -> str:
        """
        Extract potential company name from query for domain biasing.
        
        Returns the first capitalized multi-word phrase that looks like a company name.
        """
        import re
        
        # Remove common ICP-related phrases
        cleaned = topic
        
        icp_phrases = [
            "give me icp",
            "icp titles",
            "icp for",
            "actual leaders",
            "relevant to",
            "decision makers",
        ]
        
        for phrase in icp_phrases:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Look for capitalized words/phrases (likely company names)
        words = cleaned.split()
        if not words:
            return ""
        
        # Find first capitalized phrase
        i = 0
        while i < len(words):
            word = words[i]
            if word and word[0].isupper() and len(word) > 1:
                phrase_parts = [word]
                i += 1
                while i < len(words) and words[i] and words[i][0].isupper():
                    phrase_parts.append(words[i])
                    i += 1
                if phrase_parts:
                    return " ".join(phrase_parts)
            i += 1
        
        return ""

    def run(self, queries: list, layout: str = None):
        # Initialize agents
        search_agent = SearchAgent()
        curator_agent = CuratorAgent()
        writer_agent = WriterAgent()
        critique_agent = CritiqueAgent()
        designer_agent = DesignerAgent(self.output_dir)
        # Layout parameter is deprecated - EditorAgent now uses unified layout
        editor_agent = EditorAgent(layout)
        publisher_agent = PublisherAgent(self.output_dir)

        # Define a LangGraph state graph
        workflow = StateGraph(ArticleState)

        # Add nodes for each agent
        workflow.add_node("search", search_agent.run)
        workflow.add_node("curate", curator_agent.run)
        workflow.add_node("write", writer_agent.run)
        workflow.add_node("critique", critique_agent.run)
        workflow.add_node("design", designer_agent.run)

        # Set up edges
        workflow.add_edge("search", "curate")
        workflow.add_edge("curate", "write")
        workflow.add_edge("write", "critique")
        workflow.add_conditional_edges(
            "critique",
            lambda state: "design" if state.get("critique") is None else "write",
        )

        # set up start and end nodes
        workflow.set_entry_point("search")
        workflow.set_finish_point("design")

        # compile the graph
        chain = workflow.compile()

        # Execute the graph for each query in parallel
        with ThreadPoolExecutor() as executor:
            parallel_results = list(
                executor.map(lambda q: chain.invoke({"query": q}), queries)
            )

        # Compile the final newspaper
        newspaper_html = editor_agent.run(parallel_results)
        newspaper_path = publisher_agent.run(newspaper_html)

        return newspaper_path

    def run_json(
        self,
        topics: List[str],
        domains: List[str] = None,
        window: str = "week",
        k: int = 5,
        strict: bool = True,
        client: Dict[str, Any] = None,
        include_insights: bool = True,
        include_icp: bool = False,
        use_case: str = None,
        region: str = "US",
        # LEADERSHIP_MODE START
        is_leadership_query: bool = False,
        company: str = None,
        # LEADERSHIP_MODE END
    ) -> Dict[str, Any]:
        """
        API-first method that returns JSON responses.
        
        Args:
            topics: List of topics to research
            domains: Optional domain filters
            window: Time range ("week" or "month")
            k: Number of sources to curate (default 5)
            strict: If True, fail closed on insufficient sources
        
        Returns:
            JSON response with articles, sources, summaries, and links
        """
        results = []
        
        # Process topics in parallel (limited by thread pool size)
        with ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
            futures = []
            for topic in topics:
                # Submit for processing (no caching)
                future = executor.submit(
                    self._process_topic_json,
                    topic,
                    domains,
                    window,
                    k,
                    strict,
                    client,
                    include_insights,
                    include_icp,
                    use_case,
                    region,
                    # LEADERSHIP_MODE START
                    is_leadership_query,
                    company,
                    # LEADERSHIP_MODE END
                )
                futures.append((topic, future))
            
            # Collect results
            for topic, future in futures:
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Error processing topic '{topic}': {e}")
                    if strict:
                        results.append({
                            "topic": topic,
                            "sources": [],
                            "summary": [],
                            "links": [],
                            "error": str(e),
                        })
        
        # Get cost summary (if tracking enabled)
        cost_summary = {}
        try:
            cost_summary = cost_tracker.get_request_summary()
        except:
            pass
        
        return {
            "topics": topics,
            "results": results,
            "cost": cost_summary,
        }

    def _process_topic_json(
        self,
        topic: str,
        domains: List[str] = None,
        window: str = "week",
        k: int = 5,
        strict: bool = True,
        client: Dict[str, Any] = None,
        include_insights: bool = True,
        include_icp: bool = False,
        use_case: str = None,
        region: str = "US",
        # LEADERSHIP_MODE START
        is_leadership_query: bool = False,
        company: str = None,
        # LEADERSHIP_MODE END
    ) -> Dict[str, Any]:
        """Process a single topic and return JSON result."""
        # Define ICP use cases that should skip Market Insights
        ICP_USE_CASES = {"icp_companies", "icp_profiles"}
        is_icp_use_case = use_case in ICP_USE_CASES

        # Determine effective k (number of curated sources) based on use_case.
        # For normal queries: k = 5 (default).
        # For ICP-related queries (icp_companies, icp_profiles): k = 12
        # Respect explicit k overrides where provided (only auto-upgrade default 5).
        if is_icp_use_case and (k is None or k == 5):
            effective_k = 12
        else:
            effective_k = k
        
        # Only build insights if include_insights is True AND we are not in an ICP-only use case
        # (unless user explicitly overrides with include_insights=True)
        should_build_insights = bool(include_insights) and not is_icp_use_case
        
        # LEADERSHIP_MODE START
        if is_leadership_query:
             # Force leadership_mode=True in SearchAgent (passed via is_leadership_query)
             # Skip industry agent (implied by use_case="icp_profiles")
             # Skip funding agent (implied by use_case="icp_profiles")
             # Skip insights agent
             should_build_insights = False
             # Force ICPProfileAgent only (handled by use_case="icp_profiles" logic later)
             # Ensure we don't accidentally run ICP strategy unless requested, but usually leadership query is just for profiles
             include_icp = False 
        # LEADERSHIP_MODE END

        # Initialize agents
        search_agent = SearchAgent()
        curator_agent = CuratorAgent()
        writer_agent = WriterJSONAgent()
        insights_agent = InsightsAgent() if should_build_insights else None
        icp_agent = ICPStrategyAgent() if include_icp and client else None
        
        # Create simplified state
        article_state = {
            "query": topic,
            "topic": topic,
            "domains": domains,
            "time_range": window,
            "k": effective_k,
            "sources": [],
            # LEADERSHIP_MODE START
            "is_leadership_query": is_leadership_query,
            # LEADERSHIP_MODE END
        }
        
        # Add client metadata if provided
        if client:
            article_state["client"] = client
        
        # Step 1: Discover sources using XLR8 Research method
        # For ICP profiles, use a broader time range, rewrite the query to target leadership
        # pages, and apply domain bias towards company site + Wikipedia.
        search_query = topic
        search_time_range = window
        search_domains = domains  # Use provided domains or None

        if use_case == "icp_profiles":
            # Construct ICP-specific query: extract company/industry names and add leadership keywords
            icp_query = self._construct_icp_profile_query(topic)
            if icp_query:
                search_query = icp_query
                # Use broader time range for ICP profiles to hit canonical leadership pages
                # Tavily supports: "day", "week", "month", "year", "all_time"
                search_time_range = "year"  # Broader time range for leadership pages

            # LEADERSHIP_MODE START
            # For leadership queries, don't restrict domains - we want global coverage.
            # The search agent will prioritize company domains via ranking, but we need
            # to search broadly to find leadership information from any source.
            # For non-leadership ICP queries, we can still bias towards company site and Wikipedia.
            if not is_leadership_query:
                # ICP-aware domain bias: bias Tavily towards company site and Wikipedia
                if search_domains is None:
                    company_name_for_domains = self._extract_company_name_from_query(topic)
                    if company_name_for_domains:
                        company_slug = (
                            company_name_for_domains.lower()
                            .replace(" ", "")
                            .replace(".", "")
                        )
                        preferred_domains = [f"{company_slug}.com", "wikipedia.org"]
                        search_domains = preferred_domains
            # LEADERSHIP_MODE END

        # Determine how many sources to target in discovery (align with effective_k)
        discovery_n = effective_k if isinstance(effective_k, int) and effective_k > 0 else 5
        # LEADERSHIP_MODE START
        # For leadership-focused ICP profile queries, pull in a larger set of sources.
        leadership_mode_active = bool(is_leadership_query and use_case == "icp_profiles")
        if leadership_mode_active:
            discovery_n = max(discovery_n, 20)
            print(f"[INFO] Leadership mode active for topic '{topic}': discovery_n={discovery_n}, search_domains={search_domains}, region={region}")
        # LEADERSHIP_MODE END

        sources = search_agent.discover_sources(
            topic,
            search_domains,
            window,
            n=discovery_n,
            region=region,
            search_query_override=search_query if search_query != topic else None,
            time_range_override=search_time_range if search_time_range != window else None,
            # LEADERSHIP_MODE START
            leadership_mode=leadership_mode_active,
            company=company,
            # LEADERSHIP_MODE END
        )
        
        # LEADERSHIP_MODE START
        if leadership_mode_active:
            print(f"[INFO] Leadership mode search returned {len(sources)} sources for topic '{topic}'")
        # LEADERSHIP_MODE END
        article_state["sources"] = sources
        
        # Check if sources are sufficient
        if len(sources) < MIN_SOURCES_REQUIRED:
            if strict:
                return {
                    "topic": topic,
                    "sources": [],
                    "summary": [],
                    "links": [],
                    "error": "INSUFFICIENT_SOURCES",
                }
            # Non-strict: continue with what we have
        
        # Step 2: Curate (if we have more than effective_k sources)
        if len(sources) > effective_k:
            article_state = curator_agent.run(article_state)
            sources = article_state.get("sources", [])[:effective_k]  # Ensure we only keep effective_k sources
            article_state["sources"] = sources
        
        # Format sources for response
        formatted_sources = [
            {
                "title": s.get("title", "No title"),
                "url": s.get("url", ""),
                "date": s.get("published_date", s.get("date", "")),
                "snippet": s.get("content", s.get("snippet", s.get("description", "")))[:200],
                "source_domain": s.get("url", "").split("/")[2] if s.get("url") else "",
            }
            for s in sources
        ]
        
        # Step 3: Write (generate bullets with citations)
        article_state = writer_agent.run(article_state)
        
        # Extract article data
        headline = article_state.get("headline", topic)
        bullets = article_state.get("bullets", [])
        why_it_matters = article_state.get("why_it_matters")
        tags = article_state.get("tags", {})
        links = article_state.get("links", [])
        quality_check = article_state.get("quality_check", "PASS")
        
        # Check for errors
        error = article_state.get("error")
        if error == "INSUFFICIENT_SOURCES":
            if strict:
                return {
                    "topic": topic,
                    "sources": formatted_sources,
                    "summary": [],
                    "links": links,
                    "error": "INSUFFICIENT_SOURCES",
                }
            # Non-strict: return partial results
        
        # Step 4: Generate insights (if enabled and not ICP use case)
        insights = None
        if not should_build_insights:
            if is_icp_use_case:
                print(f"[INFO] Insights generation skipped for ICP use case '{use_case}' on topic '{topic}'")
            else:
                print(f"[INFO] Insights generation disabled for topic '{topic}'")
        elif not insights_agent:
            print(f"[INFO] Insights agent not initialized for topic '{topic}'")
        elif not bullets:
            print(f"[WARNING] No bullets available for insights generation for topic '{topic}'")
        else:
            try:
                print(f"[INFO] Generating insights for topic: '{topic}' (bullets: {len(bullets)})")
                # Prepare article state for insights (include formatted sources)
                article_state["sources"] = formatted_sources
                article_state["bullets"] = bullets  # Ensure bullets are in article_state
                article_state["headline"] = headline
                article_state["why_it_matters"] = why_it_matters
                article_state["tags"] = tags
                article_state = insights_agent.run(article_state)
                insights = article_state.get("insights")
                
                if insights:
                    if insights.get("error"):
                        print(f"[WARNING] Insights generation returned error for topic '{topic}': {insights.get('error')} - {insights.get('message', '')}")
                    else:
                        print(f"[INFO] Insights generated successfully for topic '{topic}'")
                        print(f"[DEBUG] Insights keys: {list(insights.keys())}")
                else:
                    print(f"[WARNING] Insights generation returned None for topic '{topic}'")
            except Exception as e:
                print(f"[ERROR] Insights generation failed for topic '{topic}': {e}")
                import traceback
                traceback.print_exc()
                # Set error insights so frontend can display it
                insights = {
                    "error": "INSIGHTS_GENERATION_ERROR",
                    "message": str(e)
                }
        
        # Format summary bullets
        summary = [
            {
                "bullet": bullet.get("text", ""),
                "cite": bullet.get("cite", []),
            }
            for bullet in bullets
        ]
        
        # Build result
        result = {
            "topic": topic,
            "sources": formatted_sources,
            "summary": summary,
            "bullets": bullets,  # Also include as bullets for compatibility
            "links": links,
            "headline": headline,
            "why_it_matters": why_it_matters,
            "tags": tags,
            "quality_check": quality_check,
            "use_case": use_case,  # Always include use_case so frontend can branch rendering
        }
        
        # Add insights if generated (only include when actually generated, not for ICP use cases)
        # Include even if error, so frontend can display it
        if insights is not None:
            result["insights"] = insights
            if insights.get("error"):
                print(f"[INFO] Including insights with error in result for topic '{topic}'")
            else:
                print(f"[INFO] Including valid insights in result for topic '{topic}'")

        # Optionally generate use case output (fail-soft). Conditions:
        # - use_case is provided
        # - we have bullets (grounded content)
        # Note: This runs even when insights is None (e.g., for ICP use cases)
        use_case_output = None
        if use_case and bullets:
            try:
                print(f"[INFO] Generating use case output for topic '{topic}' with use_case='{use_case}'")
                router = UseCaseRouterAgent()
                use_case_output = router.run(
                    use_case=use_case,
                    topic=topic,
                    bullets=bullets,
                    insights=insights,  # may be None for ICP use cases
                    tags=tags,
                    sources=formatted_sources,
                    region=region,
                    client=client,
                    # LEADERSHIP_MODE START
                    is_leadership_query=is_leadership_query,
                    raw_query=topic,
                    company_hint=company,
                    # LEADERSHIP_MODE END
                )
                if use_case_output:
                    result["use_case_output"] = use_case_output
                    if use_case_output.get("error"):
                        print(f"[WARNING] Use case output returned error for topic '{topic}': {use_case_output.get('error')}")
                    else:
                        print(f"[INFO] Use case output generated successfully for topic '{topic}'")
            except Exception as e:
                print(f"[ERROR] Use case output generation failed for topic '{topic}': {e}")
                import traceback
                traceback.print_exc()
                result["use_case_output"] = {
                    "error": "USE_CASE_OUTPUT_ERROR",
                    "message": str(e)
                }

        # ICP profiles: leadership-recovery fallback search if no leaders found
        # Goal: If the first company has an empty leaders[] array, run a
        # fallback leadership-focused search against company site + Wikipedia,
        # merge those sources, and re-run ICPProfileAgent via UseCaseRouterAgent.
        if use_case == "icp_profiles":
            uc = result.get("use_case_output")
            if uc and not uc.get("error"):
                companies_uc = uc.get("companies") or []
                if companies_uc:
                    first_company = companies_uc[0]
                    leaders_list = first_company.get("leaders") or []
                    if not leaders_list:
                        company_name = first_company.get("name") or ""
                        if company_name:
                            company_slug = (
                                company_name.lower()
                                .replace(" ", "")
                                .replace(".", "")
                            )
                        else:
                            company_slug = ""

                        if company_slug:
                            try:
                                fallback_query = (
                                    f"{company_name} leadership team board of directors CEO executives"
                                )
                                fallback_domains = [f"{company_slug}.com", "wikipedia.org"]
                                print(
                                    f"[INFO] Running ICP leadership fallback search for '{company_name}' with query '{fallback_query}'"
                                )
                                fallback_sources, _ = search_agent.search_tavily(
                                    query=fallback_query,
                                    time_range="year",
                                    domains=fallback_domains,
                                    max_results=6,
                                    region=region,
                                )

                                if fallback_sources:
                                    # Merge fallback sources, preferring new leadership pages
                                    merged_sources = self._merge_sources_with_preference(
                                        sources,
                                        fallback_sources,
                                        preferred_domains=fallback_domains,
                                    )
                                    sources = merged_sources
                                    article_state["sources"] = sources

                                    # Rebuild formatted_sources from merged raw sources
                                    formatted_sources = [
                                        {
                                            "title": s.get("title", "No title"),
                                            "url": s.get("url", ""),
                                            "date": s.get("published_date", s.get("date", "")),
                                            "snippet": s.get(
                                                "content",
                                                s.get("snippet", s.get("description", "")),
                                            )[:200],
                                            "source_domain": s.get("url", "").split("/")[2]
                                            if s.get("url")
                                            else "",
                                        }
                                        for s in sources
                                    ]
                                    result["sources"] = formatted_sources

                                    # Re-run ICPProfileAgent via UseCaseRouterAgent with enriched sources
                                    try:
                                        print(
                                            f"[INFO] Re-running ICPProfileAgent with enriched sources for topic '{topic}'"
                                        )
                                        router = UseCaseRouterAgent()
                                        new_use_case_output = router.run(
                                            use_case=use_case,
                                            topic=topic,
                                            bullets=bullets,
                                            insights=insights,
                                            tags=tags,
                                            sources=formatted_sources,
                                            region=region,
                                            client=client,
                                            # LEADERSHIP_MODE START
                                            is_leadership_query=is_leadership_query,
                                            raw_query=topic,
                                            company_hint=company or company_name,
                                            # LEADERSHIP_MODE END
                                        )
                                        if new_use_case_output:
                                            result["use_case_output"] = new_use_case_output
                                    except Exception as e:
                                        print(
                                            f"[ERROR] ICP leadership fallback re-run failed for topic '{topic}': {e}"
                                        )
                                        import traceback

                                        traceback.print_exc()
                            except Exception as e:
                                print(
                                    f"[ERROR] ICP leadership fallback search failed for topic '{topic}': {e}"
                                )

        # Optionally generate ICP strategy (fail-soft). Conditions:
        # - include_icp is True
        # - client metadata is provided
        # - we have bullets (grounded content)
        if include_icp and client and bullets:
            if not icp_agent:
                print(f"[INFO] ICPStrategyAgent not initialized for topic '{topic}'")
            else:
                try:
                    print(f"[INFO] Generating ICP strategy for topic '{topic}'")
                    icp_strategy = icp_agent.generate_icp_strategy(
                        topic=topic,
                        bullets=summary,  # normalized bullets with citations
                        insights=insights or {},
                        tags=tags or {},
                        sources=formatted_sources,
                        client=client,
                    )
                    result["icp_strategy"] = icp_strategy
                    print(f"[INFO] ICP strategy generated successfully for topic '{topic}'")
                except Exception as e:
                    print(f"[ERROR] ICP strategy generation failed for topic '{topic}': {e}")
                    result["icp_strategy_error"] = {
                        "error": "ICP_STRATEGY_GENERATION_ERROR",
                        "message": str(e),
                    }

        return result
