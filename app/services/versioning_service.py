"""
Document versioning service for RAG
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

@dataclass
class DocumentVersion:
    id: str
    document_id: str
    version: int
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    created_by: Optional[str]

class VersioningService:
    """Service for managing document versions"""
    
    def __init__(self):
        self.supabase = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception:
                pass
        
        # In-memory storage for demo
        self.versions: Dict[str, List[DocumentVersion]] = {}
    
    async def create_version(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> DocumentVersion:
        """Create a new version of a document"""
        version_id = str(uuid.uuid4())
        
        # Get current version number
        current_version = 1
        if document_id in self.versions:
            current_version = len(self.versions[document_id]) + 1
        
        version = DocumentVersion(
            id=version_id,
            document_id=document_id,
            version=current_version,
            content=content,
            metadata=metadata,
            created_at=datetime.now(),
            created_by=user_id
        )
        
        # Store version
        if document_id not in self.versions:
            self.versions[document_id] = []
        
        self.versions[document_id].append(version)
        
        return version
    
    async def get_versions(self, document_id: str) -> List[DocumentVersion]:
        """Get all versions of a document"""
        return self.versions.get(document_id, [])
    
    async def get_version(
        self,
        document_id: str,
        version: int
    ) -> Optional[DocumentVersion]:
        """Get a specific version of a document"""
        versions = self.versions.get(document_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    async def get_latest_version(
        self,
        document_id: str
    ) -> Optional[DocumentVersion]:
        """Get the latest version of a document"""
        versions = self.versions.get(document_id, [])
        if versions:
            return versions[-1]
        return None
    
    async def compare_versions(
        self,
        document_id: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """Compare two versions of a document"""
        v1 = await self.get_version(document_id, version1)
        v2 = await self.get_version(document_id, version2)
        
        if not v1 or not v2:
            raise ValueError("One or both versions not found")
        
        return {
            "version1": {
                "version": v1.version,
                "created_at": v1.created_at.isoformat(),
                "content_length": len(v1.content)
            },
            "version2": {
                "version": v2.version,
                "created_at": v2.created_at.isoformat(),
                "content_length": len(v2.content)
            },
            "content_changed": v1.content != v2.content,
            "size_diff": len(v2.content) - len(v1.content)
        }
    
    async def rollback(
        self,
        document_id: str,
        version: int
    ) -> DocumentVersion:
        """Rollback to a specific version"""
        target_version = await self.get_version(document_id, version)
        
        if not target_version:
            raise ValueError(f"Version {version} not found")
        
        # Create a new version with the old content
        new_version = await self.create_version(
            document_id=document_id,
            content=target_version.content,
            metadata={
                **target_version.metadata,
                "rollback_from": version
            }
        )
        
        return new_version
    
    async def delete_version(
        self,
        document_id: str,
        version: int
    ) -> bool:
        """Delete a specific version"""
        versions = self.versions.get(document_id, [])
        for i, v in enumerate(versions):
            if v.version == version:
                del versions[i]
                return True
        return False
    
    def get_version_count(self, document_id: str) -> int:
        """Get the number of versions for a document"""
        return len(self.versions.get(document_id, []))

# Singleton
versioning_service = VersioningService()