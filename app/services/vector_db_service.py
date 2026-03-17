"""
Vector database service using PostgreSQL with pgvector
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector

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
                register_vector(self.conn)
                self._ensure_extension()
                self._create_table()
            except Exception as e:
                print(f"PostgreSQL connection error: {e}")
                self.conn = None
    
    def _ensure_extension(self):
        """Ensure pgvector extension is enabled"""
        if not self.conn:
            return
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                if not cur.fetchone():
                    try:
                        cur.execute("CREATE EXTENSION vector;")
                        self.conn.commit()
                        print("✓ pgvector extension created")
                    except Exception as e:
                        print(f"Extension creation error: {e}")
                        print("Please install pgvector manually")
                        self.conn = None
        except Exception as e:
            print(f"Extension check error: {e}")
    
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
                        embedding VECTOR(2000),
                        document_id VARCHAR(255),
                        chunk_index INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE}_embedding 
                    ON {VECTOR_TABLE} USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                    
                    CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE}_document_id 
                    ON {VECTOR_TABLE}(document_id);
                """)
            self.conn.commit()
            print(f"✓ Table {VECTOR_TABLE} created/verified successfully")
        except Exception as e:
            print(f"Table creation error: {e}")
    
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
            
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {VECTOR_TABLE} (content, metadata, embedding, document_id, chunk_index, created_at)
                    VALUES (%s, %s::jsonb, %s::vector, %s, %s, %s)
                    RETURNING id, content, metadata, document_id, chunk_index
                """, (
                    content,
                    metadata_json,
                    embedding,
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
                        SELECT id, content, metadata, document_id, chunk_index,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM {VECTOR_TABLE}
                        WHERE document_id = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, document_id, query_embedding, limit))
                else:
                    cur.execute(f"""
                        SELECT id, content, metadata, document_id, chunk_index,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM {VECTOR_TABLE}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, query_embedding, limit))
                
                results = cur.fetchall()
                return [
                    {
                        "id": str(row[0]),
                        "content": row[1],
                        "metadata": row[2],
                        "document_id": row[3],
                        "chunk_index": row[4],
                        "similarity": row[5]
                    }
                    for row in results
                ]
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None,
        file_type_filter: Optional[str] = None
    ) -> List[Dict]:
        """Hybrid search: vector similarity + keyword matching with metadata filtering"""
        vector_results = await self.search(query, limit=limit * 2, document_id=document_id)
        keyword_results = await self.keyword_search(query, limit=limit * 2, document_id=document_id)
        
        combined = {}
        
        # Process vector results
        for result in vector_results:
            # Use consistent key - always use document_id for combining
            doc_id = result.get("document_id")
            if not doc_id:
                continue
                
            # Apply file type filter if specified
            if file_type_filter:
                metadata = result.get("metadata", {})
                if isinstance(metadata, str):
                    import json
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                if metadata.get("file_type") != file_type_filter:
                    continue
            
            combined[doc_id] = {
                **result,
                "vector_score": result.get("similarity", 0),
                "keyword_score": 0,
                "final_score": result.get("similarity", 0) * 0.7
            }
        
        # Process keyword results
        for result in keyword_results:
            doc_id = result.get("document_id")
            if not doc_id:
                continue
                
            # Apply file type filter if specified
            if file_type_filter:
                metadata = result.get("metadata", {})
                if isinstance(metadata, str):
                    import json
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                if metadata.get("file_type") != file_type_filter:
                    continue
            
            keyword_score = result.get("score", 0)
            # Improve keyword scoring - normalize to 0-1 range
            normalized_keyword_score = min(keyword_score, 1.0)
            
            if doc_id in combined:
                combined[doc_id]["keyword_score"] = normalized_keyword_score
                combined[doc_id]["final_score"] = (
                    combined[doc_id]["vector_score"] * 0.6 +
                    normalized_keyword_score * 0.4
                )
            else:
                combined[doc_id] = {
                    **result,
                    "vector_score": 0,
                    "keyword_score": normalized_keyword_score,
                    "final_score": normalized_keyword_score * 0.4
                }
        
        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        return sorted_results[:limit]
    
    async def keyword_search(
        self,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Enhanced keyword-based search with better scoring"""
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
                
                query_words = [word.lower().strip() for word in query.split() if len(word.strip()) > 2]
                if not query_words:
                    return []
                
                scored = []
                
                for row in results:
                    content_lower = row[1].lower()
                    
                    # Enhanced scoring algorithm
                    exact_matches = sum(1 for word in query_words if word in content_lower)
                    partial_matches = sum(1 for word in query_words 
                                        if any(word in content_word for content_word in content_lower.split()))
                    
                    # Calculate score with different weights
                    exact_score = exact_matches / len(query_words) * 1.0  # Full weight for exact matches
                    partial_score = (partial_matches - exact_matches) / len(query_words) * 0.5  # Half weight for partial
                    
                    total_score = exact_score + partial_score
                    
                    if total_score > 0:  # Only include results with some match
                        scored.append({
                            "id": str(row[0]),
                            "content": row[1],
                            "metadata": row[2],
                            "document_id": row[3],
                            "chunk_index": row[4],
                            "score": min(total_score, 1.0)  # Cap at 1.0
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
    
    async def get_csv_candidates(self, skills_query: str = None, role_query: str = None) -> List[Dict]:
        """Get all CSV candidates with optional skills and role filtering"""
        if not self.conn:
            return []
        
        try:
            with self.conn.cursor() as cur:
                # Get all CSV documents
                cur.execute(f"""
                    SELECT DISTINCT document_id, content, metadata
                    FROM {VECTOR_TABLE}
                    WHERE metadata->>'file_type' = 'text/csv'
                """)
                
                csv_docs = cur.fetchall()
                all_candidates = []
                
                for doc_id, content, metadata in csv_docs:
                    try:
                        import csv
                        import io
                        
                        # Parse CSV content - handle both proper CSV and single-line CSV
                        csv_content = content
                        
                        # If content is on a single line, try to split it properly
                        if '\n' not in csv_content and ',' in csv_content:
                            # This might be a single-line CSV, try to reconstruct it
                            parts = csv_content.split()
                            if len(parts) > 5:  # Should have header + at least one row
                                # Try to reconstruct proper CSV format
                                # Look for patterns like "name,role,skills,location,cost"
                                reconstructed_lines = []
                                current_line = []
                                
                                for part in parts:
                                    current_line.append(part)
                                    # If we have 5 parts (name,role,skills,location,cost), start new line
                                    if len(current_line) == 5:
                                        reconstructed_lines.append(','.join(current_line))
                                        current_line = []
                                
                                if reconstructed_lines:
                                    csv_content = '\n'.join(reconstructed_lines)
                        
                        # Parse CSV content - handle malformed single-line CSV
                        csv_content = content.strip()
                        
                        # Try to reconstruct proper CSV from single-line format
                        if '\n' not in csv_content and csv_content.count(',') > 10:
                            # This looks like a single-line CSV, reconstruct it
                            print(f"Reconstructing single-line CSV...")
                            
                            # Use regex to find candidate records - improved pattern
                            import re
                            
                            # Pattern to match: name,role,"skills",location,cost
                            # Skip the header line by looking for records that don't start with "name,"
                            pattern = r'(?!name,)([^,]+),([^,]+),"([^"]+)",([^,]+),(\d+)'
                            matches = re.findall(pattern, csv_content)
                            
                            if matches:
                                # Reconstruct proper CSV
                                lines = ['name,role,skills,location,cost']
                                for match in matches:
                                    name, role, skills, location, cost = match
                                    # Clean up the name field (remove any leading text)
                                    name = name.strip()
                                    if ' ' in name and not name.split()[0].istitle():
                                        # If first word is not a proper name (like "cost"), take the rest
                                        name_parts = name.split()
                                        if len(name_parts) > 1:
                                            name = ' '.join(name_parts[1:])
                                    
                                    lines.append(f'{name},{role},"{skills}",{location},{cost}')
                                
                                csv_content = '\n'.join(lines)
                                print(f"Reconstructed CSV:\n{csv_content}")
                        
                        # Now parse the CSV normally
                        reader = csv.DictReader(io.StringIO(csv_content))
                        candidates_parsed = []
                        
                        for row in reader:
                            if row and any(row.values()):  # Skip empty rows
                                candidates_parsed.append(row)
                        
                        print(f"Successfully parsed {len(candidates_parsed)} candidates")
                        
                        # Process parsed candidates
                        for row in candidates_parsed:
                            # Clean row data
                            cleaned_row = {k.strip().replace('\r', ''): v.strip() 
                                         for k, v in row.items() if k and v}
                            
                            # Add document metadata
                            cleaned_row['csv_document_id'] = doc_id
                            cleaned_row['source'] = 'csv'
                            
                            # Enhanced filtering
                            should_include = True
                            
                            # If no specific filters provided, include all candidates (fallback mode)
                            if not skills_query and not role_query:
                                should_include = True
                            else:
                                # Apply filtering logic when specific criteria are provided
                                should_include = False  # Start with false, then check matches
                                
                                # For Java searches, check both skills AND role, with special handling
                                if skills_query:
                                    candidate_skills = cleaned_row.get('skills', '').lower()
                                    candidate_role = cleaned_row.get('role', '').lower()
                                    query_skills = [s.strip().lower() for s in skills_query.split(',')]
                                    
                                    # Check if any query skill matches candidate skills
                                    skill_match = any(skill in candidate_skills for skill in query_skills if skill)
                                    
                                    # Special handling for technology-based searches
                                    if 'java' in query_skills:
                                        # Java can be found in skills or role
                                        java_skill_match = 'java' in candidate_skills
                                        java_role_match = 'java' in candidate_role
                                        skill_match = skill_match or java_skill_match or java_role_match
                                    
                                    if 'react' in query_skills:
                                        # React can be found in skills or role
                                        react_skill_match = 'react' in candidate_skills
                                        react_role_match = 'react' in candidate_role
                                        skill_match = skill_match or react_skill_match or react_role_match
                                    
                                    if 'javascript' in query_skills:
                                        # JavaScript can be found in skills or role
                                        js_skill_match = 'javascript' in candidate_skills
                                        js_role_match = 'javascript' in candidate_role
                                        skill_match = skill_match or js_skill_match or js_role_match
                                    
                                    if 'sql' in query_skills:
                                        # SQL can be found in skills or role
                                        sql_skill_match = 'sql' in candidate_skills
                                        sql_role_match = 'sql' in candidate_role
                                        skill_match = skill_match or sql_skill_match or sql_role_match
                                    
                                    if 'fullstack' in query_skills or 'full stack' in query_skills:
                                        # Full stack can be found in skills or role, or inferred from multiple technologies
                                        fullstack_skill_match = any(keyword in candidate_skills for keyword in ['fullstack', 'full stack', 'full-stack'])
                                        fullstack_role_match = any(keyword in candidate_role for keyword in ['fullstack', 'full stack', 'full-stack'])
                                        
                                        # Also check if candidate has multiple full-stack technologies
                                        fullstack_techs = ['react', 'angular', 'vue', 'nodejs', 'node', 'javascript', 'typescript', 'python', 'java']
                                        frontend_techs = ['react', 'angular', 'vue', 'javascript', 'typescript']
                                        backend_techs = ['nodejs', 'node', 'python', 'java', 'express']
                                        
                                        has_frontend = any(tech in candidate_skills for tech in frontend_techs)
                                        has_backend = any(tech in candidate_skills for tech in backend_techs)
                                        has_multiple_techs = sum(1 for tech in fullstack_techs if tech in candidate_skills) >= 3
                                        
                                        # Consider it a full stack match if they have frontend + backend or multiple technologies
                                        fullstack_inferred = (has_frontend and has_backend) or has_multiple_techs
                                        
                                        skill_match = skill_match or fullstack_skill_match or fullstack_role_match or fullstack_inferred
                                    
                                    if 'mongodb' in query_skills or 'mongo' in query_skills:
                                        # MongoDB can be found in skills or role
                                        mongo_skill_match = any(keyword in candidate_skills for keyword in ['mongodb', 'mongo', 'nosql'])
                                        mongo_role_match = any(keyword in candidate_role for keyword in ['mongodb', 'mongo', 'nosql'])
                                        skill_match = skill_match or mongo_skill_match or mongo_role_match
                                    if 'ibm' in query_skills:
                                        ibm_keywords = ['ibm', 'iib', 'ace', 'websphere', 'mq', 'integration', 'esql']
                                        ibm_skill_match = any(keyword in candidate_skills for keyword in ibm_keywords)
                                        ibm_role_match = any(keyword in candidate_role for keyword in ibm_keywords)
                                        
                                        # Special case: if role contains "ibm" but skills don't explicitly mention it,
                                        # still consider it a match (for cases where role is "Ibm Developer")
                                        if 'ibm' in candidate_role.lower():
                                            ibm_role_match = True
                                        
                                        skill_match = skill_match or ibm_skill_match or ibm_role_match
                                    
                                    # Fallback: if query contains common words, do partial matching
                                    if not skill_match:
                                        for query_skill in query_skills:
                                            if query_skill and len(query_skill) > 2:  # Avoid matching very short words
                                                if (query_skill in candidate_skills or 
                                                    query_skill in candidate_role or
                                                    query_skill in cleaned_row.get('name', '').lower()):
                                                    skill_match = True
                                                    break
                                    
                                    should_include = should_include or skill_match
                                
                                # Role filtering if provided
                                if role_query:
                                    candidate_role = cleaned_row.get('role', '').lower()
                                    role_query_lower = role_query.lower()
                                    
                                    # Direct role match or IBM-related role matching
                                    role_match = (role_query_lower in candidate_role or 
                                                candidate_role in role_query_lower)
                                    
                                    # Special handling for IBM roles
                                    if 'ibm' in role_query_lower:
                                        ibm_role_keywords = ['ibm', 'integration', 'iib', 'middleware']
                                        ibm_role_match = any(keyword in candidate_role for keyword in ibm_role_keywords)
                                        role_match = role_match or ibm_role_match
                                    
                                    # Special handling for Java developer roles
                                    if 'java developer' in role_query_lower:
                                        # Accept any role if candidate has Java skills
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        if 'java' in candidate_skills:
                                            role_match = True
                                    
                                    # Special handling for React developer roles
                                    if 'react developer' in role_query_lower:
                                        # Accept any role if candidate has React skills
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        if 'react' in candidate_skills:
                                            role_match = True
                                    
                                    # Special handling for JavaScript developer roles
                                    if 'javascript developer' in role_query_lower:
                                        # Accept any role if candidate has JavaScript skills
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        if 'javascript' in candidate_skills:
                                            role_match = True
                                    
                                    # Special handling for Full Stack developer roles
                                    if 'full stack developer' in role_query_lower or 'fullstack developer' in role_query_lower:
                                        # Accept any role if candidate has full stack skills or is explicitly full stack
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        candidate_role_lower = candidate_role.lower()
                                        
                                        # Direct role match
                                        if any(keyword in candidate_role_lower for keyword in ['full stack', 'fullstack', 'full-stack']):
                                            role_match = True
                                        # Inferred from multiple technologies
                                        else:
                                            fullstack_techs = ['react', 'angular', 'vue', 'nodejs', 'node', 'javascript', 'typescript', 'python', 'java']
                                            frontend_techs = ['react', 'angular', 'vue', 'javascript', 'typescript']
                                            backend_techs = ['nodejs', 'node', 'python', 'java', 'express']
                                            
                                            has_frontend = any(tech in candidate_skills for tech in frontend_techs)
                                            has_backend = any(tech in candidate_skills for tech in backend_techs)
                                            has_multiple_techs = sum(1 for tech in fullstack_techs if tech in candidate_skills) >= 3
                                            
                                            if (has_frontend and has_backend) or has_multiple_techs:
                                                role_match = True
                                    
                                    # Special handling for MongoDB developer roles
                                    if 'mongodb developer' in role_query_lower or 'mongo developer' in role_query_lower:
                                        # Accept any role if candidate has MongoDB skills
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        if any(keyword in candidate_skills for keyword in ['mongodb', 'mongo']):
                                            role_match = True
                                    
                                    # Special handling for SQL developer roles
                                    if 'sql developer' in role_query_lower or 'sql' in role_query_lower:
                                        # Accept any role if candidate has SQL skills
                                        candidate_skills = cleaned_row.get('skills', '').lower()
                                        if 'sql' in candidate_skills:
                                            role_match = True
                                    
                                    should_include = should_include or role_match
                            
                            if should_include:
                                all_candidates.append(cleaned_row)
                                
                    except Exception as e:
                        print(f"Error parsing CSV document {doc_id}: {e}")
                        continue
                
                return all_candidates
                
        except Exception as e:
            print(f"Error getting CSV candidates: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
vector_db_service = VectorDBService()
