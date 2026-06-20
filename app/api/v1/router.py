from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.v1.auth import get_me
from api.v1 import auth, github, submissions
from models.user import User
from schemas.auth import MeResponse

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(github.router, prefix="/github", tags=["github"])


@api_router.get("/me", response_model=MeResponse, tags=["auth"])
def get_me_alias(user: User = Depends(get_current_user)):
    return get_me(user)
