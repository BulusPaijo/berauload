"""Stage 9a substation API composition."""
from fastapi import APIRouter
from .master import router as master_router
from .definitions import router as definitions_router
from .visits import router as visits_router
from .imports import router as imports_router

router = APIRouter()
router.include_router(imports_router)
router.include_router(master_router)
router.include_router(definitions_router)
router.include_router(visits_router)
