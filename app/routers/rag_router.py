"""
RAG (Retrieval-Augmented Generation) router - Week 7 Advanced Version
"""
import os
import uuid
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv  

from app.services.embeddings_service import embeddings_service
from app.services.vector_db_service import vector_db_service
from app.services.chunking_service import chunking_service
from app.services.rerank_service import rerank_service
from app.services.metadata_service import metadata_service
from app.services.summarization_service import summarization_service
from app.services.cache_service import summary_cache_service, cache_service
from app.services.versioning_service import versioning_service
from app.services.background_service import background_job_service, JobType
from app.services.team_service import team_service
from app.middleware.logging_config import logger

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

router = APIRouter()

# RAG prompt template
RAG_PROMPT = PromptTemplate.from_template("""
You are a helpful AI assistant. Use the following context to answer the user's question.

Context:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the context doesn't contain enough information, say so
- Provide clear, concise answers
- Include relevant details from the context
- Cite your sources when possible

Answer:
""")

class RAGRequest(BaseModel):
    question: str   
    document_id: Optional[str] = None
    model: Optional[str] = "gemini-2.5-flash"
    max_chunks: Optional[int] = 5
    search_type: Optional[str] = "hybrid"
    use_rerank: Optional[bool] = True
    use_summarize: Optional[bool] = False
    filters: Optional[dict] = None

class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict]
    chunks_used: int
    model: str
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    cached: Optional[bool] = False

class BatchUploadRequest(BaseModel):
    document_names: List[str]
    team_id: Optional[str] = None

