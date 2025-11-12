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

    def run(self, queries: list, layout: str):
        # Initialize agents
        search_agent = SearchAgent()
        curator_agent = CuratorAgent()
        writer_agent = WriterAgent()
        critique_agent = CritiqueAgent()
        designer_agent = DesignerAgent(self.output_dir)
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
                    self._process_topic_json, topic, domains, window, k, strict
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
    ) -> Dict[str, Any]:
        """Process a single topic and return JSON result."""
        # Initialize agents
        search_agent = SearchAgent()
        curator_agent = CuratorAgent()
        writer_agent = WriterJSONAgent()
        
        # Create simplified state
        article_state = {
            "query": topic,
            "domains": domains,
            "time_range": window,
            "k": k,
        }
        
        # Step 1: Discover sources using XLR8 Research method
        sources = search_agent.discover_sources(topic, domains, window, n=10)
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
        
        # Step 2: Curate (if we have more than k sources)
        if len(sources) > k:
            article_state = curator_agent.run(article_state)
            sources = article_state.get("sources", [])[:k]  # Ensure we only keep k sources
        
        # Format sources for response
        formatted_sources = [
            {
                "title": s.get("title", "No title"),
                "url": s.get("url", ""),
                "date": s.get("published_date", ""),
                "snippet": s.get("content", s.get("snippet", ""))[:200],
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
        
        # Format summary bullets
        summary = [
            {
                "bullet": bullet.get("text", ""),
                "cite": bullet.get("cite", []),
            }
            for bullet in bullets
        ]
        
        # Return in the requested format
        return {
            "topic": topic,
            "sources": formatted_sources,
            "summary": summary,
            "links": links,
            "headline": headline,
            "why_it_matters": why_it_matters,
            "tags": tags,
        }
