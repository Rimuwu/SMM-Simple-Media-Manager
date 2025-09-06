from fastapi import APIRouter


router = APIRouter(prefix="/test", tags=["test"])

@router.get("/events")
async def test():
    return {"message": "No events"}