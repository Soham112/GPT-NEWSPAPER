"""
RAG Search System
Combines vector search with Groq LLM for question answering.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.rag.vectorstore import FaissVectorStore
from backend.rag.data_loader import load_all_documents
from backend.config import GROQ_API_KEY, SUMMARY_MODEL, TEMPERATURE, MAX_TOKENS

load_dotenv()


class RAGSearch:
    def __init__(
        self, 
        persist_dir: str = "faiss_store", 
        embedding_model: str = "all-MiniLM-L6-v2", 
        llm_model: str = None,
        kb_files: Optional[list] = None
    ):
        """
        Initialize RAG search system.
        
        Args:
            persist_dir: Directory for FAISS index persistence
            embedding_model: Sentence transformer model name
            llm_model: Groq LLM model name (defaults to SUMMARY_MODEL from config)
            kb_files: List of JSONL file keys to load (defaults to ['kb_outreach_activities.jsonl'])
        """
        self.persist_dir = persist_dir
        self.vectorstore = FaissVectorStore(persist_dir, embedding_model)
        
        # Load or build vectorstore
        faiss_path = os.path.join(persist_dir, "faiss.index")
        meta_path = os.path.join(persist_dir, "metadata.pkl")
        
        if not (os.path.exists(faiss_path) and os.path.exists(meta_path)):
            print(f"[INFO] Building new vector store from S3 data...")
            if kb_files is None:
                kb_files = ['kb_outreach_activities.jsonl']
            docs = load_all_documents(kb_files)
            if not docs:
                print(f"[WARNING] No documents loaded. Vector store will be empty.")
            else:
                self.vectorstore.build_from_documents(docs)
        else:
            print(f"[INFO] Loading existing vector store...")
            self.vectorstore.load()
        
        # Initialize Groq LLM
        llm_model = llm_model or SUMMARY_MODEL
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=llm_model,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        print(f"[INFO] RAG Search initialized with LLM: {llm_model}")

    def search_and_summarize(self, query: str, top_k: int = 5) -> str:
        """
        Search vector store and generate summary using Groq LLM.
        
        Args:
            query: User query string
            top_k: Number of relevant chunks to retrieve
        
        Returns:
            Generated summary/answer string
        """
        # Search vector store
        results = self.vectorstore.query(query, top_k=top_k)
        
        if not results:
            return "No relevant information found in the knowledge base."
        
        # Extract context from results
        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            text = metadata.get("text", "")
            if text:
                context_parts.append(f"[Source {i}]\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # Generate response using Groq
        system_prompt = """You are an AI Research Assistant for outreach and marketing campaigns. 
Answer questions based ONLY on the provided context from the knowledge base. 
Be concise, factual, and cite sources when relevant.
Format your response with:
- 3-6 bullet points with key insights
- Optional KPIs line: "KPIs: LinkedIn: <n> | Email: <n> | Calls: <n> | HubSpot: <n>"
- Sources line: "Sources: <id1>, <id2>, <id3>"
If the context doesn't contain enough information, say so clearly."""
        
        user_prompt = f"""Context from knowledge base:

{context}

Question: {query}

Answer based on the context above. Format with bullets, KPIs (if available), and Sources:"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"[ERROR] LLM generation failed: {e}")
            return f"Error generating response: {str(e)}"

    def rebuild_index(self, kb_files: Optional[list] = None):
        """
        Rebuild the vector store index from S3 data.
        
        Args:
            kb_files: List of JSONL file keys to load
        """
        if kb_files is None:
            kb_files = ['kb_outreach_activities.jsonl']
        
        print(f"[INFO] Rebuilding vector store from {kb_files}...")
        docs = load_all_documents(kb_files)
        if docs:
            self.vectorstore.build_from_documents(docs)
            print(f"[INFO] Vector store rebuilt successfully.")
        else:
            print(f"[WARNING] No documents loaded. Index not rebuilt.")

