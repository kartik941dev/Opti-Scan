"""
OptiScan FastAPI Backend Master Application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.answer_key import router as answer_key_router
from app.routes.auth import router as auth_router
from app.routes.exams import router as exams_router
from app.routes.omr_upload import router as omr_upload_router
from app.routes.results import router as results_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-Speed Computer Vision OMR Evaluation & Psychometric Analytics API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for React/Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static annotated audit images
app.mount("/static/annotated", StaticFiles(directory=str(settings.ANNOTATED_DIR)), name="annotated")

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(exams_router, prefix=settings.API_V1_STR)
app.include_router(answer_key_router, prefix=settings.API_V1_STR)
app.include_router(omr_upload_router, prefix=settings.API_V1_STR)
app.include_router(results_router, prefix=settings.API_V1_STR)


@app.api_route("/", methods=["GET", "HEAD"], tags=["Health"])
async def root():
    return {
        "status": "online",
        "project": "OptiScan OMR Evaluation API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
@app.api_route(f"{settings.API_V1_STR}/health", methods=["GET", "HEAD"], tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "optiscan-backend",
        "version": settings.VERSION,
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
