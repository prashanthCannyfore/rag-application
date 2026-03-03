"""
Embeddings service for semantic search
"""
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class EmbeddingsService:
    """Service for generating and managing embeddings"""
    
    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY must be set in .env")
        
        # Initialize embedding model
        # Use models/gemini-embedding-001 for Google Generative AI
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=GOOGLE_API_KEY
        )
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        return self.embedding_model.embed_query(text)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return self.embedding_model.embed_documents(texts)
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query"""
        return self.embed_text(query)
    
    def get_embedding_dimension(self) -> int:
        """Return embedding vector dimension"""
        # models/gemini-embedding-001 produces 3072-dimensional vectors
        return 3072
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def calculate_token_cost(self, texts: List[str]) -> Dict[str, float]:
        """Estimate token usage and cost for embeddings"""
        # Rough estimate: 1 token ≈ 4 characters
        total_chars = sum(len(text) for text in texts)
        total_tokens = total_chars // 4
        
        # Gemini embedding pricing (approximate)
        cost_per_million = 0.00025  # $0.25 per million tokens
        
        return {
            "total_tokens": total_tokens,
            "estimated_cost": (total_tokens / 1_000_000) * cost_per_million
        }

# Singleton instance
embeddings_service = EmbeddingsService()