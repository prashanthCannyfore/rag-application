import psycopg2

conn = psycopg2.connect('postgresql://postgres:Thangamani%40123@localhost:5433/rag')
cur = conn.cursor()

# Drop existing table if exists
cur.execute("DROP TABLE IF EXISTS document_embeddings;")
print("Table dropped")

# Create table with pgvector VECTOR(2000)
cur.execute("""
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content TEXT NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb,
        embedding VECTOR(2000),
        document_id VARCHAR(255),
        chunk_index INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
""")
print("Table created with VECTOR(2000)")

# Create index
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding 
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
""")
print("IVFFlat index created")

cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id 
    ON document_embeddings(document_id);
""")
print("Document ID index created")

conn.commit()
conn.close()
print("Done!")
