from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from backend.langgraph_agent import MasterAgent
from backend.cost_tracker import cost_tracker
import uuid

# Load environment variables BEFORE importing blueprint
load_dotenv()

from backend.outreach_agent_api import outreach_blueprint

backend_app = Flask(__name__)
CORS(backend_app)  # Enable CORS for all routes

# Register Outreach Agent blueprint
backend_app.register_blueprint(outreach_blueprint)

@backend_app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Running"}), 200

@backend_app.route('/healthz', methods=['GET'])
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@backend_app.route('/generate_newspaper', methods=['POST'])
def generate_newspaper():
    """
    Legacy endpoint for HTML newspaper generation.
    Now uses JSON-first flow and renders HTML from JSON result.
    """
    data = request.json or {}
    topics = data.get("topics", [])
    # Layout parameter is deprecated - using unified layout
    layout = data.get("layout", "layout.html")  # Default to unified layout
    
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
        "layout": "layout.html"  # Always use unified layout
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
        client = data.get("client")  # Optional client metadata for ICP-aware insights
        include_insights = data.get("include_insights", True)  # Default to True
        
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
            client=client,
            include_insights=include_insights,
        )
        
        # Add request metadata
        result["request_id"] = request_id
        
        return jsonify(result), 200
        
    except ValueError as e:
        # Budget exceeded or validation error
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

