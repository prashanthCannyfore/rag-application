"""
Vector database service using Supabase pgvector
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from app.services.embeddings_service import embeddings_service

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
VECTOR_TABLE = os.getenv("VECTOR_TABLE_NAME", "document_embeddings")

class VectorDBService:
    """Service for managing vector embeddings in Supabase"""
    
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            self.supabase = None
    
    def create_tables(self):
        """Create vector database tables"""
        if not self.supabase:
            print("Supabase not configured, skipping table creation")
            return
        
        sql = f"""
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create document embeddings table
        CREATE TABLE IF NOT EXISTS {VECTOR_TABLE} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{{}}',
            embedding VECTOR(768),
            document_id VARCHAR(255),
            chunk_index INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create index for vector similarity search
        CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE}_embedding 
        ON {VECTOR_TABLE} USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        
        -- Create index for document lookup
        CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE}_document_id 
        ON {VECTOR_TABLE}(document_id);
        """
        
        try:
            self.supabase.rpc("run_sql_query", {"sql_text": sql}).execute()
            print(f"✓ Table {VECTOR_TABLE} created successfully")
        except Exception as e:
            print(f"Note: {e}")
            print("Run SQL manually in Supabase SQL Editor if needed")
    
    async def add_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict = None,
        chunk_index: int = 0
    ) -> Dict:
        """Add a document chunk with embedding"""
        if not self.supabase:
            # Demo mode - return mock data
            return {
                "id": "demo-id",
                "content": content[:100],
                "document_id": document_id,
                "chunk_index": chunk_index
            }
        
        # Generate embedding
        embedding = embeddings_service.embed_text(content)
        
        # Store in database
        data = {
            "content": content,
            "metadata": metadata or {},
            "embedding": embedding,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "created_at": datetime.now().isoformat()
        }
        
        result = self.supabase.table(VECTOR_TABLE).insert(data).execute()
        return result.data[0]
    
    async def add_documents(
        self,
        contents: List[str],
        document_id: str,
        metadata: Dict = None
    ) -> List[Dict]:
        """Add multiple document chunks"""
        results = []
        
        for i, content in enumerate(contents):
            result = await self.add_document(
                content=content,
                document_id=document_id,
                metadata=metadata,
                chunk_index=i
            )
            results.append(result)
        
        return results
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar documents using vector similarity"""
        if not self.supabase:
            # Demo mode - return mock results
            return [
                {
                    "content": f"Demo result for: {query}",
                    "similarity": 0.95,
                    "document_id": "demo-doc",
                    "metadata": {}
                }
            ]
        
        # Generate query embedding
        query_embedding = embeddings_service.embed_query(query)
        
        # Build search query
        if document_id:
            # Search within specific document
            sql = f"""
            SELECT id, content, metadata, document_id, chunk_index,
                   1 - (embedding <=> '{query_embedding}') as similarity
            FROM {VECTOR_TABLE}
            WHERE document_id = '{document_id}'
            ORDER BY embedding <=> '{query_embedding}'
            LIMIT {limit}
            """
        else:
            # Search all documents
            sql = f"""
            SELECT id, content, metadata, document_id, chunk_index,
                   1 - (embedding <=> '{query_embedding}') as similarity
            FROM {VECTOR_TABLE}
            ORDER BY embedding <=> '{query_embedding}'
            LIMIT {limit}
            """
        
        try:
            result = self.supabase.rpc("run_sql_query", {"sql_text": sql}).execute()
            return result.data
        except Exception as e:
            # Fallback to simple search
            print(f"Vector search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Hybrid search: vector similarity + keyword matching"""
        # Get vector search results
        vector_results = await self.search(query, limit=limit * 2, document_id=document_id)
        
        # Get keyword search results
        keyword_results = await self.keyword_search(query, limit=limit, document_id=document_id)
        
        # Merge and re-rank results
        combined = {}
        
        for result in vector_results:
            doc_id = result.get("id", result.get("document_id"))
            combined[doc_id] = {
                **result,
                "vector_score": result.get("similarity", 0),
                "keyword_score": 0,
                "final_score": result.get("similarity", 0) * 0.7
            }
        
        for result in keyword_results:
            doc_id = result.get("id", result.get("document_id"))
            if doc_id in combined:
                combined[doc_id]["keyword_score"] = result.get("score", 0)
                combined[doc_id]["final_score"] = (
                    combined[doc_id]["vector_score"] * 0.7 +
                    result.get("score", 0) * 0.3
                )
            else:
                combined[doc_id] = {
                    **result,
                    "vector_score": 0,
                    "keyword_score": result.get("score", 0),
                    "final_score": result.get("score", 0) * 0.3
                }
        
        # Sort by final score and return top results
        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        return sorted_results[:limit]
    
    async def keyword_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Simple keyword-based search"""
        if not self.supabase:
            return []
        
        try:
            query_builder = self.supabase.table(VECTOR_TABLE).select(
                "id, content, metadata, document_id, chunk_index"
            )
            
            if document_id:
                query_builder = query_builder.eq("document_id", document_id)
            
            # Simple text search (PostgreSQL full-text search would be better)
            results = query_builder.limit(limit * 2).execute()
            
            # Score by keyword matches
            scored = []
            query_words = query.lower().split()
            
            for item in results.data:
                content_lower = item.get("content", "").lower()
                score = sum(1 for word in query_words if word in content_lower) / len(query_words)
                
                scored.append({
                    **item,
                    "score": score
                })
            
            # Sort by score
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit]
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        if not self.supabase:
            return True
        
        try:
            self.supabase.table(VECTOR_TABLE).delete().eq("document_id", document_id).execute()
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        if not self.supabase:
            return 0
        
        try:
            result = self.supabase.table(VECTOR_TABLE).select("id", count="exact").execute()
            return result.count or 0
        except Exception:
            return 0

# Singleton instance
vector_db_service = VectorDBService()