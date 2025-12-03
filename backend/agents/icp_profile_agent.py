"""
ICPProfileAgent - Identifies ideal customer profiles and specific leaders at companies.
"""
import json
import time
import random
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from backend.utils.leadership_scraper import fetch_leadership_pages
from backend.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    GROQ_API_KEY,
    LLM_CALL_DELAY_SECONDS,
)


def parse_icp_profile_json(raw: str, llm: ChatGroq) -> Dict[str, Any]:
    """
    Parse ICP profile JSON robustly.

    Strategy:
    1) First try a direct json.loads().
    2) On failure, ask the same LLM to fix the JSON and try json.loads() again.

    Raises:
        Exception if parsing still fails after the repair attempt.
    """
    raw_stripped = (raw or "").strip()

    # First attempt: direct parse
    try:
        return json.loads(raw_stripped)
    except json.JSONDecodeError:
        pass

    # Second attempt: ask LLM to repair the JSON
    fix_system_prompt = (
        "You fix invalid JSON into strictly valid JSON that Python json.loads can parse.\n"
        "- Output ONLY the corrected JSON object.\n"
        "- Do NOT add explanations, comments, or markdown code fences.\n"
        "- Do NOT wrap the JSON in ```json or ```.\n"
        "- Ensure there are no trailing commas and that all strings are properly quoted."
    )

    fix_user_prompt = f"""
The following is intended to be a JSON object, but it is invalid JSON.
Fix it so that it becomes valid JSON that Python's json.loads can parse.
Do not add any explanation or commentary, output only the corrected JSON.

Invalid JSON:
{raw_stripped}
"""

    try:
        messages = [
            SystemMessage(content=fix_system_prompt),
            HumanMessage(content=fix_user_prompt),
        ]
        response = llm.invoke(messages)
        fixed_text = (response.content or "").strip()

        # Strip any code fences if the model added them anyway
        if "```json" in fixed_text:
            fixed_text = fixed_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in fixed_text:
            fixed_text = fixed_text.split("```", 1)[1].split("```", 1)[0].strip()

        return json.loads(fixed_text)
    except Exception as e:
        # Re-raise with context so caller can handle as ICP_PROFILE_AGENT_ERROR
        raise Exception(f"JSON repair failed: {e}") from e


class ICPProfileAgent:
    """
    Identifies ideal customer profiles and specific leaders at those companies.
    Focuses on United States only by default.
    """
    
    def __init__(self):
        """Initialize ICP Profile Agent with Groq LLM."""
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
        # LEADERSHIP_MODE START
        is_leadership_query: bool = False,
        raw_query: Optional[str] = None,
        company_hint: Optional[str] = None,
        # LEADERSHIP_MODE END
    ) -> Dict[str, Any]:
        """
        Generate ICP profiles with leaders for the topic.
        
        Args:
            topic: The research topic
            bullets: List of bullet points with citations
            insights: Optional insights from InsightsAgent
            tags: Tags dictionary (companies, regions, themes)
            sources: List of source dictionaries
            region: Geographic region (default "US")
            client: Optional client metadata
        
        Returns:
            Dictionary with companies array (with icp_titles and leaders) and sources
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
            target_audience = client.get("target_audience", [])
            client_context = f"""
CLIENT CONTEXT:
- Client Name: {client_name}
- Client Industry: {client_industry}
- Focus Industry: {focus_industry}
- Target Audience: {', '.join(target_audience) if target_audience else 'N/A'}
Use this context to identify ICP profiles and leaders who would be interested in buying technology in the {focus_industry} industry.
"""
        
        system_prompt = """You are the ICPProfileAgent for the XLR8 Research system.

Your job is to identify ideal customer profiles and specific leaders at companies responsible for buying the tech, using ONLY the provided data.

CRITICAL RULES:
- You DO NOT fetch new data. You DO NOT browse URLs. You ONLY use the provided bullets, insights, tags, and sources.
- Default to US-based companies/leaders unless region says otherwise.
- CRITICAL: Do NOT make up leader names or titles that are not in the sources. If a source mentions a person and their role, you may include them. If no specific name appears, still return icp_titles but leave leaders as an empty list for that company.
- Titles should be commercially relevant buying roles:
  - Director / VP of Operations
  - Head of Construction Technology / Head of Innovation
  - CRO, VP Sales, CPO, VP Procurement, CTO, CIO, COO, CEO, Founder (only where relevant to buying)
- Avoid repeating generic "ICP Strategy" sections. Focus ONLY on who to target (titles + specific leaders) for outreach.

