from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.roles import router as roles_router
from app.api.translations import router as translations_router
from app.api.users import router as users_router
from app.router.health import router as health_router
from app.router.secom import router as secom_router

api_router = APIRouter(prefix="/v1")

include_api = api_router.include_router

routers = [
    (health_router, "", "Health"),
    (auth_router, "auth", "Authentication"),
    (users_router, "users", "Users"),
    (roles_router, "roles", "Roles & Permissions"),
    (translations_router, "translations", "Translation Services"),
    (secom_router, "secom", "SECOM"),
]

for router_item in routers:
    router, prefix, tag = router_item

    # Construct the prefix only if it's not empty
    final_prefix = f"/{prefix}" if prefix else ""

    # Include the router with the correct prefix and tags
    include_api(router, prefix=final_prefix, tags=[tag])
