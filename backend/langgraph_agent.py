import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import NotRequired, TypedDict

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
