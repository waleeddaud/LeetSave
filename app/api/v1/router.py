from fastapi import APIRouter

from api.v1 import auth, github, submissions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(github.router, prefix="/github", tags=["github"])
