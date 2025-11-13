"""
Outreach Agent API - Amazon Bedrock Agent Integration
Provides endpoints for interacting with Bedrock Agent for outreach analytics.
"""
import os
import json
import base64
from flask import Blueprint, jsonify, request, Response, stream_with_context
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

outreach_blueprint = Blueprint('outreach', __name__, url_prefix='/api/outreach')

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_OUTREACH_AGENT_ID = os.getenv('BEDROCK_OUTREACH_AGENT_ID')
BEDROCK_OUTREACH_ALIAS = os.getenv('BEDROCK_OUTREACH_ALIAS', 'TSTALIASID')
USE_STREAMING = os.getenv('USE_STREAMING', 'false').lower() == 'true'

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = None

def get_bedrock_client():
    """Get or create Bedrock Agent Runtime client."""
    global bedrock_agent_runtime
    if bedrock_agent_runtime is None:
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=AWS_REGION
        )
    return bedrock_agent_runtime


@outreach_blueprint.route('/healthz', methods=['GET'])
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "outreach-agent"}), 200


@outreach_blueprint.route('/ask', methods=['POST'])
def ask():
    """
    Non-streaming endpoint for Bedrock Agent queries.
    
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
        
        if not BEDROCK_OUTREACH_AGENT_ID:
            return jsonify({"error": "BEDROCK_OUTREACH_AGENT_ID not configured"}), 500
        
        client = get_bedrock_client()
        
        # Invoke Bedrock Agent - returns an event stream
        response = client.invoke_agent(
            agentId=BEDROCK_OUTREACH_AGENT_ID,
            agentAliasId=BEDROCK_OUTREACH_ALIAS,
            sessionId=session_id,
            inputText=prompt
        )
        
        # Collect response chunks from event stream
        # invoke_agent returns a dict with 'completion' key containing an iterable event stream
        text_parts = []
        event_count = 0
        
        try:
            # The 'completion' is an iterable event stream
            completion_stream = response.get('completion', [])
            print(f"DEBUG: Starting to process event stream. Type: {type(completion_stream)}")
            
            for event in completion_stream:
                event_count += 1
                event_keys = list(event.keys()) if isinstance(event, dict) else []
                print(f"DEBUG: Event {event_count} - Keys: {event_keys}")
                
                # Check for chunk event
                if 'chunk' in event:
                    chunk_data = event['chunk']
                    chunk_bytes = chunk_data.get('bytes') if isinstance(chunk_data, dict) else None
                    if chunk_bytes:
                        try:
                            # The bytes field is already a bytes object, not base64-encoded
                            if isinstance(chunk_bytes, bytes):
                                chunk_text = chunk_bytes.decode('utf-8')
                            elif isinstance(chunk_bytes, str):
                                # If it's a string, try base64 decode (with padding fix)
                                missing_padding = len(chunk_bytes) % 4
                                if missing_padding:
                                    chunk_bytes += '=' * (4 - missing_padding)
                                decoded_bytes = base64.b64decode(chunk_bytes)
                                chunk_text = decoded_bytes.decode('utf-8')
                            else:
                                raise ValueError(f"Unexpected bytes type: {type(chunk_bytes)}")
                            
                            text_parts.append(chunk_text)
                            print(f"DEBUG: Decoded chunk ({len(chunk_text)} chars): {chunk_text[:50]}...")
                        except Exception as e:
                            print(f"Error decoding chunk: {e}")
                            print(f"  Chunk bytes type: {type(chunk_bytes)}, length: {len(chunk_bytes) if chunk_bytes else 0}")
                            continue
                    else:
                        print(f"DEBUG: Chunk event has no 'bytes' field")
                # Log other event types for debugging
                elif 'trace' in event:
                    trace_type = event.get('trace', {}).get('type', 'unknown') if isinstance(event.get('trace'), dict) else 'unknown'
                    print(f"DEBUG: Trace event received: {trace_type}")
                elif 'returnControl' in event:
                    print(f"DEBUG: ReturnControl event received")
                else:
                    # Log unknown event types
                    print(f"DEBUG: Unknown event type with keys: {event_keys}")
        except Exception as e:
            print(f"Error iterating event stream: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        full_text = ''.join(text_parts)
        
        # Log for debugging
        print(f"DEBUG: Processed {event_count} events, extracted {len(text_parts)} chunks, total text length: {len(full_text)}")
        if not full_text:
            print(f"WARNING: Empty response from Bedrock Agent.")
            print(f"Response type: {type(response)}, Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
            print(f"Session ID: {session_id}, Prompt: {prompt[:50]}...")
        
        return jsonify({
            "session_id": session_id,
            "text": full_text
        }), 200
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"Bedrock ClientError: {error_code} - {error_msg}")
        return jsonify({
            "error": f"AWS Bedrock error: {error_code}",
            "message": error_msg
        }), 500
    except Exception as e:
        print(f"Unexpected error in /ask: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@outreach_blueprint.route('/ask/stream', methods=['POST'])
def ask_stream():
    """
    Streaming endpoint for Bedrock Agent queries (Server-Sent Events).
    
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
        
        if not BEDROCK_OUTREACH_AGENT_ID:
            return jsonify({"error": "BEDROCK_OUTREACH_AGENT_ID not configured"}), 500
        
        client = get_bedrock_client()
        
        def generate():
            try:
                # Send session_id first
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # Invoke Bedrock Agent
                response = client.invoke_agent(
                    agentId=BEDROCK_OUTREACH_AGENT_ID,
                    agentAliasId=BEDROCK_OUTREACH_ALIAS,
                    sessionId=session_id,
                    inputText=prompt
                )
                
                # Stream chunks
                for event in response.get('completion', []):
                    if 'chunk' in event:
                        chunk_bytes = event['chunk']['bytes']
                        try:
                            chunk_text = base64.b64decode(chunk_bytes).decode('utf-8')
                            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text})}\n\n"
                        except Exception as e:
                            # Handle decoding errors gracefully
                            yield f"data: {json.dumps({'type': 'error', 'error': f'Decoding error: {str(e)}'})}\n\n"
                
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
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        return jsonify({
            "error": f"AWS Bedrock error: {error_code}",
            "message": error_msg
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

