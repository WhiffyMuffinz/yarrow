from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_documents():
    return {"message": "stub"}

@router.post("/upload")
async def upload_document():
    return {"message": "stub"}

@router.get("/{id}")
async def get_document(id: str):
    return {"message": "stub"}

