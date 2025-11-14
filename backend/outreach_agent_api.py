"""
Outreach Agent API - RAG System Integration
Provides endpoints for interacting with RAG system for outreach analytics.
Uses FAISS vector store + Groq LLM instead of Amazon Bedrock Agent.
"""
import os
import json
from flask import Blueprint, jsonify, request, Response, stream_with_context
from dotenv import load_dotenv
from backend.s3_data_loader import get_all_clients, get_client_data, get_client_metrics
from backend.rag.search import RAGSearch

# Load environment variables
load_dotenv()

outreach_blueprint = Blueprint('outreach', __name__, url_prefix='/api/outreach')

# RAG System Configuration
USE_STREAMING = os.getenv('USE_STREAMING', 'false').lower() == 'true'
FAISS_PERSIST_DIR = os.getenv('FAISS_PERSIST_DIR', 'faiss_store')
KB_FILES = ['kb_outreach_activities.jsonl']  # Knowledge base files from S3

# Initialize RAG Search system (lazy loading)
rag_search = None

def get_rag_search():
    """Get or create RAG Search instance."""
    global rag_search
    if rag_search is None:
        print("[INFO] Initializing RAG Search system...")
        rag_search = RAGSearch(
            persist_dir=FAISS_PERSIST_DIR,
            embedding_model="all-MiniLM-L6-v2",
            kb_files=KB_FILES
        )
    return rag_search


@outreach_blueprint.route('/healthz', methods=['GET'])
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "outreach-agent-rag"}), 200


@outreach_blueprint.route('/rebuild-index', methods=['POST'])
def rebuild_index():
    """
    Rebuild the FAISS vector store index from S3 knowledge base files.
    Useful when knowledge base is updated.
    
    Request body (optional):
    {
        "kb_files": ["kb_outreach_activities.jsonl", "kb_client_metric_summaries.jsonl"]
    }
    
    Response:
    {
        "status": "success",
        "message": "Vector store rebuilt successfully",
        "documents_loaded": 123
    }
    """
    try:
        data = request.get_json(force=True) or {}
        kb_files = data.get('kb_files', KB_FILES)
        
        print(f"[INFO] Rebuilding vector store with files: {kb_files}")
        rag = get_rag_search()
        
        # Rebuild index
        from backend.rag.data_loader import load_all_documents
        docs = load_all_documents(kb_files)
        
        if docs:
            rag.rebuild_index(kb_files)
            return jsonify({
                "status": "success",
                "message": "Vector store rebuilt successfully",
                "documents_loaded": len(docs),
                "kb_files": kb_files
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "No documents loaded from S3",
                "kb_files": kb_files
            }), 400
            
    except Exception as e:
        print(f"[ERROR] Failed to rebuild index: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@outreach_blueprint.route('/clients', methods=['GET'])
def get_clients():
    """
    Get list of all available clients.
    
    Response:
    {
        "clients": [
            {"company_id": "C001", "name": "TechCorp Inc.", ...},
            ...
        ]
    }
    """
    try:
        clients = get_all_clients()
        return jsonify({"clients": clients}), 200
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return jsonify({"error": str(e)}), 500


@outreach_blueprint.route('/clients/<client_id>', methods=['GET'])
def get_client(client_id):
    """
    Get all data for a specific client with optional filters.
    
    Query parameters:
    - channel: Filter activities by channel (Email, LinkedIn, Call, HubSpot)
    - status: Filter activities by status (Success, Pending, Failed)
    - days: Filter activities by last N days (7, 30, etc.)
    
    Response:
    {
        "client_id": "C001",
        "metrics": {...},
        "activities": [...],
        "contacts": [...],
        "campaigns": [...],
        "summary": {...},
        "top_contacts": [...]
    }
    """
    try:
        # Parse filters from query parameters
        filters = {}
        channel = request.args.get('channel')
        status = request.args.get('status')
        days = request.args.get('days', type=int)
        
        if channel:
            filters['channel'] = channel
        if status:
            filters['status'] = status
        if days:
            filters['days'] = days
        
        data = get_client_data(client_id, filters=filters if filters else None)
        if not data.get('metrics'):
            return jsonify({"error": f"Client {client_id} not found"}), 404
        return jsonify(data), 200
    except Exception as e:
        print(f"Error fetching client data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@outreach_blueprint.route('/ask', methods=['POST'])
def ask():
    """
    Non-streaming endpoint for RAG system queries.
    
    Request body:
    {
        "prompt": "Compare LinkedIn vs Email engagement for Innovate Solutions",
        "session_id": "optional-session-id"
    }
    
    Response:
    {
        "session_id": "...",
        "text": "Full response text..."
    }
    """
    try:
        data = request.get_json(force=True) or {}
        prompt = data.get('prompt', '').strip()
        session_id = data.get('session_id') or f"session-{os.urandom(8).hex()}"
        
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400
        
        # Get RAG search instance
        rag = get_rag_search()
        
        # Search and generate response
        print(f"[INFO] Processing query: {prompt[:50]}...")
        response_text = rag.search_and_summarize(prompt, top_k=5)
        
        return jsonify({
            "session_id": session_id,
            "text": response_text
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Unexpected error in /ask: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@outreach_blueprint.route('/ask/stream', methods=['POST'])
def ask_stream():
    """
    Streaming endpoint for RAG system queries (Server-Sent Events).
    Note: Groq doesn't support streaming in the same way, so we simulate it by chunking the response.
    
    Request body:
    {
        "prompt": "Compare LinkedIn vs Email engagement for Innovate Solutions",
        "session_id": "optional-session-id"
    }
    
    Response: Server-Sent Events stream
    """
    if not USE_STREAMING:
        return jsonify({"error": "Streaming not enabled. Set USE_STREAMING=true"}), 403
    
    try:
        data = request.get_json(force=True) or {}
        prompt = data.get('prompt', '').strip()
        session_id = data.get('session_id') or f"session-{os.urandom(8).hex()}"
        
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400
        
        def generate():
            try:
                # Send session_id first
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # Get RAG search instance
                rag = get_rag_search()
                
                # Generate response (non-streaming, but we'll chunk it for SSE)
                print(f"[INFO] Processing streaming query: {prompt[:50]}...")
                response_text = rag.search_and_summarize(prompt, top_k=5)
                
                # Simulate streaming by chunking the response
                chunk_size = 20  # Characters per chunk
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                
                # Send completion
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Unexpected error in /ask/stream: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

