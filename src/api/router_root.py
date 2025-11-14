from fastapi import APIRouter

router = APIRouter()

# Placeholder for core-only endpoints
@router.get("/health")
def health():
    return {"ok": True}
