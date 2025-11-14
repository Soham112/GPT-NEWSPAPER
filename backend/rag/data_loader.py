"""
Data Loader for RAG System
Loads JSONL files from S3 and converts to LangChain document structure.
"""
import os
import json
from typing import List, Any
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
from langchain_core.documents import Document

load_dotenv()

# S3 Configuration
S3_BUCKET = os.getenv('S3_BUCKET', 'project-xlr8')
S3_OUTREACH_PREFIX = os.getenv('S3_OUTREACH_PREFIX', 'outreach-agent/')

# Initialize S3 client
s3_client = None

def get_s3_client():
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client


def load_jsonl_from_s3(file_key: str) -> List[Document]:
    """
    Load a JSONL file from S3 and convert to LangChain documents.
    
    Args:
        file_key: S3 key (e.g., 'kb_outreach_activities.jsonl')
    
    Returns:
        List of LangChain Document objects
    """
    try:
        client = get_s3_client()
        full_key = f"{S3_OUTREACH_PREFIX}{file_key}"
        
        print(f"[DEBUG] Loading JSONL from S3: s3://{S3_BUCKET}/{full_key}")
        response = client.get_object(Bucket=S3_BUCKET, Key=full_key)
        content = response['Body'].read().decode('utf-8')
        
        documents = []
        for line_num, line in enumerate(content.strip().split('\n'), 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # Extract text content - handle various JSONL structures
                # Try common fields: text, content, summary, description, or use entire JSON as text
                text = (
                    data.get('text', '') or 
                    data.get('content', '') or 
                    data.get('summary', '') or 
                    data.get('description', '') or
                    data.get('activity_summary', '') or
                    json.dumps(data, ensure_ascii=False)
                )
                
                # Preserve all metadata except text fields
                metadata = {k: v for k, v in data.items() if k not in ['text', 'content', 'summary', 'description', 'activity_summary']}
                metadata['source'] = file_key
                metadata['line_number'] = line_num
                
                # Only add if we have actual text content
                if text.strip():
                    documents.append(Document(page_content=text, metadata=metadata))
                    
            except json.JSONDecodeError as e:
                print(f"[WARNING] Failed to parse line {line_num} in {file_key}: {e}")
                continue
        
        print(f"[INFO] Loaded {len(documents)} documents from {file_key}")
        return documents
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            print(f"[ERROR] File not found in S3: s3://{S3_BUCKET}/{S3_OUTREACH_PREFIX}{file_key}")
        else:
            print(f"[ERROR] Failed to load {file_key} from S3: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error loading {file_key}: {e}")
        import traceback
        traceback.print_exc()
        return []


def load_all_documents(file_keys: List[str] = None) -> List[Document]:
    """
    Load all specified JSONL files from S3.
    If no keys provided, loads default knowledge base files.
    
    Args:
        file_keys: List of S3 file keys (e.g., ['kb_outreach_activities.jsonl'])
    
    Returns:
        List of LangChain Document objects
    """
    if file_keys is None:
        # Default knowledge base files
        file_keys = ['kb_outreach_activities.jsonl']
    
    all_documents = []
    for file_key in file_keys:
        docs = load_jsonl_from_s3(file_key)
        all_documents.extend(docs)
    
    print(f"[INFO] Total loaded documents: {len(all_documents)}")
    return all_documents

