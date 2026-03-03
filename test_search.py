import requests

url = "http://localhost:8000/api/rag/search"

# Test questions
questions = [
    "Who has the highest score?",
    "What is Jane's score?",
    # "How many students are there?",
    # "Who scored above 85?",
    # "What is the average score in Math?"
]

for question in questions:
    print(f"\nQuestion: {question}")
    response = requests.post(url, json={"question": question})
    result = response.json()
    print(f"Answer: {result.get('answer', 'No answer')}")
    print(f"Chunks used: {result.get('chunks_used', 0)}")