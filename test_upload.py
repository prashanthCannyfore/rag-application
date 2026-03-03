import requests

url = "http://localhost:8000/api/rag/upload"

# Upload file
with open("students.csv", "rb") as f:
    files = {"file": ("students.csv", f, "text/csv")}
    data = {"document_name": "students.csv"}
    
    response = requests.post(url, files=files, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")