"""
Generate a test PDF for RAG testing
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Create a PDF with detailed information about PDF extraction
c = canvas.Canvas("test_document.pdf", pagesize=letter)
width, height = letter

# Title
c.setFont("Helvetica-Bold", 16)
c.drawString(1 * inch, height - 1 * inch, "PDF Text Extraction Process")

# Subtitle
c.setFont("Helvetica", 12)
c.drawString(1 * inch, height - 1.5 * inch, "A comprehensive guide to extracting text from PDF documents.")

# Content
c.setFont("Helvetica", 10)
text = c.beginText(1 * inch, height - 2.2 * inch)
text.setLeading(14)

lines = [
    "",
    "1. Introduction to PDF Text Extraction",
    "PDF text extraction is the process of converting PDF documents into plain text that can be processed,",
    "searched, and analyzed by applications. This is essential for building search engines, document analysis",
    "systems, and RAG (Retrieval-Augmented Generation) applications.",
    "",
    "2. How PDF Text Extraction Works",
    "The PDF text extraction process involves several steps:",
    "",
    "Step 1: Parse the PDF Structure",
    "- Read the PDF file structure including objects, cross-reference tables, and trailers",
    "- Identify pages, fonts, and content streams",
    "",
    "Step 2: Extract Content Streams",
    "- Access the content streams of each page",
    "- Handle different encodings and font mappings",
    "",
    "Step 3: Convert to Text",
    "- Interpret content stream operators",
    "- Map glyphs to characters using font information",
    "- Reconstruct the text content",
    "",
    "Step 4: Handle Special Cases",
    "- Dealing with compressed streams (FlateDecode, LZWDecode)",
    "- Handling encoded text (Unicode, CID fonts)",
    "- Extracting text from form fields and annotations",
    "",
    "3. Common PDF Text Extraction Tools",
    "Popular libraries for PDF text extraction include:",
    "- PyPDF2: A pure-python PDF library capable of splitting, merging, and extracting text",
    "- pypdf: A modern fork of PyPDF2 with improved text extraction",
    "- pdfplumber: Excellent for extracting text and tables from PDFs",
    "- pdfminer.six: A powerful tool for text extraction with fine-grained control",
    "",
    "4. Challenges in PDF Text Extraction",
    "PDF text extraction can be challenging due to:",
    "- PDFs are designed for layout, not text extraction",
    "- Fonts may not embed complete character mappings",
    "- Text may be positioned absolutely rather than as a flow",
    "- Some PDFs contain scanned images instead of actual text",
    "",
    "5. Best Practices",
    "For reliable PDF text extraction:",
    "- Use the right library for your use case",
    "- Handle encoding issues gracefully",
    "- Validate extracted text quality",
    "- Consider pre-processing scanned PDFs with OCR",
    "",
    "6. Conclusion",
    "PDF text extraction is a crucial step in document processing pipelines. While PDFs excel at",
    "preserving layout, extracting meaningful text requires understanding the PDF structure and",
    "handling various encoding and formatting challenges. The libraries mentioned above provide",
    "robust solutions for most text extraction needs."
]

for line in lines:
    text.textLine(line)

c.drawText(text)
c.save()

print("Test PDF created: test_document.pdf")
print("This PDF contains detailed information about PDF text extraction.")
