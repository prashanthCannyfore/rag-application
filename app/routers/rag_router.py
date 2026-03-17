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
from app.services.candidate_matching_service import candidate_matching_service
from app.services.resume_parser_service import resume_parser_service, clean_text
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
    Enhanced job search with improved candidate matching and CSV-resume linking
    """
    try:
        # Parse job description
        job_req = job_parser_service.parse_job_description(job_description)
        logger.info(f"Job search: {job_req}, strict_location: {strict_location}")
        
        # STEP 1: Get CSV candidates efficiently with enhanced search
        skills_query = ",".join(job_req.get("skills", []))
        role_query = job_req.get("role", "")
        
        # FALLBACK: If no structured data extracted, use raw text for keyword search
        if not skills_query and not role_query:
            # Use raw text as fallback search terms
            raw_text = job_req.get("raw_text", "").lower()
            # Extract potential keywords from raw text
            fallback_keywords = []
            common_tech_terms = [
                'react', 'angular', 'vue', 'javascript', 'python', 'java', 'node', 'sql', 
                'mongodb', 'postgresql', 'mysql', 'oracle', 'aws', 'azure', 'docker', 
                'kubernetes', 'ibm', 'iib', 'ace', 'mq', 'websphere', 'esql', 'developer',
                'engineer', 'programmer', 'fullstack', 'backend', 'frontend', 'integration'
            ]
            
            for term in common_tech_terms:
                if term in raw_text:
                    fallback_keywords.append(term)
            
            if fallback_keywords:
                skills_query = ",".join(fallback_keywords[:5])  # Limit to top 5 keywords
                logger.info(f"Using fallback keywords: {skills_query}")
            else:
                # Last resort: use first few words of raw text
                words = raw_text.split()[:3]  # Take first 3 words
                skills_query = " ".join(words) if words else "developer"
                logger.info(f"Using raw text fallback: {skills_query}")
        
        csv_candidates = await vector_db_service.get_csv_candidates(
            skills_query=skills_query, 
            role_query=role_query
        )
        
        # Filter and score CSV candidates
        qualified_csv_candidates = []
        for candidate in csv_candidates:
            match_result = candidate_matching_service.match_candidate_to_job(
                candidate, job_req, strict_location
            )
            
            if match_result["is_match"]:
                candidate.update({
                    "match_score": match_result["total_score"] * 100,
                    "match_details": match_result,
                    "source": "csv"
                })
                qualified_csv_candidates.append(candidate)
        
        logger.info(f"Found {len(qualified_csv_candidates)} qualified CSV candidates")
        
        # STEP 2: Get resume candidates using hybrid search
        role = job_req.get('role', '')
        skills = job_req.get('skills', [])
        rag_search_query = f"{role} {' '.join(skills)}".strip()
        
        # FALLBACK: If no meaningful search query, use raw text
        if not rag_search_query or rag_search_query.isspace():
            raw_text = job_req.get("raw_text", "")
            if raw_text:
                rag_search_query = raw_text
                logger.info(f"Using raw text for resume search: {rag_search_query}")
            else:
                rag_search_query = "developer"  # Ultimate fallback
                logger.info("Using ultimate fallback: developer")
        
        rag_results = await vector_db_service.hybrid_search(
            query=rag_search_query,
            limit=50,
            file_type_filter="application/pdf"
        )
        
        # Process resume results
        resume_candidates = {}  # document_id -> best candidate data
        
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
                    resume_text = latest.content
                    
                    # Parse resume to extract structured information
                    parsed_resume = resume_parser_service.parse_resume(resume_text, filename)
                    
                    # Enhanced scoring using candidate matching service
                    resume_candidate = {
                        "name": parsed_resume["name"],
                        "skills": parsed_resume["skills"],
                        "role": "",  # Will be inferred from content
                        "location": parsed_resume["location"] or "",
                        "cost": parsed_resume["salary"] or "",
                        "experience": parsed_resume["experience"]  # Include experience for validation
                    }
                    
                    match_result = candidate_matching_service.match_candidate_to_job(
                        resume_candidate, job_req, False  # Not strict for resumes
                    )
                    
                    # Add vector similarity boost
                    vector_score = result.get("final_score", result.get("similarity", 0))
                    total_score = (match_result["total_score"] * 0.7) + (vector_score * 0.3)
                    
                    if total_score > 0.3:  # Lower threshold for resume discovery
                        # Keep only the best scoring chunk for each document
                        if doc_id not in resume_candidates or total_score > resume_candidates[doc_id]["match_score"]:
                            resume_candidates[doc_id] = {
                                "document_id": doc_id,
                                "filename": filename,
                                "name": resume_candidate["name"],
                                "skills": parsed_resume["skills"],
                                "location": parsed_resume["location"] or "Not specified",
                                "cost": parsed_resume["salary"] or "Not specified",
                                "experience": parsed_resume["experience"] or "Not specified",
                                "email": parsed_resume.get("email"),
                                "phone": parsed_resume.get("phone"),
                                "education": parsed_resume.get("education", []),
                                "certifications": parsed_resume.get("certifications", []),
                                "companies": parsed_resume.get("companies", []),
                                "summary": parsed_resume.get("summary"),
                                "notice_period": parsed_resume.get("notice_period"),
                                "file_path": metadata.get("file_path"),
                                "cloudinary_url": metadata.get("cloudinary_url"),
                                "match_score": total_score * 100,
                                "match_details": match_result,
                                "source": "resume",
                                "resume_content_preview": clean_text(resume_text[:500]) + "...",
                                "vector_similarity": vector_score
                            }
            except Exception as e:
                logger.error(f"Error processing resume {doc_id}: {e}")
        
        resume_candidates_list = list(resume_candidates.values())
        logger.info(f"Found {len(resume_candidates_list)} qualified resume candidates")
        
        # STEP 3: Enhanced CSV-Resume linking
        final_candidates = []
        
        # Link CSV candidates with their resumes
        for csv_candidate in qualified_csv_candidates:
            csv_name = csv_candidate.get('name', '')
            
            # Find best matching resume
            best_resume = candidate_matching_service.find_best_resume_match(
                csv_name, resume_candidates_list
            )
            
            # Create enhanced candidate profile
            final_candidate = {
                **csv_candidate,
                "has_resume": best_resume is not None,
                "resume_document_id": best_resume.get("document_id") if best_resume else None,
                "resume_filename": best_resume.get("filename") if best_resume else None,
                "resume_file_path": best_resume.get("file_path") if best_resume else None,
                "resume_cloudinary_url": best_resume.get("cloudinary_url") if best_resume else None,
                "resume_match_confidence": 0.0,
                "combined_score": csv_candidate["match_score"]
            }
            
            if best_resume:
                # Calculate name matching confidence
                name_similarity = candidate_matching_service.calculate_name_similarity(
                    csv_name, best_resume.get("name", "")
                )
                final_candidate["resume_match_confidence"] = name_similarity * 100

                # Merge rich resume fields into CSV candidate
                for field in ["email", "phone", "education", "certifications", "companies", "summary", "notice_period"]:
                    if best_resume.get(field):
                        final_candidate[field] = best_resume[field]

                # IMPORTANT: Merge experience data from resume into CSV candidate
                if best_resume.get("experience") and best_resume["experience"] != "Not specified":
                    final_candidate["experience"] = best_resume["experience"]
                    
                    # Re-evaluate match with actual experience data
                    csv_candidate_with_experience = {**csv_candidate, "experience": best_resume["experience"]}
                    updated_match = candidate_matching_service.match_candidate_to_job(
                        csv_candidate_with_experience, job_req, strict_location
                    )
                    
                    if updated_match["is_match"]:
                        final_candidate["match_score"] = updated_match["total_score"] * 100
                        final_candidate["match_details"] = updated_match
                
                # Boost combined score if resume is well-matched
                resume_boost = best_resume["match_score"] * 0.2 * name_similarity
                final_candidate["combined_score"] += resume_boost
            
            final_candidates.append(final_candidate)
        
        # Add standalone resume candidates (not in CSV)
        used_resume_ids = {c.get("resume_document_id") for c in final_candidates if c.get("resume_document_id")}
        
        for resume in resume_candidates_list:
            if resume["document_id"] not in used_resume_ids:
                # Check if this resume name matches any CSV candidate we might have missed
                csv_match = None
                for csv_cand in qualified_csv_candidates:
                    similarity = candidate_matching_service.calculate_name_similarity(
                        csv_cand.get("name", ""), resume.get("name", "")
                    )
                    if similarity > 0.8:  # High confidence match
                        csv_match = csv_cand
                        break
                
                if csv_match:
                    # Update the existing final candidate instead of creating duplicate
                    for final_cand in final_candidates:
                        if final_cand.get("name", "").lower() == csv_match.get("name", "").lower():
                            final_cand.update({
                                "has_resume": True,
                                "resume_document_id": resume["document_id"],
                                "resume_filename": resume["filename"],
                                "resume_file_path": resume["file_path"],
                                "resume_cloudinary_url": resume.get("cloudinary_url"),
                                "resume_match_confidence": similarity * 100,
                                "combined_score": final_cand["combined_score"] + (resume["match_score"] * 0.3)
                            })
                            break
                else:
                    # Add as standalone resume candidate
                    final_candidates.append({
                        "name": resume["name"],
                        "role": "Extracted from Resume",
                        "skills": resume.get("skills", "See resume content"),
                        "location": resume.get("location", "Not specified"),
                        "cost": resume.get("cost", "Not specified"),
                        "experience": resume.get("experience", "Not specified"),
                        "email": resume.get("email"),
                        "phone": resume.get("phone"),
                        "education": resume.get("education", []),
                        "certifications": resume.get("certifications", []),
                        "companies": resume.get("companies", []),
                        "summary": resume.get("summary"),
                        "notice_period": resume.get("notice_period"),
                        "match_score": resume["match_score"],
                        "match_details": resume["match_details"],
                        "source": "resume_only",
                        "has_resume": True,
                        "resume_document_id": resume["document_id"],
                        "resume_filename": resume["filename"],
                        "resume_file_path": resume["file_path"],
                        "resume_cloudinary_url": resume.get("cloudinary_url"),
                        "resume_match_confidence": 100.0,
                        "combined_score": resume["match_score"],
                        "resume_content_preview": resume.get("resume_content_preview", "")
                    })
        
        # Sort by combined score and limit results
        final_candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        final_candidates = final_candidates[:max_results]
        
        if not final_candidates:
            return {
                "message": "No matching candidates found. Try adjusting your search criteria.",
                "job_requirements": job_req,
                "candidates": [],
                "search_summary": {
                    "csv_candidates_found": len(qualified_csv_candidates),
                    "resume_candidates_found": len(resume_candidates_list),
                    "final_candidates": 0
                }
            }
        
        # STEP 4: Generate enhanced summary
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
            google_api_key=GOOGLE_API_KEY
        )
        
        # Build detailed context
        context_parts = []
        for i, candidate in enumerate(final_candidates, 1):
            context_parts.append(f"**Candidate {i}: {candidate.get('name', 'Unknown')}**")
            context_parts.append(f"  • Role: {candidate.get('role', 'N/A')}")
            context_parts.append(f"  • Skills: {candidate.get('skills', 'N/A')}")
            context_parts.append(f"  • Location: {candidate.get('location', 'N/A')}")
            context_parts.append(f"  • Cost: {candidate.get('cost', 'N/A')}")
            context_parts.append(f"  • Match Score: {candidate.get('combined_score', 0):.1f}%")
            context_parts.append(f"  • Resume Available: {'Yes' if candidate.get('has_resume') else 'No'}")
            
            if candidate.get('has_resume'):
                confidence = candidate.get('resume_match_confidence', 0)
                context_parts.append(f"  • Resume Match Confidence: {confidence:.1f}%")
            
            # Add match reasoning
            match_details = candidate.get('match_details', {})
            if match_details.get('reasoning'):
                context_parts.append(f"  • Match Reasons: {'; '.join(match_details['reasoning'])}")
            
            context_parts.append("")
        
        context = "\n".join(context_parts)
        
        prompt = f"""
