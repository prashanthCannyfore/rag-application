"""
RAG (Retrieval-Augmented Generation) router - Week 7 Advanced Version
"""
import os
import uuid
import io
import zipfile
import csv
import json
import pandas as pd
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
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
from app.services.pdf_service import pdf_service
from app.services.file_storage_service import file_storage_service
from app.services.job_parser_service import job_parser_service
from app.services.vector_db_service import VECTOR_TABLE
from app.services.cloudinary_service import cloudinary_service
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
    Supports: PDF, TXT, MD, DOC, DOCX, CSV, and other text-based formats
    """
    try:
        document_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        logger.info(f"Upload: Read {len(content)} bytes from {file.filename}")
        logger.info(f"Upload: First 20 bytes: {content[:20]}")
        
        # Extract metadata first
        metadata = metadata_service.extract_metadata(file, document_name)
        metadata["team_id"] = team_id
        metadata["user_id"] = user_id

        logger.info(f"Upload: Metadata extracted: {metadata.get('file_type')}")
        
        # Extract text based on file type
        file_type = metadata_service._get_file_type(file.filename)
        text = ""
        
        if file_type == "application/pdf":
            # Process PDF files
            text = pdf_service.extract_text_from_pdf(content, file.filename)
            pdf_metadata = pdf_service.extract_metadata_from_pdf(content)
            logger.info(f"Extracted {len(text)} chars from PDF, {pdf_metadata.get('pages', 'N/A')} pages")
            
            # Store original PDF bytes for download
            content_bytes = content
            logger.info(f"Storing content_bytes: {len(content_bytes)} bytes")
            
            # Upload to Cloudinary (if configured)
            cloudinary_url = cloudinary_service.upload_pdf(content, file.filename, document_id)
            if cloudinary_url:
                logger.info(f"Uploaded to Cloudinary: {cloudinary_url}")
                metadata["cloudinary_url"] = cloudinary_url
            
            # Save PDF to disk as backup
            file_path = file_storage_service.save_file(content, file.filename)
            logger.info(f"Saved to disk: {file_path}")
            metadata["file_path"] = file_path
            
            # Verify the saved file
            from pathlib import Path
            if Path(file_path).exists():
                saved_size = Path(file_path).stat().st_size
                logger.info(f"Verified saved file: {saved_size} bytes on disk")
                if saved_size != len(content):
                    logger.error(f"SIZE MISMATCH! Uploaded: {len(content)}, Saved: {saved_size}")
            else:
                logger.error(f"File was not saved to disk!")
        else:
            # Process text-based files
            text = content.decode('utf-8', errors='ignore')
            content_bytes = None
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        # Create version 1
        await versioning_service.create_version(
            document_id=document_id,
            content=text,
            metadata=metadata,
            user_id=user_id,
            content_bytes=content_bytes
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
                "team_id": team_id,
                "file_type": file_type
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
        
    except HTTPException:
        raise
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
            "batch_processing": "enabled",
            "pdf_support": "enabled"
        },
        "cache": cache_stats
    }

@router.get("/debug/document/{document_id}")
async def debug_document(document_id: str):
    """Debug endpoint to check document storage"""
    try:
        versions = await versioning_service.get_versions(document_id)
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found")
        
        latest = versions[-1]
        metadata = latest.metadata or {}
        
        from pathlib import Path
        file_path = metadata.get('file_path')
        file_exists = False
        file_size = 0
        file_is_pdf = False
        
        if file_path:
            file_path_obj = Path(file_path)
            file_exists = file_path_obj.exists()
            if file_exists:
                file_size = file_path_obj.stat().st_size
                with open(file_path_obj, 'rb') as f:
                    first_bytes = f.read(10)
                    file_is_pdf = first_bytes.startswith(b'%PDF')
        
        return {
            "document_id": document_id,
            "versions": len(versions),
            "metadata": {
                "filename": metadata.get('filename'),
                "file_type": metadata.get('file_type'),
                "file_path": file_path
            },
            "storage": {
                "has_content_bytes": latest.content_bytes is not None,
                "content_bytes_size": len(latest.content_bytes) if latest.content_bytes else 0,
                "content_bytes_is_pdf": latest.content_bytes.startswith(b'%PDF') if latest.content_bytes else False,
                "file_exists_on_disk": file_exists,
                "file_size_on_disk": file_size,
                "file_is_pdf": file_is_pdf
            },
            "content_preview": latest.content[:200] if latest.content else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/test-pdf")
async def test_pdf_response():
    """Test endpoint that returns a minimal valid PDF"""
    # Minimal valid PDF (1 page, blank)
    minimal_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
190
%%EOF"""
    
    return StreamingResponse(
        io.BytesIO(minimal_pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=test.pdf",
            "Content-Type": "application/pdf"
        }
    )

