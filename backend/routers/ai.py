import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from database import get_db
import models
from security import get_current_user
from ai_service import (
    generate_career_guidance_and_gaps,
    analyze_github_data,
    analyze_linkedin_data,
    call_qwen_chat,
)

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/guidance")
@router.post("/analyze")
def get_career_guidance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    education = db.query(models.Education).filter(models.Education.student_id == student.id).all()
    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    projects = db.query(models.Project).filter(models.Project.student_id == student.id).all()
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()
    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()

    student_data = {
        "name": f"{current_user.first_name} {current_user.last_name}",
        "targetRole": student.target_role or "Software Engineer",
        "education": [{"degree": e.degree, "institution": e.institution, "cgpa": e.grade_cgpa} for e in education],
        "skills": [s.name for s in skills],
        "projects": [{"title": p.title, "tech": p.technologies} for p in projects],
        "certifications": [{"title": c.title, "issuer": c.issuer} for c in certs],
        "github": {"repos": gh.public_repos if gh else 0, "topLanguages": gh.top_languages if gh else []},
    }

    ai_result = generate_career_guidance_and_gaps(student_data)

    if ai_result.get("success"):
        record = models.AIAnalysis(
            student_id=student.id,
            analysis_type="career_guidance",
            content=ai_result.get("data"),
            model_used="qwen3.8-flash",
        )
        db.add(record)
        db.commit()

    return ai_result

@router.get("/latest")
def get_latest_ai_analysis(
    analysis_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        return {"analysis": None}

    query = db.query(models.AIAnalysis).filter(models.AIAnalysis.student_id == student.id)
    if analysis_type:
        query = query.filter(models.AIAnalysis.analysis_type == analysis_type)

    record = query.order_by(models.AIAnalysis.created_at.desc()).first()
    if not record:
        return {"analysis": None, "message": "No AI analysis performed yet."}

    return {
        "analysis": record.content,
        "type": record.analysis_type,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }
