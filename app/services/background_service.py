"""
Background job processing service for RAG
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(Enum):
    DOCUMENT_UPLOAD = "document_upload"
    SUMMARIZE = "summarize"
    INDEX_DOCUMENT = "index_document"
    DELETE_DOCUMENT = "delete_document"
    BATCH_PROCESS = "batch_process"

@dataclass
class Job:
    id: str
    type: JobType
    status: JobStatus
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None

class BackgroundJobService:
    """In-memory background job service (use Redis/Celery for production)"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.job_queue: list = []
        self.callbacks: Dict[JobType, Callable] = {}
    
    def create_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Job:
        """Create a new background job"""
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            type=job_type,
            status=JobStatus.PENDING,
            payload=payload,
            user_id=user_id
        )
        
        self.jobs[job_id] = job
        self.job_queue.append(job_id)
        
        return job
    
    def process_job(self, job_id: str) -> Job:
        """Process a single job"""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.now()
        
        try:
            # Get handler for job type
            handler = self._get_handler(job.type)
            
            # Execute job
            if handler:
                result = handler(job.payload)
                job.result = result
                job.status = JobStatus.COMPLETED
            else:
                job.status = JobStatus.COMPLETED
            
            job.progress = 100
            
        except Exception as e:
            job.error = str(e)
            job.status = JobStatus.FAILED
        
        job.updated_at = datetime.now()
        return job
    
    def _get_handler(self, job_type: JobType) -> Optional[Callable]:
        """Get handler function for job type"""
        handlers = {
            JobType.DOCUMENT_UPLOAD: self._handle_document_upload,
            JobType.SUMMARIZE: self._handle_summarize,
            JobType.INDEX_DOCUMENT: self._handle_index_document,
            JobType.DELETE_DOCUMENT: self._handle_delete_document,
            JobType.BATCH_PROCESS: self._handle_batch_process,
        }
        return handlers.get(job_type)
    
    def _handle_document_upload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document upload job"""
        # This would integrate with the RAG router's upload logic
        return {
            "document_id": payload.get("document_id"),
            "chunks_created": payload.get("chunks_created", 0),
            "status": "completed"
        }
    
    def _handle_summarize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle summarization job"""
        # This would integrate with the summarization service
        return {
            "summary": "Summary would be generated here",
            "key_points": []
        }
    
    def _handle_index_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document indexing job"""
        return {
            "document_id": payload.get("document_id"),
            "indexed": True
        }
    
    def _handle_delete_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document deletion job"""
        return {
            "document_id": payload.get("document_id"),
            "deleted": True
        }
    
    def _handle_batch_process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch processing job"""
        return {
            "processed": payload.get("document_ids", []),
            "count": len(payload.get("document_ids", []))
        }
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def get_user_jobs(self, user_id: str) -> list:
        """Get all jobs for a user"""
        return [
            job for job in self.jobs.values()
            if job.user_id == user_id
        ]
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status for API response"""
        job = self.get_job(job_id)
        if not job:
            return {"error": "Job not found"}
        
        return {
            "job_id": job.id,
            "type": job.type.value,
            "status": job.status.value,
            "progress": job.progress,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status == JobStatus.PENDING:
            job.status = JobStatus.FAILED
            job.error = "Cancelled by user"
            job.updated_at = datetime.now()
            return True
        
        return False

# Singleton
background_job_service = BackgroundJobService()