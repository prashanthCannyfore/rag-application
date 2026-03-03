"""
Metadata filtering service for RAG
"""
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

class MetadataService:
    """Service for managing document metadata and filtering"""
    
    def __init__(self):
        self.supabase = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"Supabase not available: {e}")
    
    def extract_metadata(
        self,
        file,
        document_name: str = None
    ) -> Dict[str, Any]:
        """Extract metadata from uploaded file"""
        metadata = {
            "filename": document_name or file.filename,
            "file_type": self._get_file_type(file.filename),
            "file_size": file.size if hasattr(file, 'size') else 0,
            "uploaded_at": datetime.now().isoformat(),
            "chunk_strategy": "recursive",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        
        return metadata
    
    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        if not filename:
            return "unknown"
        
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        type_map = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "md": "text/markdown",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "html": "text/html"
        }
        
        return type_map.get(ext, "application/octet-stream")
    
    async def filter_by_metadata(
        self,
        documents: List[Dict],
        filters: Dict[str, Any]
    ) -> List[Dict]:
        """
        Filter documents by metadata fields
        
        Args:
            documents: List of documents with metadata
            filters: Dictionary of filter criteria
                - file_type: Filter by file type
                - date_from: Filter by date (from)
                - date_to: Filter by date (to)
                - filename: Filter by filename (partial match)
                - tags: Filter by tags (any match)
        
        Returns:
            Filtered list of documents
        """
        if not filters:
            return documents
        
        filtered = []
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            
            # File type filter
            if "file_type" in filters:
                if metadata.get("file_type") != filters["file_type"]:
                    continue
            
            # Date range filter
            if "date_from" in filters:
                doc_date = metadata.get("uploaded_at", "")
                if doc_date and doc_date < filters["date_from"]:
                    continue
            
            if "date_to" in filters:
                doc_date = metadata.get("uploaded_at", "")
                if doc_date and doc_date > filters["date_to"]:
                    continue
            
            # Filename filter (partial match)
            if "filename" in filters:
                filename = metadata.get("filename", "")
                if filters["filename"].lower() not in filename.lower():
                    continue
            
            # Tags filter
            if "tags" in filters:
                doc_tags = metadata.get("tags", [])
                if not any(tag in doc_tags for tag in filters["tags"]):
                    continue
            
            filtered.append(doc)
        
        return filtered
    
    async def search_with_metadata(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search with metadata filtering
        
        This would query Supabase with metadata filters applied
        """
        if not self.supabase:
            return []
        
        try:
            query_builder = self.supabase.table("document_embeddings").select(
                "id, content, metadata, document_id, chunk_index"
            )
            
            # Apply filters
            if filters:
                if filters.get("file_type"):
                    query_builder = query_builder.eq(
                        "metadata->>file_type",
                        filters["file_type"]
                    )
                
                if filters.get("filename"):
                    query_builder = query_builder.ilike(
                        "metadata->>filename",
                        f"%{filters['filename']}%"
                    )
            
            result = query_builder.limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            print(f"Metadata search error: {e}")
            return []
    
    def build_filter_query(
        self,
        filters: Dict[str, Any]
    ) -> tuple[str, dict]:
        """
        Build SQL WHERE clause for metadata filtering
        
        Returns:
            Tuple of (where_clause, parameters)
        """
        conditions = []
        params = {}
        
        if filters.get("file_type"):
            conditions.append("metadata->>'file_type' = :file_type")
            params[":file_type"] = filters["file_type"]
        
        if filters.get("date_from"):
            conditions.append("created_at >= :date_from")
            params[":date_from"] = filters["date_from"]
        
        if filters.get("date_to"):
            conditions.append("created_at <= :date_to")
            params[":date_to"] = filters["date_to"]
        
        if filters.get("filename"):
            conditions.append("metadata->>'filename' ILIKE :filename")
            params[":filename"] = f"%{filters['filename']}%"
        
        if not conditions:
            return "1=1", params
        
        return " AND ".join(conditions), params

# Singleton
metadata_service = MetadataService()