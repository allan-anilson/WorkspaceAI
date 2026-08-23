from fastapi import APIRouter
from app.api.v1.endpoints import auth, organization

api_router = APIRouter()

# Mount authentication endpoints
api_router.include_router(auth.router)
api_router.include_router(organization.router)