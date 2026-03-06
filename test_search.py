# import requests

# url = "http://localhost:8000/api/rag/search"

# # Test questions
# questions = [
#     "Who has the highest score?",
#     # "What is Jane's score?",
#     # "How many students are there?",
#     # "Who scored above 85?",
#     # "What is the average score in Math?"
# ]

# for question in questions:
#     print(f"\nQuestion: {question}")
#     response = requests.post(url, json={"question": question})
#     result = response.json()
#     print(f"Answer: {result.get('answer', 'No answer')}")
#     print(f"Chunks used: {result.get('chunks_used', 0)}")


from sentence_transformers import SentenceTransformer
import numpy as np

# Load a free embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Convert words to vectors
words = ["dog", "cat", "car"]
vectors = model.encode(words)

# See the shape
print(vectors.shape)
# (3, 384)
# → 3 words, each has 384 numbers

# See dog's first 5 numbers
print(vectors[0][:382])
# [-0.07,  0.18, -0.29,  0.38,  0.06]
