from datetime import datetime
import time
import random
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from backend.config import (
    DISCOVERY_MODEL,
    MAX_TOKENS_CURATION,
    TEMPERATURE,
    GROQ_API_KEY,
    MAX_SOURCES_TO_CURATE,
    LLM_CALL_DELAY_SECONDS,
)


class CuratorAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=DISCOVERY_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS_CURATION,
        )

    def _jittered_sleep(self):
        """Add jittered sleep to avoid rate limit bursts."""
        delay = random.uniform(*LLM_CALL_DELAY_SECONDS)
        time.sleep(delay)

    def curate_sources(self, query: str, sources: list):
        """
        Curate relevant sources for a query using Groq.
        Returns top 5 most relevant sources.
        """
        if len(sources) <= MAX_SOURCES_TO_CURATE:
            return sources[:MAX_SOURCES_TO_CURATE]

        # Format sources with indices
        sources_text = "\n".join(
            [
                f"[{i+1}] {s.get('title', 'No title')} - {s.get('url', '')}"
                for i, s in enumerate(sources)
            ]
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a source curator for XLR8 Research. Given a user topic and a list of candidate sources, "
                    f"pick the most relevant, recent, and diverse top {MAX_SOURCES_TO_CURATE} sources.\n\n"
                    "Rules:\n"
                    "- Prefer articles ≤14 days old.\n"
                    "- Avoid duplicates or near-identical press releases.\n"
                    "- Return JSON only: { \"selected\": [ {\"idx\": <1-based>, \"reason\": \"<why>\"} ] }"
                )
            ),
            HumanMessage(
                content=(
                    f"Today's date: {datetime.now().strftime('%d/%m/%Y')}\n\n"
                    f"Topic or Query: {query}\n\n"
                    f"Articles:\n{sources_text}\n\n"
                    f"Return the top {MAX_SOURCES_TO_CURATE} most relevant sources as JSON with indices and reasons."
                )
            ),
        ]

        self._jittered_sleep()

        try:
            response = self.llm.invoke(messages).content

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parse JSON response
            result = json.loads(response)
            
            # Extract selected indices
            selected_indices = []
            if isinstance(result, dict) and "selected" in result:
                selected_indices = [item.get("idx", 0) - 1 for item in result["selected"] if isinstance(item, dict) and "idx" in item]
            elif isinstance(result, list):
                # Fallback: treat as array of indices
                selected_indices = [int(x) - 1 for x in result if isinstance(x, (int, str)) and str(x).isdigit()]
            
            # Filter sources by indices
            if selected_indices:
                selected_sources = [sources[i] for i in selected_indices if 0 <= i < len(sources)]
                if selected_sources:
                    return selected_sources[:MAX_SOURCES_TO_CURATE]
            
            # Fallback: try to extract URLs from response
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                urls = json.loads(json_match.group())
                selected_sources = [s for s in sources if s.get("url") in urls]
                if selected_sources:
                    return selected_sources[:MAX_SOURCES_TO_CURATE]

            return sources[:MAX_SOURCES_TO_CURATE]

        except Exception as e:
            print(f"Curator error: {e}, using first {MAX_SOURCES_TO_CURATE} sources")
            return sources[:MAX_SOURCES_TO_CURATE]

    def run(self, article: dict):
        article["sources"] = self.curate_sources(article["query"], article["sources"])
        return article
