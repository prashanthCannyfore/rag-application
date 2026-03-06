import psycopg2

conn = psycopg2.connect('postgresql://postgres:Thangamani%40123@localhost:5433/rag')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
print("Tables:", cur.fetchall())
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
print("Extensions:", cur.fetchall())
conn.close()
