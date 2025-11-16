"""
Insights Agent - Generates marketing-grade insights from structured article data.
Takes WriterJSONAgent output and produces actionable insights for business development.
"""
import json
import time
import random
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    GROQ_API_KEY,
    LLM_CALL_DELAY_SECONDS,
)


class InsightsAgent:
    """
    Generates high-value, marketing-grade insights from structured article data.
    Only uses grounded data from WriterJSONAgent - no external fetching.
    """
    
    def __init__(self):
        """Initialize Insights Agent with Groq LLM."""
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
    
    def _format_article_state_for_prompt(self, article_state: Dict[str, Any]) -> str:
        """Format article state into a structured prompt."""
        topic = article_state.get("topic", "")
        headline = article_state.get("headline", "")
        bullets = article_state.get("bullets", [])
        why_it_matters = article_state.get("why_it_matters", "")
        tags = article_state.get("tags", {})
        sources = article_state.get("sources", [])
        client = article_state.get("client")  # Optional client metadata
        
        # Format bullets with citations
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
        
        # Format tags
        companies = tags.get("companies", [])
        regions = tags.get("regions", [])
        themes = tags.get("themes", [])
        
        tags_text = f"Companies: {', '.join(companies) if companies else 'None'}\n"
        tags_text += f"Regions: {', '.join(regions) if regions else 'None'}\n"
        tags_text += f"Themes: {', '.join(themes) if themes else 'None'}\n"
        
        # Format client metadata if present
        client_text = ""
        if client:
            client_text = f"""
CLIENT CONTEXT (use for ICP-aware recommendations):
- Name: {client.get('name', 'N/A')}
- Type: {client.get('type', 'N/A')}
- Focus Industry: {client.get('focus_industry', 'N/A')}
- Client Industry: {client.get('client_industry', 'N/A')}
- Target Regions: {', '.join(client.get('target_regions', []))}
- Target Audience: {', '.join(client.get('target_audience', []))}
"""
        
        prompt = f"""TOPIC: {topic}
HEADLINE: {headline}

WHY IT MATTERS: {why_it_matters if why_it_matters else 'Not provided'}

BULLETS (with citations):
{bullets_text}

TAGS:
{tags_text}

SOURCES:
{sources_text}
{client_text}
"""
        return prompt
    
    def generate_insights(self, article_state: Dict[str, Any], include_trend: bool = False) -> Dict[str, Any]:
        """
        Generate marketing-grade insights from article state.
        
        Args:
            article_state: Dictionary containing topic, headline, bullets, tags, sources, etc.
            include_trend: Whether to include trend analysis (if previous window data available)
        
        Returns:
            Dictionary with market_overview, key_segments, key_players, opportunities, risks, recommended_plays, trend
        """
        # Validate required fields
        bullets = article_state.get("bullets")
        if not bullets:
            print(f"[WARNING] No bullets found in article_state for insights generation")
            print(f"[DEBUG] article_state keys: {list(article_state.keys())}")
            return {
                "error": "INSUFFICIENT_DATA",
                "message": "No bullets provided for insights generation"
            }
        
        print(f"[INFO] Generating insights with {len(bullets)} bullets")
        
        # Format prompt
        article_prompt = self._format_article_state_for_prompt(article_state)
        
        # Build system prompt
        system_prompt = """You are the InsightsAgent for the XLR8 Research system.

Your job is to take structured output from WriterJSONAgent and generate high-value, marketing-grade insights that help business development, marketing, and sales teams understand WHAT is happening, WHY it matters, and WHAT they should do next.

You DO NOT fetch new data. You DO NOT browse URLs. You ONLY use the provided input fields.

YOUR TASK:
Using ONLY the provided data, produce a structured JSON object with:
- market_overview: 2-4 sentence summary of market state
- key_segments: 2-6 segments extracted from themes/companies
- key_players: Companies mentioned with their role and signals
- opportunities: Strategic opportunities for marketers/agencies
- risks: Meaningful threats (regulatory, funding, competition, etc.)
- recommended_plays: ICP-aware plays if client context provided, else generalized B2B plays
- trend: Optional, only if requested

All insights MUST be derived from the provided bullets, snippets, tags, and topic — never invent facts, numbers, or claims that are NOT present in the grounded content.

RESPONSE FORMAT:
Return ONLY valid JSON, no explanations or prose:

{
  "market_overview": "2-4 sentence qualitative summary. Identify trajectory: 'growing', 'declining', or 'plateau/mixed signals' based on language in bullets.",
  "key_segments": [
    {"name": "Segment Name", "note": "Brief note with citation [n]"}
  ],
  "key_players": [
    {"name": "Company Name", "role": "Industry/role", "signal": "Key signal from bullets [n]"}
  ],
  "opportunities": [
    {"text": "Opportunity description", "cite": [1, 3]}
  ],
  "risks": [
    {"text": "Risk description", "cite": [2]}
  ],
  "recommended_plays": [
    {
      "play_name": "Play name",
      "channels": ["LinkedIn", "Email"],
      "angle": "Positioning angle with citations [1][3]",
      "evidence": [1, 3]
    }
  ],
  "trend": {
    "momentum": "strong|moderate|weak",
    "signal_basis": "Qualitative basis from bullets [1][3]"
  }
}

IMPORTANT:
- Ground EVERYTHING in bullet citations
- Use citation numbers [n] from bullets
- Do NOT invent KPIs or numbers
- If client context provided, tailor recommended_plays to their ICP
- If no client context, provide 2-4 generalized B2B marketing plays"""
        
        # Add trend instruction if requested
        if include_trend:
            system_prompt += "\n\nInclude trend analysis if previous window data is available, otherwise provide qualitative momentum assessment."
        
        user_prompt = f"""Generate insights from the following article data:

{article_prompt}

Return ONLY the JSON object, no additional text."""
        
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
            
            insights = json.loads(response_text)
            
            # Validate structure
            required_fields = ["market_overview", "key_segments", "key_players", "opportunities", "risks", "recommended_plays"]
            for field in required_fields:
                if field not in insights:
                    print(f"[WARNING] Missing required field '{field}' in insights response")
                    insights[field] = [] if field in ["key_segments", "key_players", "opportunities", "risks", "recommended_plays"] else ""
            
            # Log what we got
            print(f"[INFO] Insights generated successfully. Fields: {list(insights.keys())}")
            print(f"[DEBUG] Market overview present: {bool(insights.get('market_overview'))}")
            print(f"[DEBUG] Key segments count: {len(insights.get('key_segments', []))}")
            print(f"[DEBUG] Key players count: {len(insights.get('key_players', []))}")
            print(f"[DEBUG] Opportunities count: {len(insights.get('opportunities', []))}")
            print(f"[DEBUG] Risks count: {len(insights.get('risks', []))}")
            print(f"[DEBUG] Recommended plays count: {len(insights.get('recommended_plays', []))}")
            
            return insights
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse insights JSON: {e}")
            print(f"[DEBUG] Response text: {response_text[:500]}")
            return {
                "error": "JSON_PARSE_ERROR",
                "message": f"Failed to parse insights: {str(e)}"
            }
        except Exception as e:
            print(f"[ERROR] Insights generation failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": "INSIGHTS_GENERATION_ERROR",
                "message": str(e)
            }
    
    def run(self, article_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run insights generation (LangGraph node interface).
        
        Args:
            article_state: Article state dictionary
        
        Returns:
            Updated article_state with insights added
        """
        print(f"[INFO] InsightsAgent.run() called for topic: {article_state.get('topic', 'unknown')}")
        include_trend = article_state.get("include_trend", False)
        insights = self.generate_insights(article_state, include_trend=include_trend)
        
        if insights:
            print(f"[INFO] Insights generated, type: {type(insights)}, has error: {insights.get('error') if isinstance(insights, dict) else 'N/A'}")
        else:
            print(f"[WARNING] Insights generation returned None/empty")
        
        article_state["insights"] = insights
        return article_state

