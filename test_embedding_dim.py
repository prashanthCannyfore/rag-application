from app.services.embeddings_service import embeddings_service

embedding = embeddings_service.embed_text("test")
print(f"Embedding dimension: {len(embedding)}")
