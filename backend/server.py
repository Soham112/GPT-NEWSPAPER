from flask import Flask, jsonify, request
from backend.langgraph_agent import MasterAgent
from backend.cost_tracker import cost_tracker
import uuid

backend_app = Flask(__name__)

@backend_app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Running"}), 200

@backend_app.route('/generate_newspaper', methods=['POST'])
def generate_newspaper():
    """
    Legacy endpoint for HTML newspaper generation.
    Now uses JSON-first flow and renders HTML from JSON result.
    """
    data = request.json or {}
    topics = data.get("topics", [])
    layout = data.get("layout", "layout_1.html")
    
    if not topics:
        return jsonify({"error": "topics array is required"}), 400
    
    # Use JSON-first flow
    master_agent = MasterAgent()
    json_result = master_agent.run_json(
        topics=topics,
        domains=None,
        window="week",
        k=5,
        strict=True,
    )
    
    # Generate HTML from JSON (for backward compatibility)
    # This can be enhanced to use the EditorAgent to create HTML
    # For now, return JSON and let frontend render it
    return jsonify({
        "path": None,  # No longer generating HTML file
        "json": json_result,  # Include JSON for frontend rendering
        "layout": layout
    }), 200

@backend_app.route('/research/v1', methods=['POST'])
def research_v1():
    """
    API-first research endpoint that returns JSON.
    
    Request body:
    {
        "topics": ["topic1", "topic2"],
        "domains": ["domain1.com", "domain2.com"],  # optional
        "window": "week",  # "week" or "month", default "week"
        "k": 5,  # number of sources to curate, default 5
        "strict": true  # fail closed on insufficient sources, default true
    }
    
    Response:
    {
        "topics": [...],
        "results": [
            {
                "topic": "...",
                "sources": [{"title": "...", "url": "...", "date": "...", "snippet": "..."}],
                "summary": [{"bullet": "...", "cite": [1, 3]}],
                "links": [{"n": 1, "url": "..."}],
                "headline": "...",
                "why_it_matters": "...",
                "tags": {"company": "...", "region": "...", "theme": "..."}
            }
        ],
        "cost": {"tokens": 1234, "cost": 0.0012}
    }
    """
    try:
        data = request.get_json(force=True) or {}
        
        topics = data.get("topics", [])
        if not topics:
            return jsonify({"error": "topics array is required"}), 400
        
        domains = data.get("domains")
        window = data.get("window", "week")
        k = int(data.get("k", 5))
        strict = data.get("strict", True)
        
        # Generate request ID for cost tracking
        request_id = str(uuid.uuid4())
        cost_tracker.reset_request(request_id)
        
        # Create master agent and run
        master_agent = MasterAgent()
        result = master_agent.run_json(
            topics=topics,
            domains=domains,
            window=window,
            k=k,
            strict=strict,
        )
        
        # Add request metadata
        result["request_id"] = request_id
        
        return jsonify(result), 200
        
    except ValueError as e:
        # Budget exceeded or validation error
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

