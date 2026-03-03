"""
Document chunking service for RAG
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Chunk:
    """Represents a document chunk"""
    content: str
    start_index: int
    end_index: int
    metadata: Dict

class ChunkingService:
    """Service for splitting documents into chunks"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # Paragraphs
            "\n",    # Lines
            ". ",    # Sentences
            " ",     # Words
            ""       # Characters
        ]
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks using recursive splitting"""
        chunks = []
        
        # Clean text
        text = self._clean_text(text)
        
        # Try splitting with different separators
        for separator in self.separators:
            if not separator:
                # Character-level splitting
                chunks = self._split_by_chars(text)
                break
            
            # Split by separator
            parts = text.split(separator)
            
            if len(parts) > 1:
                chunks = self._merge_parts(parts, separator)
                break
        
        # If no chunks created, use character splitting
        if not chunks:
            chunks = self._split_by_chars(text)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        return text.strip()
    
    def _split_by_chars(self, text: str) -> List[str]:
        """Split text by characters with overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to split at word boundary
            if end < len(text):
                last_space = text[start:end].rfind(' ')
                if last_space > self.chunk_size * 0.5:
                    end = start + last_space
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
        
        return chunks
    
    def _merge_parts(self, parts: List[str], separator: str) -> List[str]:
        """Merge parts into chunks"""
        chunks = []
        current_chunk = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if adding this part would exceed chunk size
            if len(current_chunk) + len(separator) + len(part) > self.chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part
            else:
                if current_chunk:
                    current_chunk += separator + part
                else:
                    current_chunk = part
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def split_by_headings(self, text: str, heading_pattern: str = r'^#{1,6}\s') -> List[Chunk]:
        """Split text by headings"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_heading = ""
        
        for line in lines:
            # Check if line is a heading
            if re.match(heading_pattern, line):
                # Save previous chunk
                if current_chunk:
                    content = '\n'.join(current_chunk)
                    chunks.append(Chunk(
                        content=content,
                        start_index=0,
                        end_index=len(content),
                        metadata={"heading": current_heading}
                    ))
                
                current_heading = line.strip('#').strip()
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Save final chunk
        if current_chunk:
            content = '\n'.join(current_chunk)
            chunks.append(Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                metadata={"heading": current_heading}
            ))
        
        return chunks
    
    def split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Split by common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def split_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    def create_chunks_with_metadata(
        self,
        text: str,
        document_id: str,
        document_name: str = "",
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> List[Dict]:
        """Create chunks with metadata for vector storage"""
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        # Create new service instance with specified parameters
        service = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        chunks = service.split_text(text)
        
        # Add metadata to each chunk
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "content": chunk,
                "document_id": document_id,
                "document_name": document_name,
                "chunk_index": i,
                "chunk_size": len(chunk),
                "metadata": {
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            })
        
        return result
    
    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks for text"""
        return len(self.split_text(text))

# Default instance
chunking_service = ChunkingService()