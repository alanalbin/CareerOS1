from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from database import get_db
import models
from security import get_current_user, require_role

router = APIRouter(prefix="/college", tags=["college"])

@router.get("/profile")
def get_college_profile(
    current_user: models.User = Depends(require_role(["COLLEGE", "COLLEGE_ADMIN"])),
    db: Session = Depends(get_db)
):
    college = db.query(models.College).filter(models.College.user_id == current_user.id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College profile not found.")

    return {
        "profile": {
            "id": college.id,
            "collegeName": college.college_name,
            "officialEmail": college.official_email,
            "collegeIdCode": college.college_id_code,
            "contactPerson": college.contact_person,
            "phone": college.phone,
            "address": college.address,
            "website": college.website,
        }
    }

@router.get("/students")
@router.get("/roster")
def get_college_students(
    current_user: models.User = Depends(require_role(["COLLEGE", "COLLEGE_ADMIN"])),
    db: Session = Depends(get_db)
):
    college = db.query(models.College).filter(models.College.user_id == current_user.id).first()
    c_name = college.college_name if college else None

    query = db.query(models.Student)
    if c_name:
        query = query.filter(models.Student.college_name.ilike(f"%{c_name}%"))

    students = query.all()
    results = []

    for s in students:
        u = s.user
        certs_count = len(s.certifications)
        projs_count = len(s.projects) + (1 if s.github_profile else 0)
        skills_count = len(s.skills)

        # Find latest readiness score
        latest_r = (
            db.query(models.CareerReadiness)
            .filter(models.CareerReadiness.student_id == s.id)
            .order_by(models.CareerReadiness.calculated_at.desc())
            .first()
        )
        readiness_score = int(latest_r.overall_score) if latest_r else (70 if certs_count > 0 else 50)

        results.append({
            "id": s.id,
            "userId": u.id if u else None,
            "fullName": f"{u.first_name} {u.last_name}" if u else "Student Scholar",
            "email": u.email if u else "",
            "studentIdNumber": s.student_id_number or "—",
            "department": s.department or s.course or "General Engineering",
            "course": s.course or "—",
            "graduationYear": s.graduation_year or 2026,
            "cgpa": s.cgpa or "—",
            "targetRole": s.target_role or "Software Engineer",
            "readinessScore": readiness_score,
            "verifiedEvidenceCount": sum(1 for c in s.certifications if c.verified) + (1 if s.github_profile else 0),
            "certificatesCount": certs_count,
            "projectsCount": projs_count,
            "skillsCount": skills_count,
        })

    return {"students": results}

@router.get("/analytics")
def get_college_analytics(
    current_user: models.User = Depends(require_role(["COLLEGE", "COLLEGE_ADMIN"])),
    db: Session = Depends(get_db)
):
    college = db.query(models.College).filter(models.College.user_id == current_user.id).first()
    c_name = college.college_name if college else None

    query = db.query(models.Student)
    if c_name:
        query = query.filter(models.Student.college_name.ilike(f"%{c_name}%"))

    students = query.all()
    total_students = len(students)

    if total_students == 0:
        return {
            "hasData": False,
            "message": "Not enough data to generate this analysis.",
            "totalStudents": 0,
            "averageReadiness": 0,
            "skillDistribution": {},
            "topCertifications": [],
            "placementReadinessTier": {"high": 0, "medium": 0, "needsImprovement": 0},
        }

    # Real skill distribution calculation
    skill_counts: Dict[str, int] = {}
    for s in students:
        for sk in s.skills:
            skill_counts[sk.name] = skill_counts.get(sk.name, 0) + 1
        if s.github_profile and s.github_profile.top_languages:
            for lang in s.github_profile.top_languages:
                skill_counts[lang] = skill_counts.get(lang, 0) + 1

    # Tiers calculation
    high_tier = 0
    med_tier = 0
    low_tier = 0
    scores = []

    for s in students:
        latest_r = (
            db.query(models.CareerReadiness)
            .filter(models.CareerReadiness.student_id == s.id)
            .order_by(models.CareerReadiness.calculated_at.desc())
            .first()
        )
        score = int(latest_r.overall_score) if latest_r else (65 if len(s.certifications) > 0 else 40)
        scores.append(score)
        if score >= 80:
            high_tier += 1
        elif score >= 60:
            med_tier += 1
        else:
            low_tier += 1

    avg_readiness = round(sum(scores) / len(scores)) if scores else 0

    return {
        "hasData": True,
        "totalStudents": total_students,
        "averageReadiness": avg_readiness,
        "skillDistribution": dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "placementReadinessTier": {
            "high": high_tier,
            "medium": med_tier,
            "needsImprovement": low_tier,
        },
    }
