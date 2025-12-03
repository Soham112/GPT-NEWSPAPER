"""
FundingAgent - Provides US-only view of recent funding and company-level strategic context.
"""
import json
import time
import random
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from backend.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    GROQ_API_KEY,
    LLM_CALL_DELAY_SECONDS,
)


class FundingAgent:
    """
    Provides US-only view of recent funding and company-level strategic context.
    Focuses on United States companies and funding events.
    """
    
    def __init__(self):
        """Initialize Funding Agent with Groq LLM."""
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
    
    def _format_context_for_prompt(
        self,
        topic: str,
        bullets: List[Dict[str, Any]],
        insights: Optional[Dict[str, Any]],
        tags: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> str:
        """Format context data for the prompt."""
        # Format bullets
        bullets_text = ""
        for i, bullet in enumerate(bullets, 1):
            text = bullet.get("text", bullet.get("bullet", ""))
            cites = bullet.get("cite", [])
            cite_str = ", ".join([f"[{c}]" for c in cites]) if cites else ""
            bullets_text += f"{i}. {text} {cite_str}\n"
        
        # Format sources
        sources_text = ""
        for i, source in enumerate(sources, 1):
            title = source.get("title", "")
            url = source.get("url", "")
            snippet = source.get("snippet", source.get("description", ""))
            date = source.get("date", "")
            sources_text += f"[{i}] {title}\n   URL: {url}\n   Snippet: {snippet}\n   Date: {date}\n\n"
        
        # Format insights if available
        insights_text = ""
        if insights and not insights.get("error"):
            key_players = insights.get("key_players", [])
            if key_players:
                insights_text = "Key Players:\n"
                for player in key_players:
                    name = player.get("name", "")
                    role = player.get("role", "")
                    signal = player.get("signal", "")
                    insights_text += f"- {name} ({role}): {signal}\n"
        
        # Format tags
        companies = tags.get("companies", [])
        regions = tags.get("regions", [])
        
        tags_text = f"Companies: {', '.join(companies) if companies else 'None'}\n"
        tags_text += f"Regions: {', '.join(regions) if regions else 'None'}\n"
        
        return f"""TOPIC: {topic}

BULLETS (with citations):
{bullets_text}

INSIGHTS:
{insights_text}

TAGS:
{tags_text}

SOURCES:
{sources_text}"""
    
    def run(
        self,
        topic: str,
        bullets: List[Dict[str, Any]],
        insights: Optional[Dict[str, Any]],
        tags: Dict[str, Any],
        sources: List[Dict[str, Any]],
        region: str = "US",
        client: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate funding insights for the topic.
        
        Args:
            topic: The research topic
            bullets: List of bullet points with citations
            insights: Optional insights from InsightsAgent
            tags: Tags dictionary (companies, regions, themes)
            sources: List of source dictionaries
            region: Geographic region (default "US")
            client: Optional client metadata
        
        Returns:
            Dictionary with strategic_objectives, recent_funding, financial_performance, sources
        """
        if not bullets:
            return {
                "strategic_objectives": [],
                "recent_funding": [],
                "financial_performance": [],
                "sources": [],
            }
        
        system_prompt = """You are the FundingAgent for the XLR8 Research system.

Your job is to provide a US-only view of recent funding and company-level strategic context using ONLY the provided data.

CRITICAL RULES:
- You DO NOT fetch new data. You DO NOT browse URLs. You ONLY use the provided bullets, insights, tags, and sources.
- US-only focus by default (respect region if provided). Only include non-US companies if there are essentially zero US examples.
- Only describe funding events that are clearly in the last ~6-12 months. If the topic mentions a timeframe (e.g., "last 90 days"), honor that. If no timeframe is derivable, prefer the most recent events in the sources.
- NEVER invent round names, amounts, investors, or dates if not present in the sources. If missing, use "unknown" or "undisclosed" or "not specified".
- Do NOT invent precise ownership percentages. Use narrative description only if specific % is not available.

YOUR TASK:
Using ONLY the provided data, produce a structured JSON object with:

{
  "strategic_objectives": [
    "Short bullet describing strategic objectives for the segment or key companies"
  ],
  "recent_funding": [
    {
      "company": "Company Name",
      "round": "Seed / Series A / Series B / etc. or 'unknown'",
      "amount": "e.g. '$15M' or 'undisclosed'",
      "date": "YYYY-MM or 'unknown'",
      "investors": ["VC name(s) or empty"],
      "type": "VC / PE / angel / strategic / family office / other / 'unknown'",
      "reason": "Short explanation inferred from the article",
      "source": "url or domain"
    }
  ],
  "financial_performance": [
    {
      "company": "Company Name",
      "ownership_split": "Narrative description only, no fabricated specific % if not available",
      "notes": "Any performance detail that IS in the sources"
    }
  ],
  "sources": ["..."]
}

RESPONSE FORMAT:
Return ONLY valid JSON, no explanations or prose."""
        
        context = self._format_context_for_prompt(topic, bullets, insights, tags, sources)
        
        # Build region-specific instruction
        region_instruction = ""
        if region == "US" or not region:
            region_instruction = "Focus EXCLUSIVELY on US companies and US funding events. Only include non-US if there are essentially zero US examples."
        else:
            region_instruction = f"Focus on {region} companies and funding events. Only include other regions if there are essentially zero {region} examples."
        
        # Check topic for timeframe hints
        timeframe_hint = ""
        topic_lower = topic.lower()
        if "90 days" in topic_lower or "last 90 days" in topic_lower:
            timeframe_hint = "Focus on funding events in the last 90 days."
        elif "6 months" in topic_lower or "last 6 months" in topic_lower:
            timeframe_hint = "Focus on funding events in the last 6 months."
        elif "12 months" in topic_lower or "last 12 months" in topic_lower or "year" in topic_lower:
            timeframe_hint = "Focus on funding events in the last 12 months."
        else:
            timeframe_hint = "Focus on the most recent funding events (last 6-12 months) from the sources."
        
        user_prompt = f"""Generate funding insights for the following topic:

{context}

Region: {region}
{region_instruction}
{timeframe_hint}

CRITICAL: Only include funding details that are explicitly stated in the sources. Use "unknown" or "undisclosed" for any missing information. Do NOT invent round names, amounts, investors, or dates.

Return ONLY the JSON object, no additional text."""
        
        response_text = ""
        try:
            self._jittered_sleep()
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Validate structure
            required_fields = ["strategic_objectives", "recent_funding", "financial_performance", "sources"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Ensure all fields are lists
            for field in required_fields:
                if not isinstance(result[field], list):
                    result[field] = []
            
            # Validate recent_funding entries have required keys
            for funding in result["recent_funding"]:
                required_funding_keys = ["company", "round", "amount", "date", "investors", "type", "reason", "source"]
                for key in required_funding_keys:
                    if key not in funding:
                        funding[key] = "unknown" if key in ["round", "amount", "date", "type"] else ([] if key == "investors" else "")
            
            # Extract and deduplicate sources from provided sources list
            source_urls = []
            seen_sources = set()
            for source in sources:
                url = source.get("url", "")
                if url:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        domain = parsed.netloc
                        source_key = domain if domain else url
                        if source_key not in seen_sources:
                            seen_sources.add(source_key)
                            source_urls.append(source_key)
                    except:
                        if url not in seen_sources:
                            seen_sources.add(url)
                            source_urls.append(url)
            
            # Use provided sources if result sources are empty or invalid
            if not result["sources"] or not isinstance(result["sources"], list):
                result["sources"] = source_urls
            else:
                # Deduplicate result sources
                result["sources"] = list(dict.fromkeys(result["sources"]))
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse FundingAgent JSON: {e}")
            if response_text:
                print(f"[DEBUG] Response text: {response_text[:500]}")
            return {
                "error": "FUNDING_AGENT_ERROR",
                "message": f"Failed to parse JSON: {str(e)}"
            }
        except Exception as e:
            print(f"[ERROR] FundingAgent failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": "FUNDING_AGENT_ERROR",
                "message": str(e)
            }

