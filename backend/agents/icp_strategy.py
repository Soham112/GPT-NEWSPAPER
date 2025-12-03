"""
ICP Strategy Agent
------------------

Generates ICP strategy JSON based on:
- topic
- grounded bullets with citations
- market insights
- tags
- sources
- client metadata

This agent is **optional** and is only invoked when:
- include_icp == True AND
- a valid client object is provided.

It MUST NOT mutate the existing article state (bullets, insights, tags, sources).
"""

from typing import Any, Dict, List
import json
import random
import time

from langchain_groq import ChatGroq

from backend.config import (
    GROQ_API_KEY,
    SUMMARY_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    LLM_CALL_DELAY_SECONDS,
)


SYSTEM_PROMPT = (
    'You are an ICP-strategy agent. You receive topic, grounded bullets with citations, '
    'market insights, and an ICP description. Use ONLY provided data. Output STRICT JSON:\n\n'
    '{\n'
    '  "icp_profile": {...},\n'
    '  "icp_pains": [...],\n'
    '  "icp_triggers": [...],\n'
    '  "icp_jobs_to_be_done": [...],\n'
    '  "icp_risks": [...],\n'
    '  "icp_recommendations": [...],\n'
    '  "product_opportunities": [...],\n'
    '  "workflow_impact": [...],\n'
    '  "decision_framework": {\n'
    '      "if": "...",\n'
    '      "then": "...",\n'
    '      "because": "...",\n'
    '      "evidence": [1]\n'
    '  }\n'
    '}'
)


class ICPStrategyAgent:
    """Standalone ICP Strategy Agent that returns structured ICP strategy JSON."""

    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY must be set to use ICPStrategyAgent")

        # Use SUMMARY_MODEL (llama-3.x) for ICP strategy generation
        self.llm = ChatGroq(
            model=SUMMARY_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

    def _jittered_sleep(self) -> None:
        """Add jittered sleep to avoid rate limit bursts."""
        delay = random.uniform(*LLM_CALL_DELAY_SECONDS)
        time.sleep(delay)

    def generate_icp_strategy(
        self,
        topic: str,
        bullets: List[Dict[str, Any]],
        insights: Dict[str, Any],
        tags: Dict[str, Any],
        sources: List[Dict[str, Any]],
        client: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate ICP strategy JSON.

        This method is **pure** and does not modify the input objects.
        """
        self._jittered_sleep()

        # Build a compact but explicit user prompt. We rely on the system
        # message to enforce JSON-only output and grounding.
        payload = {
            "topic": topic,
            "client": client,
            "tags": tags,
            "bullets": bullets,
            "insights": insights,
            "sources": [
                {
                    "title": s.get("title"),
                    "url": s.get("url"),
                    "snippet": s.get("snippet"),
                    "source_domain": s.get("source_domain"),
                }
                for s in sources
            ],
        }

        user_content = (
            "You receive the following structured data as JSON. "
            "Use ONLY this data to build the ICP strategy JSON described in the system message. "
            "Do not add fields, do not change the schema, and do not include any commentary.\n\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        messages = [
            ("system", SYSTEM_PROMPT),
            ("user", user_content),
        ]

        try:
            response = self.llm.invoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)

            # Ensure we return valid JSON
            icp_data = json.loads(raw_content)

            # Basic validation: ensure top-level keys exist
            expected_keys = [
                "icp_profile",
                "icp_pains",
                "icp_triggers",
                "icp_jobs_to_be_done",
                "icp_risks",
                "icp_recommendations",
                "product_opportunities",
                "workflow_impact",
                "decision_framework",
            ]
            for key in expected_keys:
                icp_data.setdefault(key, {} if key in ("icp_profile", "decision_framework") else [])

            return icp_data
        except Exception as e:
            # Propagate error to caller; they will attach icp_strategy_error
            raise RuntimeError(f"ICP strategy generation failed: {e}") from e


