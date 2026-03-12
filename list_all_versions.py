"""
List all documents in versioning service
"""
from app.services.versioning_service import versioning_service

print("\n=== All Documents in Versioning Service ===\n")

if not versioning_service.versions:
    print("❌ No documents found in versioning service!")
    print("\nThis means uploads are not completing successfully.")
    print("Check your server logs for errors during upload.")
else:
    for doc_id, versions in versioning_service.versions.items():
        latest = versions[-1]
        metadata = latest.metadata or {}
        print(f"Document ID: {doc_id}")
        print(f"  Filename: {metadata.get('filename', 'unknown')}")
        print(f"  Versions: {len(versions)}")
        print(f"  Has content_bytes: {latest.content_bytes is not None}")
        print(f"  File path: {metadata.get('file_path')}")
        print()

print(f"Total documents: {len(versioning_service.versions)}")
