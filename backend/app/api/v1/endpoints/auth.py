from fastapi import APIRouter

router = APIRouter()

@router.post("/register")
async def register():
    return {"message": "stub"}

@router.post("/login")
async def login():
    return {"message": "stub"}

@router.get("/me")
async def get_me():
    return {"message": "stub"}