class BatchUploadResponse(BaseModel):
    job_id: str
    status: str
    documents_count: int

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_name: str = Form(...),
    team_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    Upload and process a document for RAG
    """
    try:
        document_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        text = content.decode('utf-8', errors='ignore')
        
        # Extract metadata
        metadata = metadata_service.extract_metadata(file, document_name)
        metadata["team_id"] = team_id
        metadata["user_id"] = user_id

        print("meta", metadata)
        
        # Create version 1
        await versioning_service.create_version(
            document_id=document_id,
            content=text,
            metadata=metadata,
            user_id=user_id
        )
        
        # Create chunks
        chunks = chunking_service.create_chunks_with_metadata(
            text=text,
            document_id=document_id,
            document_name=document_name or file.filename
        )
        
        # Store in vector database
        contents = [chunk["content"] for chunk in chunks]
        await vector_db_service.add_documents(
            contents=contents,
            document_id=document_id,
            metadata=metadata
        )
        
        # Add to team if specified
        if team_id and user_id:
            await team_service.add_document(
                team_id=team_id,
                document_id=document_id,
                name=document_name or file.filename,
                uploaded_by=user_id
            )
        
        logger.info(
            f"Document uploaded: {document_id}",
            extra={
                "document_id": document_id,
                "chunks_created": len(chunks),
                "document_name": document_name,
                "team_id": team_id
            }
        )
        
        return {
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "document_name": document_name or file.filename,
            "chunks_created": len(chunks),
            "version": 1,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/batch")
async def batch_upload(
    files: List[UploadFile] = File(...),
    document_names: Optional[List[str]] = Form(None),
    team_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    Batch upload multiple documents
    """
    try:
        # Create background job
        job = background_job_service.create_job(
            job_type=JobType.BATCH_PROCESS,
            payload={
                "files_count": len(files),
                "document_names": document_names,
                "team_id": team_id,
                "user_id": user_id
            },
            user_id=user_id
        )
        
        return {
            "job_id": job.id,
            "status": "pending",
            "documents_count": len(files)
        }
        
    except Exception as e:
        logger.error(f"Batch upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

@router.post("/search", response_model=RAGResponse)
async def rag_search(request: RAGRequest):
    """
    Search documents and generate answer using RAG
    """
    try:
        # Check cache first
        cached = summary_cache_service.get_summary(
            document_id=request.document_id or "all",
            max_length=200
        )
        
        if cached and not request.use_summarize:
            # Return cached result for simple queries
            pass  # Continue with search
        
        # Search for relevant chunks
        if request.search_type == "vector":
            chunks = await vector_db_service.search(
                query=request.question,
                limit=request.max_chunks * 2,
                document_id=request.document_id
            )
        elif request.search_type == "keyword":
            chunks = await vector_db_service.keyword_search(
                query=request.question,
                limit=request.max_chunks * 2,
                document_id=request.document_id
            )
        else:  # hybrid
            chunks = await vector_db_service.hybrid_search(
                query=request.question,
                limit=request.max_chunks * 2,
                document_id=request.document_id
            )
        
        # Apply metadata filters
        if request.filters:
            chunks = await metadata_service.filter_by_metadata(
                chunks, request.filters
            )
        
        if not chunks:
            return RAGResponse(
                answer="No relevant documents found. Please upload documents first.",
                sources=[],
                chunks_used=0,
                model=request.model
            )
        
        # Re-rank results if enabled
        if request.use_rerank:
            chunks = await rerank_service.rerank(
                query=request.question,
                documents=chunks,
                top_k=request.max_chunks
            )
        else:
            chunks = chunks[:request.max_chunks]
        
        # Build context from chunks
        context_parts = []
        sources = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            if content:
                context_parts.append(content)
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "document_id": chunk.get("document_id", "unknown"),
                    "similarity": chunk.get("similarity", chunk.get("final_score", 0)),
                    "chunk_index": chunk.get("chunk_index", i)
                })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using LLM
        llm = ChatGoogleGenerativeAI(
            model=request.model,
            temperature=0.2,
            google_api_key=GOOGLE_API_KEY
        )
        
        chain = RAG_PROMPT | llm | StrOutputParser()
        answer = await chain.ainvoke({
            "context": context,
            "question": request.question
        })
        
        # Generate summary if enabled
        summary = None
        key_points = None
        
        if request.use_summarize:
            summary = await summarization_service.summarize_search_results(
                query=request.question,
                documents=chunks
            )
            
            key_points = await summarization_service.generate_key_points(
                context,
                num_points=5
            )
            
            # Cache the summary
            summary_cache_service.cache_summary(
                document_id=request.document_id or "all",
                summary=summary,
                max_length=200
            )
        
        logger.info(
            f"RAG search completed",
            extra={
                "question": request.question,
                "chunks_used": len(chunks),
                "model": request.model
            }
        )
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            chunks_used=len(chunks),
            model=request.model,
            summary=summary,
            key_points=key_points
        )
        
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/documents")
async def list_documents(
    team_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """List all documents, optionally filtered by team"""
    try:
        if team_id and user_id:
            # Get team documents
            docs = await team_service.get_team_documents(team_id, user_id)
            return {
                "documents": [
                    {
                        "id": doc.id,
                        "name": doc.name,
                        "team_id": doc.team_id,
                        "uploaded_by": doc.uploaded_by,
                        "created_at": doc.created_at.isoformat()
                    }
                    for doc in docs
                ],
                "team_id": team_id
            }
        
        count = await vector_db_service.get_document_count()
        return {
            "total_documents": count,
            "message": "Use team_id parameter for team-specific documents"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/versions")
async def get_document_versions(document_id: str):
    """Get all versions of a document"""
    try:
        versions = await versioning_service.get_versions(document_id)
        return {
            "document_id": document_id,
            "versions": [
                {
                    "version": v.version,
                    "created_at": v.created_at.isoformat(),
                    "content_length": len(v.content)
                }
                for v in versions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/rollback/{version}")
async def rollback_document(document_id: str, version: int):
    """Rollback to a specific version"""
    try:
        new_version = await versioning_service.rollback(document_id, version)
        return {
            "message": f"Rolled back to version {version}",
            "new_version": new_version.version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/teams")
async def list_teams(user_id: str = Query(...)):
    """List all teams for a user"""
    try:
        teams = await team_service.get_user_teams(user_id)
        return {
            "teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "member_count": len(team.members),
                    "created_at": team.created_at.isoformat()
                }
                for team in teams
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/teams")
async def create_team(
    name: str = Query(...),
    owner_id: str = Query(...)
):
    """Create a new team"""
    try:
        team = await team_service.create_team(name, owner_id)
        return {
            "id": team.id,
            "name": team.name,
            "owner_id": team.owner_id,
            "created_at": team.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get background job status"""
    try:
        return background_job_service.get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return cache_service.get_stats()

@router.delete("/cache")
async def clear_cache():
    """Clear all cached data"""
    cache_service.clear()
    return {"message": "Cache cleared"}

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its versions"""
    try:
        # Invalidate cache
        summary_cache_service.invalidate_document(document_id)
        
        # Delete from vector DB
        success = await vector_db_service.delete_document(document_id)
        
        if success:
            return {"message": f"Document {document_id} deleted successfully"}
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def rag_health():
    """RAG service health check"""
    cache_stats = cache_service.get_stats()
    
    return {
        "status": "healthy",
        "service": "rag-week7",
        "features": {
            "embeddings": "configured" if GOOGLE_API_KEY else "missing",
            "vector_db": "configured" if vector_db_service.supabase else "demo mode",
            "reranking": "enabled",
            "summarization": "enabled",
            "metadata_filtering": "enabled",
            "versioning": "enabled",
            "team_isolation": "enabled",
            "caching": "enabled",
            "batch_processing": "enabled"
        },
        "cache": cache_stats
    }