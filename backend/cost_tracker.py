"""
Cost tracking and budget guardrails.
"""
from typing import Dict, Any
from backend.config import ENABLE_COST_TRACKING, MAX_COST_PER_REQUEST

# Rough cost estimates (per 1K tokens)
COST_PER_1K_TOKENS = {
    "llama-3.1-8b-instant": 0.0001,  # $0.10 per 1M tokens
    "llama-3.3-70b-versatile": 0.0007,  # $0.70 per 1M tokens
    "compound-mini": 0.0001,
    # Legacy support (with groq/ prefix)
    "groq/llama-3.1-8b-instant": 0.0001,
    "groq/llama-3.3-70b-versatile": 0.0007,
    "groq/compound-mini": 0.0001,
}


class CostTracker:
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self.request_tokens = {}
        self.request_costs = {}

    def track_call(self, model: str, tokens_used: int, request_id: str = "default"):
        """Track LLM call cost."""
        if not ENABLE_COST_TRACKING:
            return
        
        cost_per_1k = COST_PER_1K_TOKENS.get(model, 0.0001)
        cost = (tokens_used / 1000) * cost_per_1k
        
        self.total_tokens += tokens_used
        self.total_cost += cost
        
        if request_id not in self.request_tokens:
            self.request_tokens[request_id] = 0
            self.request_costs[request_id] = 0.0
        
        self.request_tokens[request_id] += tokens_used
        self.request_costs[request_id] += cost
        
        # Check budget guardrail
        if self.request_costs[request_id] > MAX_COST_PER_REQUEST:
            raise ValueError(
                f"Budget exceeded for request {request_id}: "
                f"${self.request_costs[request_id]:.4f} > ${MAX_COST_PER_REQUEST}"
            )

    def get_request_summary(self, request_id: str = "default") -> Dict[str, Any]:
        """Get cost summary for a request."""
        return {
            "tokens": self.request_tokens.get(request_id, 0),
            "cost": self.request_costs.get(request_id, 0.0),
            "model_breakdown": {},  # Could track per-model
        }

    def reset_request(self, request_id: str = "default"):
        """Reset tracking for a request."""
        self.request_tokens.pop(request_id, None)
        self.request_costs.pop(request_id, None)


# Global tracker instance
cost_tracker = CostTracker()

