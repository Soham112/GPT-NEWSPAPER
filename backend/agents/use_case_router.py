"""
UseCaseRouterAgent - Routes to specific use case agents based on use_case parameter.
"""
from typing import Dict, Any, List, Optional
from .industry_agent import IndustryAgent
from .funding_agent import FundingAgent
from .icp_companies_agent import ICPCompaniesAgent
from .icp_profile_agent import ICPProfileAgent


class UseCaseRouterAgent:
    """
    Routes to specific use case agents based on use_case value.
    Runs after InsightsAgent in the JSON flow.
    """
    
    def __init__(self):
        """Initialize the router with child agents."""
        self.industry_agent = IndustryAgent()
        self.funding_agent = FundingAgent()
        self.icp_companies_agent = ICPCompaniesAgent()
        self.icp_profile_agent = ICPProfileAgent()
    
    def run(
        self,
        use_case: str,
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
        Route to the appropriate use case agent.
        
        Args:
            use_case: One of "industry", "funding", "icp_companies", "icp_profiles"
            topic: The research topic
            bullets: List of bullet points with citations
            insights: Optional insights from InsightsAgent
            tags: Tags dictionary (companies, regions, themes)
            sources: List of source dictionaries
            region: Geographic region (default "US")
            client: Optional client metadata
        
        Returns:
            Dictionary with use case specific output
        """
        if not use_case:
            return {}
        
        try:
            if use_case == "industry":
                return self.industry_agent.run(
                    topic=topic,
                    bullets=bullets,
                    insights=insights,
                    tags=tags,
                    sources=sources,
                    region=region,
                )
            elif use_case == "funding":
                return self.funding_agent.run(
                    topic=topic,
                    bullets=bullets,
                    insights=insights,
                    tags=tags,
                    sources=sources,
                    region=region,
                    client=client,
                )
            elif use_case == "icp_companies":
                return self.icp_companies_agent.run(
                    topic=topic,
                    bullets=bullets,
                    insights=insights,
                    tags=tags,
                    sources=sources,
                    region=region,
                    client=client,
                )
            elif use_case == "icp_profiles":
                return self.icp_profile_agent.run(
                    topic=topic,
                    bullets=bullets,
                    insights=insights,
                    tags=tags,
                    sources=sources,
                    region=region,
                    client=client,
                    # LEADERSHIP_MODE START
                    is_leadership_query=is_leadership_query,
                    raw_query=raw_query,
                    company_hint=company_hint,
                    # LEADERSHIP_MODE END
                )
            else:
                # Unknown use case, return empty dict
                return {}
        except Exception as e:
            print(f"[ERROR] UseCaseRouterAgent failed for use_case '{use_case}': {e}")
            import traceback
            traceback.print_exc()
            return {"error": "USE_CASE_ROUTER_ERROR", "message": str(e)}

