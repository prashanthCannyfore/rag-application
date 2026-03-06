"""
Vector database service using PostgreSQL with JSONB embeddings
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
VECTOR_TABLE = os.getenv("VECTOR_TABLE_NAME", "document_embeddings")

class VectorDBService:
    """Service for managing vector embeddings in PostgreSQL"""
    
    def __init__(self):
        self.conn = None
        if DATABASE_URL:
            try:
                self.conn = psycopg2.connect(DATABASE_URL)
                self._create_table()
            except Exception as e:
                print(f"PostgreSQL connection error: {e}")
                self.conn = None
    
    def _create_table(self):
        """Create vector database table"""
        if not self.conn:
            print("PostgreSQL not configured, skipping table creation")
            return
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {VECTOR_TABLE} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        embedding JSONB,
                        document_id VARCHAR(255),
                        chunk_index INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE}_document_id 
                    ON {VECTOR_TABLE}(document_id);
                """)
            self.conn.commit()
            print(f"✓ Table {VECTOR_TABLE} created/verified successfully")
        except Exception as e:
            print(f"Table creation error: {e}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    async def add_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict = None,
        chunk_index: int = 0
    ) -> Dict:
        """Add a document chunk with embedding"""
        if not self.conn:
            return {
                "id": "demo-id",
                "content": content[:100],
                "document_id": document_id,
                "chunk_index": chunk_index
            }
        
        try:
            from app.services.embeddings_service import embeddings_service
            embedding = embeddings_service.embed_text(content)
            metadata_json = json.dumps(metadata or {})
            embedding_json = json.dumps(embedding)
            
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {VECTOR_TABLE} (content, metadata, embedding, document_id, chunk_index, created_at)
                    VALUES (%s, %s::jsonb, %s::jsonb, %s, %s, %s)
                    RETURNING id, content, metadata, document_id, chunk_index
                """, (
                    content,
                    metadata_json,
                    embedding_json,
                    document_id,
                    chunk_index,
                    datetime.now().isoformat()
                ))
                result = cur.fetchone()
                self.conn.commit()
                
                return {
                    "id": str(result[0]),
                    "content": result[1],
                    "metadata": result[2],
                    "document_id": result[3],
                    "chunk_index": result[4]
                }
        except Exception as e:
            print(f"Add document error: {e}")
            return {}
    
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
        if not self.conn:
            return []
        
        try:
            from app.services.embeddings_service import embeddings_service
            query_embedding = embeddings_service.embed_query(query)
            
            with self.conn.cursor() as cur:
                if document_id:
                    cur.execute(f"""
                        SELECT id, content, metadata, document_id, chunk_index, embedding
                        FROM {VECTOR_TABLE}
                        WHERE document_id = %s
                    """, (document_id,))
                else:
                    cur.execute(f"""
                        SELECT id, content, metadata, document_id, chunk_index, embedding
                        FROM {VECTOR_TABLE}
                    """)
                
                results = cur.fetchall()
                
                scored = []
                for row in results:
                    embedding_json = row[5]
                    if embedding_json:
                        row_embedding = json.loads(embedding_json)
                        similarity = self._cosine_similarity(query_embedding, row_embedding)
                        scored.append({
                            "id": str(row[0]),
                            "content": row[1],
                            "metadata": row[2],
                            "document_id": row[3],
                            "chunk_index": row[4],
                            "similarity": similarity
                        })
                
                scored.sort(key=lambda x: x["similarity"], reverse=True)
                return scored[:limit]
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Hybrid search: vector similarity + keyword matching"""
        vector_results = await self.search(query, limit=limit * 2, document_id=document_id)
        keyword_results = await self.keyword_search(query, limit=limit, document_id=document_id)
        
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
        
        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        return sorted_results[:limit]
    
    async def keyword_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Simple keyword-based search"""
        if not self.conn:
            return []
        
        try:
            with self.conn.cursor() as cur:
                if document_id:
                    cur.execute(f"""
                        SELECT id, content, metadata, document_id, chunk_index
                        FROM {VECTOR_TABLE}
                        WHERE document_id = %s
                    """, (document_id,))
                else:
                    cur.execute(f"""
                        SELECT id, content, metadata, document_id, chunk_index
                        FROM {VECTOR_TABLE}
                    """)
                
                results = cur.fetchall()
                
                query_words = query.lower().split()
                scored = []
                
                for row in results:
                    content_lower = row[1].lower()
                    score = sum(1 for word in query_words if word in content_lower) / max(len(query_words), 1)
                    scored.append({
                        "id": str(row[0]),
                        "content": row[1],
                        "metadata": row[2],
                        "document_id": row[3],
                        "chunk_index": row[4],
                        "score": score
                    })
                
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:limit]
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        if not self.conn:
            return True
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"DELETE FROM {VECTOR_TABLE} WHERE document_id = %s", (document_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        if not self.conn:
            return 0
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(DISTINCT document_id) FROM {VECTOR_TABLE}")
                result = cur.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
vector_db_service = VectorDBService()
