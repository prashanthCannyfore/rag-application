"""
Test PDF extraction to see what content is being retrieved
"""
from app.services.pdf_service import pdf_service

# Read the test PDF
with open("test_document.pdf", "rb") as f:
    pdf_content = f.read()

print(f"PDF file size: {len(pdf_content)} bytes")

# Extract text
text = pdf_service.extract_text_from_pdf(pdf_content, "test_document.pdf")
print(f"\nExtracted text length: {len(text)} characters")
print(f"\nFirst 500 characters:\n{text[:500]}")
print(f"\nLast 500 characters:\n{text[-500:]}")

# Extract metadata
metadata = pdf_service.extract_metadata_from_pdf(pdf_content)
print(f"\nMetadata: {metadata}")
