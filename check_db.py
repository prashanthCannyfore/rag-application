import psycopg2

conn = psycopg2.connect('postgresql://postgres:Thangamani%40123@localhost:5433/rag')
cur = conn.cursor()
cur.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'document_embeddings'::regclass AND attname = 'embedding'")
print('Embedding dimension:', cur.fetchone())
conn.close()
