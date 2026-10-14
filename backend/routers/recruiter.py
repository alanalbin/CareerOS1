from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
import models
from security import get_current_user, require_role

router = APIRouter(prefix="/recruiter", tags=["recruiter"])

class ApplicationStatusUpdate(BaseModel):
    status: str  # Applied, Under Review, Shortlisted, Interview, Selected, Rejected, Withdrawn

@router.get("/profile")
def get_recruiter_profile(
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found.")

    return {
        "profile": {
            "id": recruiter.id,
            "recruiterName": recruiter.recruiter_name,
            "company": recruiter.company,
            "officialEmail": recruiter.official_email,
            "phone": recruiter.phone,
            "designation": recruiter.designation,
            "website": recruiter.company_website,
        }
    }

@router.get("/candidates")
def search_candidates(
    skill: Optional[str] = None,
    course: Optional[str] = None,
    graduationYear: Optional[int] = None,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    """Searches candidates strictly respecting individual student privacy settings."""
    students = db.query(models.Student).all()
    results = []

    for s in students:
        # Check student privacy visibility
        vis = s.visibility_settings
        if vis and not vis.profile_visible:
            # Student has disabled general recruiter visibility
            continue

        u = s.user
        if not u:
            continue

        skills_list = [sk.name for sk in s.skills]
        if vis and vis.github_visible and s.github_profile and s.github_profile.top_languages:
            skills_list.extend(s.github_profile.top_languages)

        # Filters
        if skill and not any(skill.lower() in sk.lower() for sk in skills_list):
            continue
        if course and s.course and course.lower() not in s.course.lower():
            continue
        if graduationYear and s.graduation_year and s.graduation_year != graduationYear:
            continue

        # Build authorized candidate card
        candidate_data = {
            "id": s.id,
            "fullName": f"{u.first_name} {u.last_name}",
            "email": u.email,
            "targetRole": s.target_role or "Software Engineer",
            "department": s.department or s.course or "General Engineering",
            "course": s.course or "—",
            "graduationYear": s.graduation_year or 2026,
            "cgpa": s.cgpa if (vis and vis.profile_visible) else None,
            "skills": skills_list[:8],
            "verifiedEvidenceCount": sum(1 for c in s.certifications if c.verified) + (1 if (s.github_profile and vis and vis.github_visible) else 0),
        }

        if vis and vis.github_visible and s.github_profile:
            candidate_data["github"] = {
                "username": s.github_profile.username,
                "profileUrl": s.github_profile.profile_url,
                "publicRepos": s.github_profile.public_repos,
            }
        else:
            candidate_data["github"] = None

        if vis and vis.linkedin_visible and s.linkedin_profile:
            candidate_data["linkedin"] = {
                "username": s.linkedin_profile.username,
                "profileUrl": s.linkedin_profile.profile_url,
            }
        else:
            candidate_data["linkedin"] = None

        if vis and vis.certificates_visible:
            candidate_data["certifications"] = [
                {"title": c.title, "issuer": c.issuer, "verified": c.verified}
                for c in s.certifications[:4]
            ]
        else:
            candidate_data["certifications"] = []

        results.append(candidate_data)

    return {"candidates": results}

@router.get("/candidates/{student_id}")
def get_candidate_details(
    student_id: int,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    vis = student.visibility_settings
    if vis and not vis.profile_visible:
        raise HTTPException(status_code=403, detail="Student has not authorized recruiter profile visibility.")

    u = student.user
    data = {
        "id": student.id,
        "fullName": f"{u.first_name} {u.last_name}",
        "targetRole": student.target_role,
        "department": student.department,
        "course": student.course,
        "graduationYear": student.graduation_year,
        "bio": student.bio,
    }

    if vis and vis.github_visible and student.github_profile:
        data["github"] = {
            "username": student.github_profile.username,
            "profileUrl": student.github_profile.profile_url,
            "topLanguages": student.github_profile.top_languages,
            "publicRepos": student.github_profile.public_repos,
        }

    if vis and vis.linkedin_visible and student.linkedin_profile:
        data["linkedin"] = {
            "username": student.linkedin_profile.username,
            "profileUrl": student.linkedin_profile.profile_url,
            "headline": student.linkedin_profile.headline,
        }

    if vis and vis.certificates_visible:
        data["certifications"] = [
            {"title": c.title, "issuer": c.issuer, "verified": c.verified, "credentialUrl": c.credential_url}
            for c in student.certifications
        ]

    if vis and vis.projects_visible:
        data["projects"] = [
            {"title": p.title, "description": p.description, "technologies": p.technologies, "url": p.project_url}
            for p in student.projects
        ]

    return {"candidate": data}

@router.get("/jobs")
def get_recruiter_jobs(
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    if not recruiter:
        return {"jobs": []}

    jobs = db.query(models.Job).filter(models.Job.recruiter_id == recruiter.id).all()
    results = []
    for j in jobs:
        app_count = len(j.applications)
        results.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "employmentType": j.employment_type,
            "skillsRequired": j.skills_required,
            "status": j.status,
            "applicationCount": app_count,
            "createdAt": j.created_at.isoformat() if j.created_at else None,
        })

    return {"jobs": results}

@router.get("/applications")
def get_recruiter_applications(
    job_id: Optional[int] = None,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    if not recruiter:
        return {"applications": []}

    query = (
        db.query(models.Application)
        .join(models.Job, models.Application.job_id == models.Job.id)
        .filter(models.Job.recruiter_id == recruiter.id)
    )

    if job_id:
        query = query.filter(models.Application.job_id == job_id)

    apps = query.order_by(models.Application.created_at.desc()).all()
    results = []

    for a in apps:
        s = a.student
        u = s.user if s else None
        results.append({
            "id": a.id,
            "jobId": a.job_id,
            "jobTitle": a.job.title if a.job else "Position",
            "studentId": s.id if s else None,
            "candidateName": f"{u.first_name} {u.last_name}" if u else "Candidate",
            "candidateEmail": u.email if u else "",
            "status": a.status,
            "coverNote": a.cover_note,
            "resumeDocumentId": a.resume_document_id,
            "appliedAt": a.created_at.isoformat() if a.created_at else None,
        })

    return {"applications": results}

@router.put("/applications/{application_id}/status")
def update_candidate_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    app = (
        db.query(models.Application)
        .join(models.Job, models.Application.job_id == models.Job.id)
        .filter(models.Application.id == application_id, models.Job.recruiter_id == recruiter.id)
        .first()
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")

    app.status = payload.status
    db.commit()

    return {"success": True, "message": f"Application status updated to {payload.status}."}
