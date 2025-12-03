"""
ICPCompaniesAgent - Identifies target companies (US only) in a specified industry.
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


class ICPCompaniesAgent:
    """
    Identifies target companies (US only) in a specified industry that are likely buyers.
    Focuses on United States only by default.
    """
    
    def __init__(self):
        """Initialize ICP Companies Agent with Groq LLM."""
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
        Generate ICP companies list for the topic.
        
        Args:
            topic: The research topic
            bullets: List of bullet points with citations
            insights: Optional insights from InsightsAgent
            tags: Tags dictionary (companies, regions, themes)
            sources: List of source dictionaries
            region: Geographic region (default "US")
            client: Optional client metadata
        
        Returns:
            Dictionary with companies array and sources
        """
        if not bullets:
            return {
                "companies": [],
                "sources": [],
            }
        
        # Build client context if available
        client_context = ""
        if client:
            client_name = client.get("name", "")
            client_industry = client.get("client_industry", "")
            focus_industry = client.get("focus_industry", "")
            client_context = f"""
CLIENT CONTEXT:
- Client Name: {client_name}
- Client Industry: {client_industry}
- Focus Industry: {focus_industry}
Use this context to identify companies that would be ideal buyers of technology in the {focus_industry} industry.
"""
        
        system_prompt = """You are the ICPCompaniesAgent for the XLR8 Research system.

Your job is to identify target companies in a specified industry that are likely buyers of a given technology, using ONLY the provided data.

CRITICAL RULES:
- You DO NOT fetch new data. You DO NOT browse URLs. You ONLY use the provided bullets, insights, tags, and sources.
- Default to US-only (region="US"). Only include non-US companies when: (1) There are zero clear US candidates AND (2) You clearly indicate "location": "non-US" in the output.
- NEVER invent new companies that are not in the sources. Only output companies that are explicitly mentioned in the provided sources.
- Only output companies that plausibly match the topic's industry (e.g., "construction tech", "solar energy", etc.). Do NOT pull in random companies like Tesla/Xpeng unless the article clearly links them to that specific tech.
- If there is not enough information to confidently recommend more than 1-2 companies, return just those and mention the limitation in why_target. Do NOT hallucinate.

YOUR TASK:
Using ONLY the provided data, produce a structured JSON object with:

{
  "companies": [
    {
      "name": "Company Name",
      "industry": "e.g. General Contractor / Utility / Developer",
      "why_target": "1-2 lines tying this company to the product/tech in a grounded way",
      "approx_size": "enterprise / mid-market / SMB / 'unknown'",
      "location": "City, State or 'US-based' or 'non-US'",
      "source": "url or domain"
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
            region_instruction = "Focus EXCLUSIVELY on US companies. Only include non-US companies if there are zero clear US candidates, and clearly mark them as 'non-US' in location."
        else:
            region_instruction = f"Focus on {region} companies. Only include other regions if there are zero clear {region} candidates."
        
        user_prompt = f"""Identify target companies for the following topic:

{context}
{client_context}
Region: {region}
{region_instruction}

CRITICAL: Only include companies that are explicitly mentioned in the sources. Do NOT invent companies. Only include companies that plausibly match the topic's industry. If insufficient information, return only 1-2 companies and note the limitation in why_target.

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
            if "companies" not in result:
                result["companies"] = []
            if "sources" not in result:
                result["sources"] = []
            
            # Validate each company has required keys
            required_company_keys = ["name", "industry", "why_target", "approx_size", "location", "source"]
            for company in result["companies"]:
                for key in required_company_keys:
                    if key not in company:
                        company[key] = "unknown" if key in ["approx_size", "location"] else ""
            
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
            print(f"[ERROR] Failed to parse ICPCompaniesAgent JSON: {e}")
            if response_text:
                print(f"[DEBUG] Response text: {response_text[:500]}")
            return {
                "error": "ICP_COMPANIES_AGENT_ERROR",
                "message": f"Failed to parse JSON: {str(e)}"
            }
        except Exception as e:
            print(f"[ERROR] ICPCompaniesAgent failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": "ICP_COMPANIES_AGENT_ERROR",
                "message": str(e)
            }

