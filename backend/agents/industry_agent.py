"""
IndustryAgent - Provides high-level US industry view for a given topic.
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


class IndustryAgent:
    """
    Provides high-level US industry view for a given topic.
    Focuses on United States only by default.
    """
    
    def __init__(self):
        """Initialize Industry Agent with Groq LLM."""
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
            sources_text += f"[{i}] {title}\n   URL: {url}\n   Snippet: {snippet}\n\n"
        
        # Format insights if available
        insights_text = ""
        if insights and not insights.get("error"):
            market_overview = insights.get("market_overview", "")
            if market_overview:
                insights_text = f"Market Overview: {market_overview}\n"
        
        # Format tags
        companies = tags.get("companies", [])
        regions = tags.get("regions", [])
        themes = tags.get("themes", [])
        
        tags_text = f"Companies: {', '.join(companies) if companies else 'None'}\n"
        tags_text += f"Regions: {', '.join(regions) if regions else 'None'}\n"
        tags_text += f"Themes: {', '.join(themes) if themes else 'None'}\n"
        
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
    ) -> Dict[str, Any]:
        """
        Generate industry insights for the topic.
        
        Args:
            topic: The research topic
            bullets: List of bullet points with citations
            insights: Optional insights from InsightsAgent
            tags: Tags dictionary (companies, regions, themes)
            sources: List of source dictionaries
            region: Geographic region (default "US")
        
        Returns:
            Dictionary with market_insights, trends, opportunities, risks, sources
        """
        if not bullets:
            return {
                "market_insights": [],
                "trends": [],
                "opportunities": [],
                "risks": [],
                "sources": [],
            }
        
        system_prompt = """You are the IndustryAgent for the XLR8 Research system.

Your job is to provide a high-level US industry view for a given topic using ONLY the provided data.

CRITICAL RULES:
- You DO NOT fetch new data. You DO NOT browse URLs. You ONLY use the provided bullets, insights, tags, and sources.
- The region argument is the geographic filter. Default to United States.
- If region is "US" or not provided, focus EXCLUSIVELY on US examples. Only include non-US examples if there are essentially zero US examples in the sources.
- All insights must be grounded in the provided sources - NO HALLUCINATION.

YOUR TASK:
Using ONLY the provided data, produce a structured JSON object with EXACTLY these keys in this order:

{
  "market_insights": ["string"],
  "trends": ["string"],
  "opportunities": ["string"],
  "risks": ["string"],
  "sources": ["url-or-domain-string"]
}

REQUIREMENTS:
- market_insights: 2-5 high-level bullets about the US industry
- trends: 2-5 clearly worded trend bullets
- opportunities: At least 1 item (more if available)
- risks: At least 1 item (more if available)
- sources: Deduplicated list of URLs/domains actually cited in the bullets (extract from provided sources)

RESPONSE FORMAT:
Return ONLY valid JSON, no explanations or prose. The JSON must have exactly these five keys in this order."""
        
        context = self._format_context_for_prompt(topic, bullets, insights, tags, sources)
        
        # Build region-specific instruction
        region_instruction = ""
        if region == "US" or not region:
            region_instruction = "Focus EXCLUSIVELY on United States examples. Ignore non-US examples unless there are essentially zero US examples in the sources."
        else:
            region_instruction = f"Focus on {region} examples. Only include examples from other regions if there are essentially zero {region} examples."
        
        user_prompt = f"""Generate industry insights for the following topic:

{context}

Region: {region}
{region_instruction}

Return ONLY the JSON object with exactly these keys in this order: market_insights, trends, opportunities, risks, sources. No additional text."""
        
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
            
            # Validate schema - must have exactly these keys
            required_fields = ["market_insights", "trends", "opportunities", "risks", "sources"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Ensure all fields are lists
            for field in required_fields:
                if not isinstance(result[field], list):
                    result[field] = []
            
            # Ensure opportunities and risks have at least 1 item
            if not result["opportunities"]:
                result["opportunities"] = ["No specific opportunities identified in sources"]
            if not result["risks"]:
                result["risks"] = ["No specific risks identified in sources"]
            
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
            print(f"[ERROR] Failed to parse IndustryAgent JSON: {e}")
            if response_text:
                print(f"[DEBUG] Response text: {response_text[:500]}")
            return {
                "error": "INDUSTRY_AGENT_ERROR",
                "message": f"Failed to parse JSON: {str(e)}"
            }
        except Exception as e:
            print(f"[ERROR] IndustryAgent failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": "INDUSTRY_AGENT_ERROR",
                "message": str(e)
            }

