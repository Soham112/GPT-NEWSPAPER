"""
FAISS Vector Store for RAG System
Handles vector storage, indexing, and similarity search.
"""
import os
import faiss
import numpy as np
import pickle
from typing import List, Any, Dict
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from backend.rag.embedding import EmbeddingPipeline


class FaissVectorStore:
    def __init__(
        self, 
        persist_dir: str = "faiss_store", 
        embedding_model: str = "all-MiniLM-L6-v2", 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ):
        """
        Initialize FAISS vector store.
        
        Args:
            persist_dir: Directory to persist/load index
            embedding_model: Sentence transformer model name
            chunk_size: Chunk size for documents
            chunk_overlap: Overlap between chunks
        """
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.index = None
        self.metadata = []
        self.embedding_model = embedding_model
        self.model = SentenceTransformer(embedding_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        print(f"[INFO] Initialized FAISS vector store with model: {embedding_model}")

    def build_from_documents(self, documents: List[Document]):
        """
        Build vector store from documents.
        
        Args:
            documents: List of LangChain Document objects
        """
        print(f"[INFO] Building vector store from {len(documents)} documents...")
        emb_pipe = EmbeddingPipeline(
            model_name=self.embedding_model, 
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        chunks = emb_pipe.chunk_documents(documents)
        embeddings = emb_pipe.embed_chunks(chunks)
        
        # Store metadata for each chunk
        metadatas = []
        for chunk in chunks:
            meta = chunk.metadata.copy()
            meta['text'] = chunk.page_content
            metadatas.append(meta)
        
        self.add_embeddings(np.array(embeddings).astype('float32'), metadatas)
        self.save()
        print(f"[INFO] Vector store built and saved to {self.persist_dir}")

    def add_embeddings(self, embeddings: np.ndarray, metadatas: List[Dict] = None):
        """
        Add embeddings to the index.
        
        Args:
            embeddings: Numpy array of embeddings
            metadatas: List of metadata dictionaries
        """
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
        
        self.index.add(embeddings)
        if metadatas:
            self.metadata.extend(metadatas)
        print(f"[INFO] Added {embeddings.shape[0]} vectors to FAISS index.")

    def save(self):
        """Save index and metadata to disk."""
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        faiss.write_index(self.index, faiss_path)
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        print(f"[INFO] Saved FAISS index and metadata to {self.persist_dir}")

    def load(self):
        """Load index and metadata from disk."""
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        
        if not (os.path.exists(faiss_path) and os.path.exists(meta_path)):
            print(f"[WARNING] Index files not found at {self.persist_dir}")
            return False
        
        self.index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        print(f"[INFO] Loaded FAISS index and metadata from {self.persist_dir}")
        return True

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
        
        Returns:
            List of result dictionaries with index, distance, and metadata
        """
        if self.index is None:
            return []
        
        D, I = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx].copy()
                meta['distance'] = float(dist)
                results.append({"index": int(idx), "distance": float(dist), "metadata": meta})
        return results

    def query(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """
        Query the vector store with text.
        
        Args:
            query_text: Query text string
            top_k: Number of results to return
        
        Returns:
            List of result dictionaries
        """
        print(f"[INFO] Querying vector store for: '{query_text[:50]}...'")
        query_emb = self.model.encode([query_text]).astype('float32')
        return self.search(query_emb, top_k=top_k)

