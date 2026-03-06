"""
Debug search to see what chunks are being retrieved
"""
import asyncio
from app.services.vector_db_service import vector_db_service
from app.services.embeddings_service import embeddings_service

async def debug_search():
    # First, let's see what documents are in the database
    count = await vector_db_service.get_document_count()
    print(f"Total documents in vector DB: {count}")
    
    # Search for "common PDF text extraction tools"
    query = "common PDF text extraction tools"
    print(f"\nSearching for: '{query}'")
    
    # Get query embedding
    query_embedding = embeddings_service.embed_query(query)
    print(f"Query embedding dimension: {len(query_embedding)}")
    
    # Do a vector search
    results = await vector_db_service.search(query, limit=5)
    print(f"\nSearch results ({len(results)} items):")
    
    for i, result in enumerate(results):
        content = result.get("content", "")
        similarity = result.get("similarity", 0)
        doc_id = result.get("document_id", "unknown")
        print(f"\n--- Result {i+1} (similarity: {similarity:.4f}) ---")
        print(f"Document ID: {doc_id}")
        print(f"Content preview: {content[:200]}...")

asyncio.run(debug_search())
