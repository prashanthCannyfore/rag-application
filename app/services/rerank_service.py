"""
Re-ranking service for improved RAG accuracy
"""
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class ReRankService:
    """Service for re-ranking search results"""
    
    def __init__(self):
        if GOOGLE_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.1,
                google_api_key=GOOGLE_API_KEY
            )
        else:
            self.llm = None
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Re-rank documents based on relevance to query
        
        Args:
            query: User's question
            documents: List of documents with content and scores
            top_k: Number of top results to return
        
        Returns:
            Re-ranked documents with relevance scores
        """
        if not documents:
            return []
        
        if not self.llm:
            # Fallback: simple scoring
            return self._simple_rerank(query, documents, top_k)
        
        # Build prompt for re-ranking
        doc_texts = "\n\n".join([
            f"[{i+1}] {doc.get('content', '')[:500]}"
            for i, doc in enumerate(documents)
        ])
        
        prompt = f"""You are a relevance scoring assistant. 
Given the user query and a list of documents, score each document 
on how well it answers the query.

Query: {query}

Documents:
{doc_texts}

Respond with ONLY a JSON array of scores (0-1) for each document, 
in the same order. Example: [0.9, 0.3, 0.7, 0.1, 0.5]"""
        
        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate
            
            chain = PromptTemplate.from_template(prompt) | self.llm | StrOutputParser()
            response = await chain.ainvoke({})
            
            # Parse scores from response
            scores = self._parse_scores(response, len(documents))
            
            # Re-rank documents
            scored_docs = []
            for i, doc in enumerate(documents):
                rerank_score = scores[i] if i < len(scores) else 0.0
                # Combine original similarity with re-rank score
                original_score = doc.get("similarity", doc.get("score", 0))
                final_score = (original_score * 0.4) + (rerank_score * 0.6)
                
                scored_docs.append({
                    **doc,
                    "rerank_score": rerank_score,
                    "final_score": final_score
                })
            
            # Sort by final score
            scored_docs.sort(key=lambda x: x["final_score"], reverse=True)
            
            return scored_docs[:top_k]
            
        except Exception as e:
            print(f"Re-ranking error: {e}")
            return self._simple_rerank(query, documents, top_k)
    
    def _simple_rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """Simple re-ranking based on keyword matching"""
        query_words = set(query.lower().split())
        
        scored_docs = []
        for doc in documents:
            content = doc.get("content", "").lower()
            
            # Count query word matches
            matches = sum(1 for word in query_words if word in content)
            keyword_score = matches / max(len(query_words), 1)
            
            # Combine with original score
            original_score = doc.get("similarity", doc.get("score", 0))
            final_score = (original_score * 0.6) + (keyword_score * 0.4)
            
            scored_docs.append({
                **doc,
                "rerank_score": keyword_score,
                "final_score": final_score
            })
        
        scored_docs.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_docs[:top_k]
    
    def _parse_scores(self, response: str, expected_count: int) -> List[float]:
        """Parse scores from LLM response"""
        import re
        import json
        
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[.*?\]', response)
            if json_match:
                scores = json.loads(json_match.group())
                if isinstance(scores, list) and len(scores) == expected_count:
                    return [max(0, min(1, float(s))) for s in scores]
        except:
            pass
        
        # Fallback: try to parse comma-separated values
        try:
            scores = [float(s.strip()) for s in response.split(",")]
            if len(scores) == expected_count:
                return [max(0, min(1, s)) for s in scores]
        except:
            pass
        
        # Return neutral scores
        return [0.5] * expected_count

# Singleton
rerank_service = ReRankService()