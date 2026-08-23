from backend.app.routes.auth import router as auth_router
from backend.app.routes.exams import router as exams_router
from backend.app.routes.answer_key import router as answer_key_router
from backend.app.routes.omr_upload import router as omr_upload_router
from backend.app.routes.results import router as results_router

__all__ = [
    "auth_router",
    "exams_router",
    "answer_key_router",
    "omr_upload_router",
    "results_router",
]
