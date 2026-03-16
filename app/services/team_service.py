"""
Team isolation service for multi-tenant RAG
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
class Team:
    id: str
    name: str
    owner_id: str
    members: List[str]
    created_at: datetime
    settings: Dict[str, Any]

@dataclass
class TeamDocument:
    id: str
    team_id: str
    document_id: str
    name: str
    uploaded_by: str
    created_at: datetime
    is_public: bool = False

class TeamService:
    """Service for managing team-based document isolation"""
    
    def __init__(self):
        self.supabase = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception:
                pass
        
        # In-memory storage for demo
        self.teams: Dict[str, Team] = {}
        self.team_documents: Dict[str, List[TeamDocument]] = {}
        self.user_teams: Dict[str, List[str]] = {}  # user_id -> [team_ids]
    
    async def create_team(
        self,
        name: str,
        owner_id: str,
        settings: Dict[str, Any] = None
    ) -> Team:
        """Create a new team"""
        team_id = str(uuid.uuid4())
        
        team = Team(
            id=team_id,
            name=name,
            owner_id=owner_id,
            members=[owner_id],
            created_at=datetime.now(),
            settings=settings or {}
        )
        
        self.teams[team_id] = team
        self.user_teams[owner_id] = self.user_teams.get(owner_id, []) + [team_id]
        self.team_documents[team_id] = []
        
        return team
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        return self.teams.get(team_id)
    
    async def get_user_teams(self, user_id: str) -> List[Team]:
        """Get all teams for a user"""
        team_ids = self.user_teams.get(user_id, [])
        return [self.teams[tid] for tid in team_ids if tid in self.teams]
    
    async def add_member(self, team_id: str, user_id: str) -> bool:
        """Add a member to a team"""
        if team_id not in self.teams:
            return False
        
        team = self.teams[team_id]
        if user_id not in team.members:
            team.members.append(user_id)
            self.user_teams[user_id] = self.user_teams.get(user_id, []) + [team_id]
        
        return True
    
    async def remove_member(self, team_id: str, user_id: str) -> bool:
        """Remove a member from a team"""
        if team_id not in self.teams:
            return False
        
        team = self.teams[team_id]
        if user_id in team.members:
            team.members.remove(user_id)
        
        return True
    
    async def is_member(self, team_id: str, user_id: str) -> bool:
        """Check if user is a member of a team"""
        team = self.teams.get(team_id)
        if not team:
            return False
        return user_id in team.members
    
    async def add_document(
        self,
        team_id: str,
        document_id: str,
        name: str,
        uploaded_by: str,
        is_public: bool = False
    ) -> TeamDocument:
        """Add a document to a team's knowledge base"""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        doc = TeamDocument(
            id=str(uuid.uuid4()),
            team_id=team_id,
            document_id=document_id,
            name=name,
            uploaded_by=uploaded_by,
            created_at=datetime.now(),
            is_public=is_public
        )
        
        self.team_documents[team_id].append(doc)
        return doc
    
    async def get_team_documents(
        self,
        team_id: str,
        user_id: str
    ) -> List[TeamDocument]:
        """Get all documents accessible to a user in a team"""
        if team_id not in self.teams:
            return []
        
        team = self.teams[team_id]
        
        # Check if user is member
        if user_id not in team.members:
            # Return only public documents
            return [
                doc for doc in self.team_documents.get(team_id, [])
                if doc.is_public
            ]
        
        # Return all documents
        return self.team_documents.get(team_id, [])
    
    async def delete_document(self, team_id: str, document_id: str) -> bool:
        """Remove a document from a team's knowledge base"""
        if team_id not in self.team_documents:
            return False
        
        docs = self.team_documents[team_id]
        for i, doc in enumerate(docs):
            if doc.document_id == document_id:
                del docs[i]
                return True
        
        return False
    
    async def remove_document_from_all_teams(self, document_id: str) -> int:
        """Remove a document from all teams"""
        removed_count = 0
        for team_id in self.team_documents:
            docs = self.team_documents[team_id]
            for i in range(len(docs) - 1, -1, -1):  # Iterate backwards
                if docs[i].document_id == document_id:
                    del docs[i]
                    removed_count += 1
        return removed_count
    
    async def search_team_documents(
        self,
        team_id: str,
        user_id: str,
        query: str
    ) -> List[TeamDocument]:
        """Search documents in a team's knowledge base"""
        docs = await self.get_team_documents(team_id, user_id)
        
        # Simple text search
        query_lower = query.lower()
        return [
            doc for doc in docs
            if query_lower in doc.name.lower()
        ]
    
    def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """Get statistics for a team"""
        if team_id not in self.teams:
            return {}
        
        team = self.teams[team_id]
        docs = self.team_documents.get(team_id, [])
        
        return {
            "team_id": team_id,
            "name": team.name,
            "member_count": len(team.members),
            "document_count": len(docs),
            "created_at": team.created_at.isoformat()
        }

# Singleton
team_service = TeamService()