YOUR TASK:
Using ONLY the provided data, produce a structured JSON object with:

{
  "companies": [
    {
      "name": "Company Name",
      "icp_titles": [
        "Director of Construction Technology",
        "VP Operations",
        "Head of Innovation"
      ],
      "leaders": [
        {
          "name": "Leader Name",
          "title": "Exact title as per article",
          "is_icp_title": true,
          "reason": "Why this person is relevant to buying the tech, grounded in the article",
          "source": "url or domain"
        }
      ]
    }
  ],
  "sources": ["..."]
}

RESPONSE FORMAT (STRICT):
- You MUST output ONLY a valid JSON object that matches the schema above.
- Do NOT wrap the JSON in markdown or backticks.
- Do NOT include any commentary, explanation, or prose before or after the JSON.
- Do NOT include comments inside the JSON.
- Do NOT leave trailing commas.
- If you are unsure about a value, use an empty string, false, or an empty list as appropriate.
- The response MUST be parseable by Python's json.loads() without any preprocessing."""
        
        context = self._format_context_for_prompt(topic, bullets, insights, tags, sources)
        
        # Build region-specific instruction
        region_instruction = ""
        if region == "US" or not region:
            if is_leadership_query:
                # Leadership Mode: allow global leadership information where relevant.
                region_instruction = (
                    "Focus primarily on companies and leaders relevant to the query. "
                    "You may include non-US leaders if that is where the official leadership information is available."
                )
            else:
                region_instruction = "Focus EXCLUSIVELY on US-based companies and leaders. Only include non-US if region explicitly says otherwise."
        else:
            region_instruction = f"Focus on {region}-based companies and leaders."
        
        # LEADERSHIP_MODE START
        if is_leadership_query:
            # Use plain text prompt for leadership mode
            # Use company_hint if available, otherwise try to infer from topic
            target_company = company_hint or topic
            
            user_prompt = f"""You are a strict information extractor.

From the sources below, extract ONLY leadership information for the company "{target_company}":
- CEO, Founder, Co-founder
- CFO, COO, CTO, CRO
- President, VP Operations, Head of Sustainability
- Board Chair and Board Directors

SOURCES:
{context}

Rules:
- Only return people who are clearly associated with "{target_company}".
- Ignore other companies mentioned.
- Return output in this EXACT plain-text format, one per line:

NAME | TITLE

Do NOT add JSON, bullets, explanation, or commentary.
"""
        else:
            user_prompt = f"""Identify ICP profiles and leaders for the following topic:

{context}
{client_context}
Region: {region}
{region_instruction}

CRITICAL: Only include leader names and titles that are explicitly mentioned in the sources. Do NOT invent leader names. If a source mentions a person, include them with their exact title from the article. If no specific names are found, return icp_titles but leave leaders[] empty for that company. Focus ONLY on buying roles and specific leaders - avoid generic ICP strategy boilerplate.

Return ONLY the JSON object, no additional text."""
        # LEADERSHIP_MODE END
        
        response_text = ""
        try:
            self._jittered_sleep()
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = (response.content or "").strip()
            
            if is_leadership_query:
                # Parse plain text response
                leaders = []
                for line in response_text.splitlines():
                    if "|" not in line:
                        continue
                    parts = line.split("|", 1)
                    if len(parts) != 2:
                        continue
                    name = parts[0].strip()
                    title = parts[1].strip()
                    
                    # Basic validation
                    if not name or not title:
                        continue
                    if len(name) > 50 or len(title) > 100: # Sanity check
                        continue
                        
                    leaders.append({
                        "name": name,
                        "title": title,
                        "is_icp_title": True, # Assume extracted leaders are relevant
                        "reason": "Extracted from leadership search",
                        "source": "Extracted from sources" # We don't have exact source attribution per line easily here without more complex logic
                    })
                
                # Deduplicate
                unique_leaders = []
                seen = set()
                for l in leaders:
                    key = (l["name"].lower(), l["title"].lower())
                    if key not in seen:
                        seen.add(key)
                        unique_leaders.append(l)
                leaders = unique_leaders

                if not leaders:
                    print(f"[INFO] No leaders found in LLM text response for '{target_company}'")
                    # We will rely on fallback scraping if enabled later
                
                # Construct result structure manually
                target_company_name = company_hint or (tags.get("companies", [topic])[0] if tags.get("companies") else topic)
                
                result = {
                    "companies": [
                        {
                            "name": target_company_name,
                            "icp_titles": sorted(list({l["title"] for l in leaders})),
                            "leaders": leaders,
                        }
                    ],
                    "sources": [] # Will be populated below
                }
                
            else:
                # Standard JSON parsing for non-leadership queries
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in response_text:
                    response_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                
                # Robust JSON parsing with repair attempt
                result = parse_icp_profile_json(response_text, self.llm)
            
            # Common post-processing
            
            # Validate structure
            if "companies" not in result:
                result["companies"] = []
            if "sources" not in result:
                result["sources"] = []
            
            # Ensure each company has required fields and validate leaders
            for company in result["companies"]:
                if "icp_titles" not in company:
                    company["icp_titles"] = []
                if "leaders" not in company:
                    company["leaders"] = []
                
                # Validate each leader has required keys
                for leader in company["leaders"]:
                    required_leader_keys = ["name", "title", "is_icp_title", "reason", "source"]
                    for key in required_leader_keys:
                        if key not in leader:
                            if key == "is_icp_title":
                                leader[key] = True
                            else:
                                leader[key] = ""

            # LEADERSHIP_MODE START
            # Leadership Mode: if the LLM could not confidently identify named leaders,
            # fall back to conservative HTML scraping of official leadership pages.
            if is_leadership_query:
                companies_list = result.get("companies") or []
                has_named_leaders = any(
                    (co.get("leaders") for co in companies_list if isinstance(co.get("leaders"), list))
                )
                all_leaders_empty = True
                for co in companies_list:
                    leaders_list = co.get("leaders") or []
                    if any((l.get("name") or "").strip() for l in leaders_list):
                        all_leaders_empty = False
                        break

                if companies_list and all_leaders_empty:
                    # Attempt fallback scraping
                    primary_company_name = (
                        company_hint
                        or companies_list[0].get("name")
                        or tags.get("companies", [None])[0]
                        if isinstance(tags.get("companies"), list)
                        else tags.get("companies")
                    )
                    if not primary_company_name:
                        primary_company_name = topic or (raw_query or "")

                    if primary_company_name:
                        try:
                            print(
                                f"[INFO] ICPProfileAgent leadership fallback scraping for company '{primary_company_name}'"
                            )
                            fallback = fetch_leadership_pages(primary_company_name)
                            scraped_leaders = fallback.get("leaders", [])

                            if scraped_leaders:
                                buying_roles = [
                                    "ceo",
                                    "chief executive officer",
                                    "cfo",
                                    "chief financial officer",
                                    "coo",
                                    "chief operating officer",
                                    "cto",
                                    "chief technology officer",
                                    "cio",
                                    "chief information officer",
                                    "cro",
                                    "chief revenue officer",
                                    "vp operations",
                                    "vp of operations",
                                    "vp procurement",
                                    "vp of procurement",
                                    "head of procurement",
                                    "head of operations",
                                    "head of sustainability",
                                ]

                                def _is_icp_title_from_title(title: str) -> bool:
                                    t = (title or "").lower()
                                    return any(br in t for br in buying_roles)

                                # Attach scraped leaders to the first company (primary entity)
                                first_company = companies_list[0]
                                existing_leaders = first_company.get("leaders") or []
                                seen_pairs = {
                                    (
                                        (l.get("name") or "").strip().lower(),
                                        (l.get("title") or "").strip().lower(),
                                    )
                                    for l in existing_leaders
                                }

                                for sl in scraped_leaders:
                                    name = (sl.get("name") or "").strip()
                                    title = (sl.get("title") or "").strip()
                                    source_url = sl.get("source") or ""
                                    if not name or not title:
                                        continue

                                    key = (name.lower(), title.lower())
                                    if key in seen_pairs:
                                        continue
                                    seen_pairs.add(key)

                                    leader_obj = {
                                        "name": name,
                                        "title": title,
                                        "is_icp_title": _is_icp_title_from_title(title),
                                        "reason": "Leadership role inferred from official leadership page.",
                                        "source": source_url,
                                    }
                                    existing_leaders.append(leader_obj)

                                first_company["leaders"] = existing_leaders
                        except Exception as e:
                            print(f"[ERROR] ICPProfileAgent leadership fallback scraping failed: {e}")
            # LEADERSHIP_MODE END
            
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
            
        except Exception as e:
            # Any exception here means JSON parsing or validation failed even after repair
            print(f"[ERROR] ICPProfileAgent failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": "ICP_PROFILE_AGENT_ERROR",
                "message": f"Failed to parse JSON even after repair: {str(e)}"
            }

