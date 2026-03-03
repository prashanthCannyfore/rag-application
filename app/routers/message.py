from fastapi import APIRouter
from app.services.message_service import get_hello_message

router = APIRouter()

@router.get("/message")
def get_message():
    return get_hello_message()