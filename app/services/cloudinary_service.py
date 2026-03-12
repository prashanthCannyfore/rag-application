"""
Cloudinary service for reliable PDF storage and delivery
"""
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

class CloudinaryService:
    """Service for uploading and retrieving PDFs from Cloudinary"""
    
    def __init__(self):
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
            api_key=os.getenv("CLOUDINARY_API_KEY", ""),
            api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
            secure=True
        )
        self.enabled = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
    
    def upload_pdf(self, pdf_bytes: bytes, filename: str, document_id: str) -> str:
        """
        Upload PDF to Cloudinary and return the URL
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename
            document_id: Unique document ID
            
        Returns:
            Cloudinary URL for the PDF
        """
        if not self.enabled:
            return None
        
        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                pdf_bytes,
                resource_type="raw",  # For non-image files
                public_id=f"resumes/{document_id}",
                overwrite=True,
                format="pdf"
            )
            
            return result.get('secure_url')
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            return None
    
    def get_pdf_url(self, document_id: str) -> str:
        """
        Get the Cloudinary URL for a PDF
        
        Args:
            document_id: Document ID
            
        Returns:
            Cloudinary URL
        """
        if not self.enabled:
            return None
        
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        return f"https://res.cloudinary.com/{cloud_name}/raw/upload/resumes/{document_id}.pdf"
    
    def delete_pdf(self, document_id: str) -> bool:
        """Delete PDF from Cloudinary"""
        if not self.enabled:
            return False
        
        try:
            cloudinary.uploader.destroy(
                f"resumes/{document_id}",
                resource_type="raw"
            )
            return True
        except Exception as e:
            print(f"Cloudinary delete error: {e}")
            return False

# Singleton
cloudinary_service = CloudinaryService()
