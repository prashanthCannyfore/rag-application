import psycopg2

conn = psycopg2.connect('postgresql://postgres:Thangamani%40123@localhost:5433/rag')
cur = conn.cursor()

# Drop existing table if exists
cur.execute("DROP TABLE IF EXISTS document_embeddings;")
print("Table dropped")

# Create table with JSONB for embeddings
cur.execute("""
    CREATE TABLE IF NOT EXISTS document_embeddings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content TEXT NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb,
        embedding JSONB,
        document_id VARCHAR(255),
        chunk_index INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
""")
print("Table created")

conn.commit()
conn.close()
print("Done!")
