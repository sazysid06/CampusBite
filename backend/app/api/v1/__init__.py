from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)

from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.restaurants import router as restaurant_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(restaurant_router)

from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.restaurants import router as restaurant_router
from backend.app.api.v1.orders import router as order_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(restaurant_router)
api_v1_router.include_router(order_router)

from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.restaurants import router as restaurant_router
from backend.app.api.v1.orders import router as order_router
from backend.app.api.v1.recommendations import router as recommendation_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(restaurant_router)
api_v1_router.include_router(order_router)
api_v1_router.include_router(recommendation_router)