You are a recruitment assistant. Based on the job requirements and candidate search results, provide a professional summary.

**Job Requirements:**
- Role: {job_req.get('role', 'N/A')}
- Required Skills: {', '.join(job_req.get('skills', []))}
- Location: {job_req.get('location', 'N/A')}
- Budget: {job_req.get('cost', 'N/A')}

**Search Results Summary:**
- CSV Database Candidates: {len(qualified_csv_candidates)}
- Resume Database Candidates: {len(resume_candidates_list)}
- Total Qualified Candidates: {len(final_candidates)}

**Top Matching Candidates:**
{context}

Please provide:
1. A brief overview of the candidate quality and match strength
2. Key highlights of the top 3 candidates
3. Recommendations for next steps in the hiring process
4. Any gaps or concerns in the candidate pool

Format your response professionally for a hiring manager.
"""
        
        answer = await llm.ainvoke(prompt)
        
        logger.info(f"Enhanced job search completed: {len(final_candidates)} final candidates")
        
        return {
            "message": f"Found {len(final_candidates)} qualified candidates matching your requirements",
            "job_requirements": job_req,
            "search_summary": {
                "csv_candidates_found": len(qualified_csv_candidates),
                "resume_candidates_found": len(resume_candidates_list),
                "final_candidates": len(final_candidates),
                "search_query_used": rag_search_query
            },
            "candidates": final_candidates,
            "answer": answer.content if hasattr(answer, 'content') else str(answer)
        }
        
    except Exception as e:
        logger.error(f"Enhanced job search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")
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