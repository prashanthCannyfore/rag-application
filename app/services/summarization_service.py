"""
Summarization service for RAG
"""
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class SummarizationService:
    """Service for generating summaries of documents and search results"""
    
    def __init__(self):
        if GOOGLE_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.3,
                google_api_key=GOOGLE_API_KEY
            )
        else:
            self.llm = None
    
    async def summarize_document(
        self,
        content: str,
        max_length: int = 200
    ) -> str:
        """
        Summarize a document or chunk
        
        Args:
            content: Document content
            max_length: Maximum summary length
        
        Returns:
            Summary text
        """
        if not self.llm:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        prompt = f"""Summarize the following text in {max_length} characters or less.
Keep the key information and main points.

Text:
{{text}}

Summary:"""
        
        try:
            chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            summary = await chain.ainvoke({"text": content[:5000]})
            return summary.strip()
        except Exception as e:
            print(f"Summarization error: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content
    
    async def summarize_search_results(
        self,
        query: str,
        documents: List[Dict],
        max_length: int = 300
    ) -> str:
        """
        Summarize multiple search results into a coherent answer
        
        Args:
            query: User's question
            documents: List of relevant documents
            max_length: Maximum summary length
        
        Returns:
            Coherent summary answering the query
        """
        if not documents:
            return "No relevant documents found."
        
        if not self.llm:
            # Simple concatenation
            combined = "\n\n".join([doc.get("content", "") for doc in documents])
            return combined[:max_length] + "..." if len(combined) > max_length else combined
        
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(documents[:5]):  # Use top 5
            content = doc.get("content", "")[:1000]
            context_parts.append(f"[Document {i+1}]: {content}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Based on the following documents, provide a concise answer 
to the user's question. Cite the document numbers when referencing information.

User Question: {query}

Relevant Documents:
{context}

Provide a clear, concise answer with sources:"""
        
        try:
            chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            summary = await chain.ainvoke({})
            return summary.strip()
        except Exception as e:
            print(f"Search summarization error: {e}")
            return "Error generating summary."
    
    async def generate_key_points(
        self,
        content: str,
        num_points: int = 5
    ) -> List[str]:
        """
        Extract key points from a document
        
        Args:
            content: Document content
            num_points: Number of key points to extract
        
        Returns:
            List of key points
        """
        if not self.llm:
            return [content[:100] + "..."]
        
        prompt = f"""Extract {num_points} key points from the following text.
Format as a numbered list.

Text:
{{text}}

Key Points:"""
        
        try:
            chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            result = await chain.ainvoke({"text": content[:3000]})
            
            # Parse numbered list
            points = []
            for line in result.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    points.append(line)
            
            return points[:num_points]
        except Exception as e:
            print(f"Key points extraction error: {e}")
            return [content[:100] + "..."]
    
    async def compare_documents(
        self,
        documents: List[Dict],
        comparison_points: List[str] = None
    ) -> str:
        """
        Compare multiple documents
        
        Args:
            documents: List of documents to compare
            comparison_points: Points to compare (optional)
        
        Returns:
            Comparison summary
        """
        if not documents or len(documents) < 2:
            return "Need at least 2 documents to compare."
        
        if not self.llm:
            return "Comparison requires LLM."
        
        # Build comparison context
        doc_summaries = []
        for i, doc in enumerate(documents):
            content = doc.get("content", "")[:500]
            doc_summaries.append(f"[Doc {i+1}]: {content}")
        
        context = "\n\n".join(doc_summaries)
        
        prompt = f"""Compare the following documents. 
Highlight similarities and differences.

Documents:
{context}

Comparison:"""
        
        try:
            chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            comparison = await chain.ainvoke({})
            return comparison.strip()
        except Exception as e:
            print(f"Document comparison error: {e}")
            return "Error comparing documents."

# Singleton
summarization_service = SummarizationService()