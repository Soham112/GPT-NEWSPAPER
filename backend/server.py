from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from backend.langgraph_agent import MasterAgent
from backend.cost_tracker import cost_tracker
from backend.intent_classifier import detect_query_intent
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
        # New: ICP strategy is opt-in and disabled by default
        include_icp = bool(data.get("include_icp", False))
        
        # Automatic intent detection: if use_case or include_insights are not explicitly provided,
        # detect them from the first topic
        # Note: If client explicitly passes include_insights, we do not override it, even for ICP-related use_cases.
        # This allows advanced users to force insights generation even for ICP queries.
        explicit_use_case = data.get("use_case")
        explicit_include_insights = data.get("include_insights")
        explicit_region = data.get("region")
        # LEADERSHIP_MODE START
        explicit_is_leadership_query = data.get("is_leadership_query")
        # LEADERSHIP_MODE END
        
        # Detect intent if either use_case or include_insights is missing
        if explicit_use_case is None or explicit_include_insights is None:
            # Detect intent from the first topic
            first_topic = topics[0] if topics else ""
            detected_intent = detect_query_intent(first_topic)
            
            # Use detected values if not explicitly provided, otherwise use explicit values
            use_case = explicit_use_case if explicit_use_case is not None else detected_intent.use_case
            include_insights = explicit_include_insights if explicit_include_insights is not None else detected_intent.include_insights
            region = explicit_region if explicit_region is not None else detected_intent.region
            # Leadership flag is always derived from detected intent unless explicitly provided
            is_leadership_query = (
                bool(explicit_is_leadership_query)
                if explicit_is_leadership_query is not None
                else bool(getattr(detected_intent, "is_leadership_query", False))
            )
            company = getattr(detected_intent, "company", None)
        else:
            # Both use_case and include_insights explicitly provided, use them as-is
            use_case = explicit_use_case
            include_insights = explicit_include_insights
            region = explicit_region if explicit_region is not None else "US"
            # When caller fully specifies use_case/include_insights, default leadership flag to False
            is_leadership_query = bool(explicit_is_leadership_query) if explicit_is_leadership_query is not None else False
            company = None
        
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
            include_icp=include_icp,
            use_case=use_case,
            region=region,
            # LEADERSHIP_MODE START
            is_leadership_query=is_leadership_query,
            company=company,
            # LEADERSHIP_MODE END
        )
        
        # Add request metadata
        result["request_id"] = request_id
        
        return jsonify(result), 200
        
    except ValueError as e:
        # Budget exceeded or validation error
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

