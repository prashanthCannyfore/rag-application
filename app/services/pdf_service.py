"""
PDF processing service for RAG
"""
import os
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)


class PDFService:
    """Service for processing PDF files"""
    
    def __init__(self):
        self.pdf_library = self._detect_pdf_library()
    
    def _detect_pdf_library(self) -> str:
        """Detect which PDF library is available"""
        try:
            import pdfplumber
            return "pdfplumber"
        except ImportError:
            try:
                import pypdf
                return "pypdf"
            except ImportError:
                try:
                    import PyPDF2
                    return "pypdf2"
                except ImportError:
                    return "none"
    
    def extract_text_from_pdf(self, pdf_content: bytes, filename: str = "") -> str:
        """
        Extract text from PDF content
        
        Args:
            pdf_content: PDF file bytes
            filename: Optional filename for logging
            
        Returns:
            Extracted text from PDF
        """
        if self.pdf_library == "pdfplumber":
            return self._extract_with_pdfplumber(pdf_content)
        elif self.pdf_library == "pypdf":
            return self._extract_with_pypdf(pdf_content)
        elif self.pdf_library == "pypdf2":
            return self._extract_with_pypdf2(pdf_content)
        else:
            raise ImportError(
                "No PDF library available. Install with: pip install pdfplumber or pip install pypdf"
            )
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> str:
        """Extract text using pdfplumber (best for text extraction)"""
        import pdfplumber
        from io import BytesIO
        
        pdf_buffer = BytesIO(pdf_content)
        text_parts = []
        
        with pdfplumber.open(pdf_buffer) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n".join(text_parts)
    
    def _extract_with_pypdf(self, pdf_content: bytes) -> str:
        """Extract text using pypdf"""
        from pypdf import PdfReader
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_content)
        reader = PdfReader(pdf_buffer)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n".join(text_parts)
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> str:
        """Extract text using PyPDF2"""
        from PyPDF2 import PdfReader
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_content)
        reader = PdfReader(pdf_buffer)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n".join(text_parts)
    
    def extract_metadata_from_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract document metadata from PDF"""
        if self.pdf_library == "pdfplumber":
            return self._metadata_with_pdfplumber(pdf_content)
        elif self.pdf_library == "pypdf":
            return self._metadata_with_pypdf(pdf_content)
        elif self.pdf_library == "pypdf2":
            return self._metadata_with_pypdf2(pdf_content)
        return {}
    
    def _metadata_with_pdfplumber(self, pdf_content: bytes) -> Dict[str, Any]:
        """Get metadata using pdfplumber"""
        import pdfplumber
        from io import BytesIO
        
        pdf_buffer = BytesIO(pdf_content)
        with pdfplumber.open(pdf_buffer) as pdf:
            info = pdf.metadata
            return {
                "title": info.get("Title") if info else None,
                "author": info.get("Author") if info else None,
                "subject": info.get("Subject") if info else None,
                "producer": info.get("Producer") if info else None,
                "pages": len(pdf.pages)
            }
    
    def _metadata_with_pypdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Get metadata using pypdf"""
        from pypdf import PdfReader
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_content)
        reader = PdfReader(pdf_buffer)
        info = reader.metadata
        return {
            "title": info.title if info else None,
            "author": info.author if info else None,
            "subject": info.subject if info else None,
            "producer": info.producer if info else None,
            "pages": len(reader.pages)
        }
    
    def _metadata_with_pypdf2(self, pdf_content: bytes) -> Dict[str, Any]:
        """Get metadata using PyPDF2"""
        from PyPDF2 import PdfReader
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_content)
        reader = PdfReader(pdf_buffer)
        info = reader.metadata
        return {
            "title": info.title if info else None,
            "author": info.author if info else None,
            "subject": info.subject if info else None,
            "producer": info.producer if info else None,
            "pages": len(reader.pages)
        }


# Singleton instance
pdf_service = PDFService()
