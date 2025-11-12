"""
Writer Agent for JSON output with grounded bullets and citations.
"""
import json
import time
import random
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from backend.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    GROQ_API_KEY,
    LLM_CALL_DELAY_SECONDS,
)

SYSTEM_PROMPT = """You are an AI Research Assistant for XLR8 Research. Summarize key points only from the given sources[].
Use their factual content only; no outside knowledge.

Return JSON only:
{
  "headline": "Concise title (≤15 words)",
  "bullets": [
    {"text": "Short factual bullet (≤2 sentences)", "cite": [1,3]},
    ...
  ],
  "why_it_matters": "Why it matters (Sales/Marketing): ... [2,4]",
  "tags": {"companies": [], "regions": [], "themes": []},
  "links": [{"n":1,"url":"..."},{"n":2,"url":"..."}]
}

Rules:
- Each bullet must cite at least one numeric source [n].
- No speculation or hallucinations.
- Use data, names, or numbers mentioned explicitly.
- Limit to 4–6 bullets max.
- If <3 valid sources, return {"error":"INSUFFICIENT_SOURCES"}.
- Headline: 1 sentence, max 15 words.
- Bullets: 4-6 bullets, each max 2 sentences.
- why_it_matters: Optional, only if relevant for sales/marketing context.
- tags: Extract from sources (companies as array, regions as array, themes as array).
- links: Map source indices to URLs with title.
"""


class WriterJSONAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=SUMMARY_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

    def _jittered_sleep(self):
        """Add jittered sleep to avoid rate limit bursts."""
        delay = random.uniform(*LLM_CALL_DELAY_SECONDS)
        time.sleep(delay)

    def _format_sources_for_prompt(self, sources: list) -> str:
        """Format sources with indices for citation."""
        formatted = []
        for idx, source in enumerate(sources, start=1):
            title = source.get("title", "No title")
            url = source.get("url", "")
            snippet = source.get("content", source.get("snippet", ""))[:200]
            formatted.append(f"[{idx}] {title}\nURL: {url}\n{snippet}")
        return "\n\n".join(formatted)

    def write_article(self, query: str, sources: list) -> dict:
        """Generate article with grounded bullets and citations."""
        if len(sources) < 3:
            return {"error": "INSUFFICIENT_SOURCES"}

        sources_text = self._format_sources_for_prompt(sources)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Today's date: {datetime.now().strftime('%d/%m/%Y')}\n\n"
                    f"Topic: {query}\n\n"
                    f"sources[]:\n{sources_text}\n\n"
                    "Generate the JSON response with grounded bullets and citations."
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

            article_data = json.loads(response)

            # Validate citations
            max_source_idx = len(sources)
            for bullet in article_data.get("bullets", []):
                cites = bullet.get("cite", [])
                # Filter out invalid citations
                valid_cites = [c for c in cites if 1 <= c <= max_source_idx]
                bullet["cite"] = valid_cites
                # If no valid citations, mark as error
                if not valid_cites:
                    bullet["error"] = "MISSING_CITATION"

            # Build links array from sources (with title)
            links = [
                {"n": idx, "url": source.get("url", ""), "title": source.get("title", "No title")}
                for idx, source in enumerate(sources, start=1)
            ]
            article_data["links"] = links

            # Ensure required fields and normalize tags structure
            article_data.setdefault("headline", query)
            article_data.setdefault("bullets", [])
            
            # Normalize tags to arrays (companies, regions, themes)
            tags = article_data.get("tags", {})
            if not isinstance(tags, dict):
                tags = {}
            
            # Convert to arrays if needed
            normalized_tags = {
                "companies": tags.get("companies", tags.get("company", [])),
                "regions": tags.get("regions", tags.get("region", [])),
                "themes": tags.get("themes", tags.get("theme", [])),
            }
            
            # Ensure arrays
            for key in normalized_tags:
                if not isinstance(normalized_tags[key], list):
                    if normalized_tags[key]:
                        normalized_tags[key] = [normalized_tags[key]]
                    else:
                        normalized_tags[key] = []
            
            article_data["tags"] = normalized_tags

            # Validation layer: Check citation quality
            quality_check = self._validate_citations(article_data, len(sources))
            article_data["quality_check"] = quality_check
            
            # Retry if validation fails
            if quality_check == "FAIL_RETRY" and len(sources) >= 3:
                print("Citation validation failed, retrying with stricter prompt...")
                return self._retry_with_stricter_prompt(query, sources)

            return article_data

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            if 'response' in locals():
                print(f"Response was: {response[:500]}")
            return {
                "error": "JSON_PARSE_ERROR",
                "headline": query,
                "bullets": [],
                "why_it_matters": None,
                "tags": {},
                "links": [],
            }
        except Exception as e:
            print(f"Writer error: {e}")
            return {
                "error": str(e),
                "headline": query,
                "bullets": [],
                "why_it_matters": None,
                "tags": {},
                "links": [],
            }

    def _validate_citations(self, article_data: dict, num_sources: int) -> str:
        """Validate that all citation indices exist in sources."""
        bullets = article_data.get("bullets", [])
        if not bullets:
            return "FAIL_RETRY"
        
        all_valid = True
        for bullet in bullets:
            cites = bullet.get("cite", [])
            if not cites:
                all_valid = False
                break
            # Check all citations are valid
            for cite in cites:
                if not (1 <= cite <= num_sources):
                    all_valid = False
                    break
            if not all_valid:
                break
        
        return "PASS" if all_valid else "FAIL_RETRY"
    
    def _retry_with_stricter_prompt(self, query: str, sources: list) -> dict:
        """Retry with stricter citation enforcement."""
        sources_text = self._format_sources_for_prompt(sources)
        
        strict_prompt = SYSTEM_PROMPT + "\n\nIMPORTANT: Citation must match exactly. Each bullet MUST cite at least one valid source index [1-" + str(len(sources)) + "]."
        
        messages = [
            SystemMessage(content=strict_prompt),
            HumanMessage(
                content=(
                    f"Today's date: {datetime.now().strftime('%d/%m/%Y')}\n\n"
                    f"Topic: {query}\n\n"
                    f"sources[]:\n{sources_text}\n\n"
                    "Generate the JSON response with grounded bullets and citations. Ensure ALL citations are valid."
                )
            ),
        ]

        self._jittered_sleep()

        try:
            response = self.llm.invoke(messages).content

            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            article_data = json.loads(response)

            # Validate citations again
            max_source_idx = len(sources)
            for bullet in article_data.get("bullets", []):
                cites = bullet.get("cite", [])
                valid_cites = [c for c in cites if 1 <= c <= max_source_idx]
                bullet["cite"] = valid_cites
                if not valid_cites:
                    bullet["error"] = "MISSING_CITATION"

            # Build links array
            links = [
                {"n": idx, "url": source.get("url", ""), "title": source.get("title", "No title")}
                for idx, source in enumerate(sources, start=1)
            ]
            article_data["links"] = links

            # Normalize tags
            tags = article_data.get("tags", {})
            normalized_tags = {
                "companies": tags.get("companies", tags.get("company", [])),
                "regions": tags.get("regions", tags.get("region", [])),
                "themes": tags.get("themes", tags.get("theme", [])),
            }
            for key in normalized_tags:
                if not isinstance(normalized_tags[key], list):
                    normalized_tags[key] = [normalized_tags[key]] if normalized_tags[key] else []
            article_data["tags"] = normalized_tags

            # Final validation
            quality_check = self._validate_citations(article_data, len(sources))
            article_data["quality_check"] = quality_check

            return article_data
        except Exception as e:
            print(f"Retry error: {e}")
            return {
                "error": "RETRY_FAILED",
                "headline": query,
                "bullets": [],
                "why_it_matters": None,
                "tags": {"companies": [], "regions": [], "themes": []},
                "links": [],
                "quality_check": "FAIL_RETRY",
            }

    def run(self, article: dict) -> dict:
        """Run writer agent on article state."""
        query = article.get("query", "")
        sources = article.get("sources", [])

        article_data = self.write_article(query, sources)

        # Merge into article state
        article.update(article_data)
        return article

