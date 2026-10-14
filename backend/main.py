import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base
import models
from routers import (
    auth,
    student,
    documents,
    github,
    linkedin,
    verification,
    readiness,
    ai,
    resume,
    jobs,
    college,
    recruiter,
)

# Ensure all database tables exist in PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Career OS API",
    description="Production AI-powered career readiness and talent verification platform",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all modular routers
app.include_router(auth.router, prefix="/api")
app.include_router(student.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(linkedin.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(readiness.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(college.router, prefix="/api")
app.include_router(recruiter.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "platform": "Career OS",
        "version": "1.0.0",
        "database": "PostgreSQL (Connected)",
        "ocrEngine": "PaddleOCR (Ready)",
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