@router.get("/debug/name-matching")
async def debug_name_matching():
    """Debug endpoint to show name matching results"""
    try:
        # Get all documents
        doc_ids = []
        if vector_db_service.conn:
            with vector_db_service.conn.cursor() as cur:
                cur.execute(f"SELECT DISTINCT document_id FROM {VECTOR_TABLE}")
                doc_ids = [row[0] for row in cur.fetchall()]
        
        # Index PDFs
        pdf_resumes = {}
        for doc_id in doc_ids:
            versions = await versioning_service.get_versions(doc_id)
            if versions:
                latest = versions[-1]
                metadata = latest.metadata or {}
                if metadata.get("file_type") == "application/pdf":
                    filename = metadata.get("filename", "")
                    name_lower = filename.lower()
                    name_lower = name_lower.replace('.pdf', '').replace('_profile', '').replace('-profile', '')
                    name_parts = name_lower.replace('_', ' ').replace('-', ' ').split()
                    if name_parts:
                        name_part = name_parts[0].strip()
                        pdf_resumes[name_part] = {
                            "document_id": doc_id,
                            "filename": filename
                        }
        
        # Get CSV candidates
        csv_candidates = []
        for doc_id in doc_ids:
            versions = await versioning_service.get_versions(doc_id)
            if versions:
                latest = versions[-1]
                metadata = latest.metadata or {}
                if metadata.get("file_type") == "text/csv":
                    import csv
                    import io
                    content = latest.content
                    reader = csv.DictReader(io.StringIO(content))
                    for row in reader:
                        cleaned_row = {k.strip().replace('\r', ''): v.strip() for k, v in row.items()}
                        csv_candidates.append(cleaned_row.get('name', ''))
        
        # Test matching
        matches = []
        for candidate_name in csv_candidates:
            candidate_first = candidate_name.lower().split()[0]
            best_match = None
            best_score = 0
            
            for pdf_name, pdf_info in pdf_resumes.items():
                # Calculate score
                score = 0
                if candidate_first == pdf_name:
                    score = 100
                elif candidate_first in pdf_name or pdf_name in candidate_first:
                    score = 80
                elif (candidate_first[0] == pdf_name[0] and 
                      abs(len(candidate_first) - len(pdf_name)) <= 2):
                    common_chars = sum(1 for c in candidate_first if c in pdf_name)
                    score = (common_chars / max(len(candidate_first), len(pdf_name))) * 70
                
                if score > best_score:
                    best_score = score
                    best_match = pdf_info
            
            matches.append({
                "csv_candidate": candidate_name,
                "csv_first_name": candidate_first,
                "matched_pdf": best_match["filename"] if best_match else None,
                "match_score": best_score,
                "will_match": best_score >= 60,
                "document_id": best_match["document_id"] if best_match else None
            })
        
        return {
            "pdf_resumes": {name: info["filename"] for name, info in pdf_resumes.items()},
            "csv_candidates": csv_candidates,
            "matches": matches
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/resume/{document_id}")
async def download_resume(document_id: str):
    """
    Download individual resume PDF by document_id
    """
    try:
        from urllib.parse import quote
        from fastapi.responses import RedirectResponse
        
        versions = await versioning_service.get_versions(document_id)
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found")

        latest = versions[-1]
        metadata = latest.metadata or {}
        filename = metadata.get('filename', f'resume_{document_id}.pdf')
        
        # Sanitize filename
        safe_filename = filename.replace('"', '').replace("'", "")
        encoded_filename = quote(safe_filename)

        logger.info(f"Download request for {document_id}, filename: {filename}")

        # PRIORITY 1: Use Cloudinary URL (most reliable)
        cloudinary_url = metadata.get('cloudinary_url')
        if cloudinary_url:
            logger.info(f"Redirecting to Cloudinary: {cloudinary_url}")
            return RedirectResponse(url=cloudinary_url)

        # PRIORITY 2: Check if file_path exists on disk
        file_path = metadata.get('file_path')
        if file_path:
            from pathlib import Path
            file_path_obj = Path(file_path)
            logger.info(f"Checking file path: {file_path_obj}, exists: {file_path_obj.exists()}")
            if file_path_obj.exists():
                with open(file_path_obj, 'rb') as f:
                    pdf_content = f.read()
                logger.info(f"Read {len(pdf_content)} bytes from disk")
                
                if not pdf_content.startswith(b'%PDF'):
                    logger.error(f"File on disk is not a valid PDF!")
                    raise HTTPException(status_code=500, detail="Stored file is corrupted")
                
                return StreamingResponse(
                    io.BytesIO(pdf_content),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                        "Content-Type": "application/pdf",
                        "Content-Length": str(len(pdf_content))
                    }
                )

        # PRIORITY 3: Use content_bytes if available
        if latest.content_bytes:
            logger.info(f"Using content_bytes: {len(latest.content_bytes)} bytes")
            
            if not latest.content_bytes.startswith(b'%PDF'):
                logger.error(f"content_bytes is not a valid PDF!")
                raise HTTPException(status_code=500, detail="Stored PDF is corrupted")
            
            return StreamingResponse(
                io.BytesIO(latest.content_bytes),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                    "Content-Type": "application/pdf",
                    "Content-Length": str(len(latest.content_bytes))
                }
            )

        # Fallback: Return as text file
        logger.warning(f"No PDF found, returning extracted text for {document_id}")
        text_filename = safe_filename.replace('.pdf', '.txt')
        encoded_text_filename = quote(text_filename)
        text_bytes = latest.content.encode('utf-8')
        return StreamingResponse(
            io.BytesIO(text_bytes),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{text_filename}"; filename*=UTF-8\'\'{encoded_text_filename}',
                "Content-Type": "text/plain",
                "Content-Length": str(len(text_bytes))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/search/job")
async def search_job(
    job_description: str = Form(...),
    max_results: Optional[int] = Form(10),
    strict_location: Optional[bool] = Form(True)  # New parameter for strict location filtering
):
    """
    Search for candidates matching job description
    Combines CSV filtering with resume RAG search
    """
    try:
        # Parse job description
        job_req = job_parser_service.parse_job_description(job_description)
        
        logger.info(f"Job search: {job_req}, strict_location: {strict_location}")
        
        # Get all documents from database
        count = await vector_db_service.get_document_count()
        if count == 0:
            return {
                "message": "No documents found. Please upload CSV and resumes first.",
                "job_requirements": job_req,
                "candidates": []
            }
        
        # Get all document IDs
        doc_ids = []
        if vector_db_service.conn:
            with vector_db_service.conn.cursor() as cur:
                cur.execute(f"SELECT DISTINCT document_id FROM {VECTOR_TABLE}")
                doc_ids = [row[0] for row in cur.fetchall()]
        
        # First, collect all PDF resumes for name matching
        pdf_resumes = {}  # name -> document_id mapping
        for doc_id in doc_ids:
            try:
                versions = await versioning_service.get_versions(doc_id)
                if versions:
                    latest = versions[-1]
                    metadata = latest.metadata or {}
                    if metadata.get("file_type") == "application/pdf":
                        filename = metadata.get("filename", "")
                        # Extract name from filename - try multiple patterns
                        # e.g., "Prashanth_Profile_React.pdf", "sakthi-2025-25.pdf"
                        name_lower = filename.lower()
                        # Remove common suffixes and split
                        name_lower = name_lower.replace('.pdf', '').replace('_profile', '').replace('-profile', '')
                        # Get first part (usually the name)
                        name_parts = name_lower.replace('_', ' ').replace('-', ' ').split()
                        if name_parts:
                            name_part = name_parts[0].strip()
                            pdf_resumes[name_part] = doc_id
                            logger.info(f"Indexed PDF: '{filename}' as '{name_part}' -> {doc_id}")
            except Exception as e:
                logger.error(f"Error indexing PDF {doc_id}: {e}")
        
        logger.info(f"Found {len(pdf_resumes)} PDF resumes: {list(pdf_resumes.keys())}")
        
        # Match candidates
        candidates = []
        seen_candidates = set()  # Track unique candidates to avoid duplicates
        
        for doc_id in doc_ids:
            try:
                versions = await versioning_service.get_versions(doc_id)
                if versions:
                    latest = versions[-1]
                    metadata = latest.metadata or {}
                    
                    # Check if this is a CSV file with structured data
                    if metadata.get("file_type") == "text/csv":
                        # Parse CSV content using csv module for proper handling
                        import csv
                        import io
                        content = latest.content
                        reader = csv.DictReader(io.StringIO(content))
                        for row in reader:
                            # Clean up any carriage returns in keys/values
                            cleaned_row = {k.strip().replace('\r', ''): v.strip() for k, v in row.items()}
                            
                            # STRICT LOCATION FILTER - Apply before matching
                            if strict_location and job_req.get("location"):
                                candidate_location = cleaned_row.get('location', '').lower().strip()
                                job_location = job_req["location"].lower().strip()
                                
                                # Exact match required for strict filtering
                                if candidate_location != job_location:
                                    logger.debug(f"Skipping {cleaned_row.get('name')} - location mismatch: {candidate_location} != {job_location}")
                                    continue
                            
                            # Create unique key for this candidate
                            candidate_key = (
                                cleaned_row.get('name', '').lower(),
                                cleaned_row.get('role', '').lower(),
                                cleaned_row.get('location', '').lower()
                            )
                            
                            # Skip if we've already seen this candidate
                            if candidate_key in seen_candidates:
                                continue
                            
                            match = job_parser_service.match_candidate(cleaned_row, job_req)
                            if match["is_match"]:
                                seen_candidates.add(candidate_key)
                                
                                candidate_name_full = cleaned_row.get('name', '')
                                candidate_name = candidate_name_full.lower().split()[0]  # Get first name
                                
                                # Try to find matching PDF resume with fuzzy matching
                                resume_doc_id = None
                                best_match_score = 0
                                
                                for pdf_name, pdf_id in pdf_resumes.items():
                                    # Calculate similarity score
                                    score = 0
                                    
                                    # Exact match
                                    if candidate_name == pdf_name:
                                        score = 100
                                    # One contains the other
                                    elif candidate_name in pdf_name or pdf_name in candidate_name:
                                        score = 80
                                    # Similar length and starts with same letter
                                    elif (candidate_name[0] == pdf_name[0] and 
                                          abs(len(candidate_name) - len(pdf_name)) <= 2):
                                        # Check character overlap
                                        common_chars = sum(1 for c in candidate_name if c in pdf_name)
                                        score = (common_chars / max(len(candidate_name), len(pdf_name))) * 70
                                    
                                    if score > best_match_score:
                                        best_match_score = score
                                        resume_doc_id = pdf_id
                                
                                if resume_doc_id and best_match_score >= 60:
                                    logger.info(f"Matched CSV candidate '{candidate_name_full}' to PDF resume (score: {best_match_score})")
                                else:
                                    logger.warning(f"No PDF resume found for '{candidate_name_full}' (best score: {best_match_score})")
                                
                                candidates.append({
                                    **cleaned_row,
                                    "match_score": match["score"],
                                    "match_details": match,
                                    "document_id": resume_doc_id or doc_id,  # Use PDF doc_id if found, else CSV doc_id
                                    "csv_document_id": doc_id,  # Keep original CSV doc_id
                                    "has_resume": resume_doc_id is not None,
                                    "resume_match_score": best_match_score if resume_doc_id else 0
                                })
                    else:
                        # This is a resume - use RAG search
                        resume_text = latest.content
                        match = job_parser_service.match_candidate(
                            {"skills": resume_text, "role": metadata.get("filename", "")},
                            job_req
                        )
                        if match["is_match"]:
                            candidates.append({
                                "document_id": doc_id,
                                "filename": metadata.get("filename", ""),
                                "file_path": metadata.get("file_path"),
                                "match_score": match["score"],
                                "match_details": match,
                                "has_resume": True
                            })
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
        
        # Sort by match score
        candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        # Limit results
        candidates = candidates[:max_results]
        
        # Generate summary using LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
            google_api_key=GOOGLE_API_KEY
        )
        
        # Build context from candidates
        context_parts = []
        for i, candidate in enumerate(candidates, 1):
            if "role" in candidate:
                context_parts.append(f"{i}. {candidate.get('name', 'Unknown')}")
                context_parts.append(f"   Role: {candidate.get('role', 'N/A')}")
                context_parts.append(f"   Skills: {candidate.get('skills', 'N/A')}")
                context_parts.append(f"   Location: {candidate.get('location', 'N/A')}")
                context_parts.append(f"   Cost: {candidate.get('cost', 'N/A')}")
                context_parts.append(f"   Resume: {'Available' if candidate.get('has_resume') else 'Not found'}")
            else:
                context_parts.append(f"{i}. {candidate.get('filename', 'Unknown')}")
                context_parts.append(f"   Match Score: {candidate.get('match_score', 0)}")
        
        context = "\n".join(context_parts)
        
        # Generate answer
        prompt = f"""
        Based on the following job requirements and matching candidates, provide a summary.
        
        Job Requirements:
        - Role: {job_req.get('role', 'N/A')}
        - Skills: {', '.join(job_req.get('skills', []))}
        - Location: {job_req.get('location', 'N/A')}
        - Cost: {job_req.get('cost', 'N/A')}
        
        Matching Candidates:
        {context}
        
        Provide a concise summary of the matching candidates.
        """
        
        answer = await llm.ainvoke(prompt)
        
        return {
            "message": f"Found {len(candidates)} matching candidates",
            "job_requirements": job_req,
            "candidates": candidates,
            "answer": answer.content if hasattr(answer, 'content') else str(answer)
        }
        
    except Exception as e:
        logger.error(f"Job search error: {e}")
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")
