from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "code": 200,
        "message": "success",
        "data": {"status": "ok", "database": "sqlite"},
    }
