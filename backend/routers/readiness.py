from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from database import get_db
import models
from security import get_current_user

router = APIRouter(prefix="/readiness", tags=["readiness"])

@router.get("/score/{user_id}")
def get_user_score(
    user_id: int,
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    readiness = (
        db.query(models.CareerReadiness)
        .filter(models.CareerReadiness.student_id == student.id)
        .order_by(models.CareerReadiness.calculated_at.desc())
        .first()
    )

    if not readiness:
        return {
            "score": 0,
            "breakdown": {"technical": 0, "academic": 0, "evidence": 0, "soft": 0},
            "status": "No readiness data calculated yet.",
        }

    return {
        "score": int(readiness.overall_score),
        "breakdown": {
            "technical": int(readiness.technical_score),
            "academic": int(readiness.academic_score),
            "evidence": int(readiness.evidence_score),
            "soft": int(readiness.soft_skills_score),
        },
        "details": readiness.breakdown,
    }

@router.post("/calculate")
def calculate_my_readiness(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    projects = db.query(models.Project).filter(models.Project.student_id == student.id).all()
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()
    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()

    cgpa = student.cgpa or 0.0
    academic_score = min(100.0, (cgpa / 4.0) * 100) if cgpa <= 4.0 else min(100.0, (cgpa / 10.0) * 100)
    if cgpa == 0:
        academic_score = 50.0

    tech_score = min(100.0, len(skills) * 10.0 + (gh.public_repos * 5 if gh else 0.0))
    evidence_score = min(100.0, len(certs) * 20.0 + (20.0 if gh else 0.0))
    soft_score = 75.0

    overall = round((academic_score * 0.25) + (tech_score * 0.35) + (evidence_score * 0.25) + (soft_score * 0.15))

    rec = models.CareerReadiness(
        student_id=student.id,
        overall_score=overall,
        technical_score=tech_score,
        academic_score=academic_score,
        evidence_score=evidence_score,
        soft_skills_score=soft_score,
        breakdown={"verifiedCertificates": len(certs), "githubRepos": gh.public_repos if gh else 0},
    )
    db.add(rec)
    db.commit()

    return {
        "score": overall,
        "pillars": {
            "academic": academic_score,
            "technical": tech_score,
            "evidence": evidence_score,
            "soft": soft_score,
        }
    }
