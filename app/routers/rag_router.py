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
            "metadata": metadata,
            "text_preview": text[:300] + "..." if len(text) > 300 else text,
            "text_length": len(text),
            "validation": {
                "has_content": len(text.strip()) > 0,
                "content_cleaned": True,
                "file_type": file_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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
                # Get file type from metadata if available
                file_type = chunk.get("metadata", {}).get("file_type", "application/pdf") if isinstance(chunk.get("metadata"), dict) else "application/pdf"
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "document_id": chunk.get("document_id", "unknown"),
                    "similarity": chunk.get("similarity", chunk.get("final_score", 0)),
                    "chunk_index": chunk.get("chunk_index", i),
                    "file_type": file_type
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

@router.post("/search/job")
async def search_job(
    job_description: str = Form(...),
    max_results: Optional[int] = Form(10),
    strict_location: Optional[bool] = Form(True)
):
    """
    Search for candidates: CSV first, then RAG search for resumes
    Returns candidates with resume download options
    """
    try:
        # Parse job description
        job_req = job_parser_service.parse_job_description(job_description)
        
        logger.info(f"Job search: {job_req}, strict_location: {strict_location}")
        
        # STEP 1: Search CSV files first using hybrid search
        csv_candidates = {}  # Use dict to avoid duplicates by name+role
        csv_search_query = " ".join([
            job_req.get("role") or "",
            *(job_req.get("skills") or [])
        ]).strip()
        
        logger.info(f"CSV search query: '{csv_search_query}'")
        
        # Try hybrid search first, then fallback to direct CSV search
        csv_results = []
        if csv_search_query:
            csv_results = await vector_db_service.hybrid_search(
                query=csv_search_query,
                limit=50  # Get more CSV results
            )
            logger.info(f"CSV hybrid search returned {len(csv_results)} results")
        
        # Fallback: Search all CSV documents directly if hybrid search returns few results
        if len(csv_results) < 5:
            logger.info("Fallback: Searching all CSV documents directly")
            # Get all document IDs
            doc_ids = []
            if vector_db_service.conn:
                with vector_db_service.conn.cursor() as cur:
                    cur.execute(f"SELECT DISTINCT document_id FROM {VECTOR_TABLE}")
                    doc_ids = [row[0] for row in cur.fetchall()]
            
            # Check each document to see if it's a CSV
            for doc_id in doc_ids:
                try:
                    versions = await versioning_service.get_versions(doc_id)
                    if versions:
                        latest = versions[-1]
                        metadata = latest.metadata or {}
                        if metadata.get("file_type") == "text/csv":
                            # Add to results as a fake search result
                            csv_results.append({
                                "document_id": doc_id,
                                "content": latest.content[:500],  # First 500 chars
                                "similarity": 1.0  # Max similarity for direct match
                            })
                except Exception as e:
                    logger.error(f"Error checking document {doc_id}: {e}")
            
            logger.info(f"After fallback: {len(csv_results)} total CSV results")
        
        # Process CSV results
        for result in csv_results:
                doc_id = result.get("document_id")
                logger.info(f"Processing CSV result: doc_id={doc_id}")
                try:
                    versions = await versioning_service.get_versions(doc_id)
                    if not versions:
                        continue
                        
                    latest = versions[-1]
                    metadata = latest.metadata or {}
                    
                    if metadata.get("file_type") == "text/csv":
                        logger.info(f"Found CSV file: {metadata.get('filename')}")
                        import csv
                        import io
                        reader = csv.DictReader(io.StringIO(latest.content))
                        for row in reader:
                            cleaned_row = {k.strip().replace('\r', ''): v.strip() for k, v in row.items()}
                            logger.info(f"CSV row: {cleaned_row}")
                            
                            # Apply strict location filter
                            if strict_location and job_req.get("location"):
                                candidate_location = cleaned_row.get('location', '').lower().strip()
                                job_location = job_req["location"].lower().strip()
                                logger.info(f"Location check: candidate='{candidate_location}' vs job='{job_location}', strict={strict_location}")
                                if candidate_location != job_location:
                                    logger.info(f"Skipping candidate due to location mismatch")
                                    continue
                            
                            # Match candidate against job requirements
                            match = job_parser_service.match_candidate(cleaned_row, job_req)
                            logger.info(f"Match result for {cleaned_row.get('name')}: {match}")
                            if match["is_match"]:
                                # Create unique key to avoid duplicates
                                candidate_key = f"{cleaned_row.get('name', '').lower()}_{cleaned_row.get('role', '').lower()}"
                                
                                csv_candidates[candidate_key] = {
                                    **cleaned_row,
                                    "match_score": match["score"],
                                    "match_details": match,
                                    "csv_document_id": doc_id,
                                    "source": "csv"
                                }
                except Exception as e:
                    logger.error(f"Error processing CSV {doc_id}: {e}")
        
        # Convert to list
        csv_candidates_list = list(csv_candidates.values())
        
        logger.info(f"Found {len(csv_candidates_list)} CSV candidates")
        
        # STEP 2: RAG search for resumes using general search
        rag_candidates = []
        role = job_req.get('role') or ''
        skills = job_req.get('skills') or []
        rag_search_query = f"Find candidates with {role} skills: {', '.join(skills)}"
        
        # Get RAG search results
        rag_results = await vector_db_service.hybrid_search(
            query=rag_search_query,
            limit=50
        )
        
        # Process RAG results for PDF resumes
        pdf_candidates = {}  # document_id -> best candidate data
        
        for result in rag_results:
            doc_id = result.get("document_id")
            try:
                versions = await versioning_service.get_versions(doc_id)
                if not versions:
                    continue
                    
                latest = versions[-1]
                metadata = latest.metadata or {}
                
                if metadata.get("file_type") == "application/pdf":
                    filename = metadata.get("filename", "")
                    resume_text = latest.content.lower()
                    
                    # Calculate match score for PDF
                    score = 0
                    matches = []
                    
                    # Check role keywords
                    if job_req.get("role"):
                        role_keywords = [k for k in job_req["role"].lower().split() if len(k) > 2]
                        for keyword in role_keywords:
                            if keyword in resume_text:
                                score += 15
                                matches.append(f"Role: {keyword}")
                    
                    # Check skills
                    for skill in job_req.get("skills", []):
                        if skill and skill.lower() in resume_text:
                            score += 20
                            matches.append(f"Skill: {skill}")
                    
                    # Add vector similarity score
                    similarity = result.get("similarity", result.get("final_score", 0))
                    score += similarity * 30
                    
                    # Only include if score is above threshold
                    if score > 20:
                        name_from_filename = filename.replace('.pdf', '').replace('_Profile', '').replace('_profile', '').replace('_', ' ').replace('-', ' ').title()
                        
                        # Keep only the best scoring chunk for each document
                        if doc_id not in pdf_candidates or score > pdf_candidates[doc_id]["match_score"]:
                            pdf_candidates[doc_id] = {
                                "document_id": doc_id,
                                "filename": filename,
                                "name": name_from_filename,
                                "file_path": metadata.get("file_path"),
                                "cloudinary_url": metadata.get("cloudinary_url"),
                                "match_score": min(score, 100),
                                "match_details": {
                                    "matches": list(set(matches)),  # Remove duplicates
                                    "score": score,
                                    "similarity": similarity
                                },
                                "source": "rag_resume",
                                "resume_content_preview": result.get("content", "")[:300] + "..."
                            }
            except Exception as e:
                logger.error(f"Error processing PDF {doc_id}: {e}")
        
        # Convert to list
        rag_candidates = list(pdf_candidates.values())
        
        logger.info(f"Found {len(rag_candidates)} RAG resume candidates")
        
        # STEP 3: Merge and link CSV candidates with their resumes
        final_candidates = []
        
        # First add CSV candidates and try to link their resumes
        for csv_candidate in csv_candidates_list:
            candidate_name = csv_candidate.get('name', '').lower().split()[0]
            
            # Find matching resume
            matching_resume = None
            best_match_score = 0
            
            for rag_candidate in rag_candidates:
                rag_name = rag_candidate.get('name', '').lower().split()[0] if rag_candidate.get('name') else ""
                
                # Calculate name similarity
                name_score = 0
                if candidate_name == rag_name:
                    name_score = 100
                elif candidate_name in rag_name or rag_name in candidate_name:
                    name_score = 80
                elif candidate_name and rag_name and candidate_name[0] == rag_name[0]:
                    name_score = 60
                
                if name_score > best_match_score:
                    best_match_score = name_score
                    matching_resume = rag_candidate
            
            # Add CSV candidate with resume info
            final_candidate = {
                **csv_candidate,
                "has_resume": matching_resume is not None,
                "resume_document_id": matching_resume.get("document_id") if matching_resume else None,
                "resume_filename": matching_resume.get("filename") if matching_resume else None,
                "resume_file_path": matching_resume.get("file_path") if matching_resume else None,
                "resume_cloudinary_url": matching_resume.get("cloudinary_url") if matching_resume else None,
                "resume_match_score": best_match_score if matching_resume else 0,
                "combined_score": csv_candidate["match_score"] + (best_match_score * 0.3) if matching_resume else csv_candidate["match_score"]
            }
            final_candidates.append(final_candidate)
        
        # Add standalone RAG candidates (resumes without CSV entries)
        used_resume_ids = {c.get("resume_document_id") for c in final_candidates if c.get("resume_document_id")}
        
        for rag_candidate in rag_candidates:
            if rag_candidate["document_id"] not in used_resume_ids:
                final_candidates.append({
                    **rag_candidate,
                    "has_resume": True,
                    "resume_document_id": rag_candidate["document_id"],
                    "resume_filename": rag_candidate["filename"],
                    "resume_file_path": rag_candidate["file_path"],
                    "resume_cloudinary_url": rag_candidate.get("cloudinary_url"),
                    "combined_score": rag_candidate["match_score"]
                })
        
        # Sort by combined score
        final_candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # Limit results
        final_candidates = final_candidates[:max_results]
        
        if not final_candidates:
            return {
                "message": "No matching candidates found.",
                "job_requirements": job_req,
                "candidates": [],
                "csv_found": len(csv_candidates_list),
                "resumes_found": len(rag_candidates)
            }
        
        # STEP 4: Generate LLM summary
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
            google_api_key=GOOGLE_API_KEY
        )
        
        # Build context from candidates
        context_parts = []
        for i, candidate in enumerate(final_candidates, 1):
            if candidate.get("source") == "csv":
                context_parts.append(f"{i}. {candidate.get('name', 'Unknown')} (CSV + Resume)")
                context_parts.append(f"   Role: {candidate.get('role', 'N/A')}")
                context_parts.append(f"   Skills: {candidate.get('skills', 'N/A')}")
                context_parts.append(f"   Location: {candidate.get('location', 'N/A')}")
                context_parts.append(f"   Cost: {candidate.get('cost', 'N/A')}")
                context_parts.append(f"   Resume Available: {'Yes' if candidate.get('has_resume') else 'No'}")
            else:
                context_parts.append(f"{i}. {candidate.get('name', 'Unknown')} (Resume Only)")
                context_parts.append(f"   Filename: {candidate.get('filename', 'N/A')}")
                context_parts.append(f"   Skills Found: {', '.join([m.split(': ')[1] for m in candidate.get('match_details', {}).get('matches', []) if 'Skill:' in m])}")
            
            context_parts.append(f"   Match Score: {candidate.get('combined_score', 0):.1f}")
            context_parts.append("")
        
        context = "\n".join(context_parts)
        
        # Generate answer
        prompt = f"""
Based on the job requirements and matching candidates found, provide a comprehensive summary.

Job Requirements:
- Role: {job_req.get('role', 'N/A')}
- Skills: {', '.join(job_req.get('skills', []))}
- Location: {job_req.get('location', 'N/A')}
- Cost Budget: {job_req.get('cost', 'N/A')}

Search Results:
- CSV Candidates Found: {len(csv_candidates)}
- Resume Candidates Found: {len(rag_candidates)}
- Total Final Candidates: {len(final_candidates)}

Matching Candidates:
{context}

Provide a summary of:
1. How well the candidates match the requirements
2. Availability of resumes for download
3. Recommendations for next steps
"""
        
        answer = await llm.ainvoke(prompt)
        
        logger.info(f"Job search completed: {len(final_candidates)} final candidates")
        
        return {
            "message": f"Found {len(final_candidates)} matching candidates",
            "job_requirements": job_req,
            "search_summary": {
                "csv_candidates_found": len(csv_candidates_list),
                "resume_candidates_found": len(rag_candidates),
                "final_candidates": len(final_candidates)
            },
            "candidates": final_candidates,
            "answer": answer.content if hasattr(answer, 'content') else str(answer)
        }
        
    except Exception as e:
        logger.error(f"Job search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")

    except Exception as e:
        logger.error(f"Job search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")

@router.get("/download/resume/{document_id}")
async def download_resume(document_id: str):
    """
    Download resume PDF by document ID
    """
    try:
        # Get document versions
        versions = await versioning_service.get_versions(document_id)
        if not versions:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        latest = versions[-1]
        metadata = latest.metadata or {}
        
        # Check if it's a PDF
        if metadata.get("file_type") != "application/pdf":
            raise HTTPException(status_code=400, detail="Document is not a PDF resume")
        
        filename = metadata.get("filename", f"resume_{document_id}.pdf")
        
        # Try to get from file path first
        file_path = metadata.get("file_path")
        if file_path:
            from pathlib import Path
            if Path(file_path).exists():
                with open(file_path, "rb") as f:
                    content = f.read()
                
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
        
        # Try to get from Cloudinary
        cloudinary_url = metadata.get("cloudinary_url")
        if cloudinary_url:
            import requests
            response = requests.get(cloudinary_url)
            if response.status_code == 200:
                return StreamingResponse(
                    io.BytesIO(response.content),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
        
        # Fallback: try to get from content_bytes in versioning
        if latest.content_bytes:
            return StreamingResponse(
                io.BytesIO(latest.content_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        raise HTTPException(status_code=404, detail="Resume file not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
@router.get("/documents")
async def list_documents():
    """
    List all uploaded documents
    """
    try:
        # Get all document IDs from vector database
        doc_ids = []
        if vector_db_service.conn:
            with vector_db_service.conn.cursor() as cur:
                cur.execute(f"SELECT DISTINCT document_id FROM {VECTOR_TABLE}")
                doc_ids = [row[0] for row in cur.fetchall()]
        
        documents = []
        for doc_id in doc_ids:
            try:
                versions = await versioning_service.get_versions(doc_id)
                if versions:
                    latest = versions[-1]
                    metadata = latest.metadata or {}
                    
                    # Count chunks for this document
                    chunk_count = 0
                    if vector_db_service.conn:
                        with vector_db_service.conn.cursor() as cur:
                            cur.execute(f"SELECT COUNT(*) FROM {VECTOR_TABLE} WHERE document_id = %s", (doc_id,))
                            chunk_count = cur.fetchone()[0]
                    
                    documents.append({
                        "id": doc_id,
                        "name": metadata.get("filename", f"Document {doc_id}"),
                        "chunks_created": chunk_count,
                        "file_type": metadata.get("file_type", "unknown"),
                        "upload_date": latest.created_at.isoformat() if hasattr(latest, 'created_at') else None
                    })
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
        
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks
    """
    try:
        # Delete from vector database
        if vector_db_service.conn:
            with vector_db_service.conn.cursor() as cur:
                cur.execute(f"DELETE FROM {VECTOR_TABLE} WHERE document_id = %s", (document_id,))
                vector_db_service.conn.commit()
        
        # Delete versions
        await versioning_service.delete_document(document_id)
        
        # Remove from teams if applicable
        await team_service.remove_document_from_all_teams(document_id)
        
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")