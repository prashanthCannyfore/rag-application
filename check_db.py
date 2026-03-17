import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = 'postgresql://postgres:Thangamani%40123@localhost:5432/rag'

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'document_embeddings'::regclass AND attname = 'embedding'")
print('Embedding dimension:', cur.fetchone())
conn.close()
