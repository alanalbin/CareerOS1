from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import datetime

from database import get_db
import models
from security import get_current_user, require_role

router = APIRouter(prefix="/jobs", tags=["jobs"])

class CreateJobPayload(BaseModel):
    title: str
    description: str
    company: Optional[str] = None
    location: str
    employmentType: Optional[str] = "Full-Time"
    skillsRequired: Optional[str] = None
    experienceRequired: Optional[str] = None

class UpdateJobPayload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    employmentType: Optional[str] = None
    skillsRequired: Optional[str] = None
    experienceRequired: Optional[str] = None
    status: Optional[str] = None

class ApplyJobPayload(BaseModel):
    coverNote: Optional[str] = None
    resumeDocumentId: Optional[int] = None

class UpdateApplicationStatusPayload(BaseModel):
    status: str  # Applied, Under Review, Shortlisted, Interview, Selected, Rejected, Withdrawn

@router.get("")
def list_jobs(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Job)
    if status_filter:
        query = query.filter(models.Job.status == status_filter)
    else:
        query = query.filter(models.Job.status == "OPEN")

    jobs = query.order_by(models.Job.created_at.desc()).all()
    return {
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "description": j.description,
                "company": j.company,
                "location": j.location,
                "employmentType": j.employment_type,
                "skillsRequired": j.skills_required,
                "experienceRequired": j.experience_required,
                "status": j.status,
                "createdAt": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    }

@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "company": job.company,
            "location": job.location,
            "employmentType": job.employment_type,
            "skillsRequired": job.skills_required,
            "experienceRequired": job.experience_required,
            "status": job.status,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
        }
    }

@router.post("")
def create_job(
    payload: CreateJobPayload,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    if not recruiter:
        raise HTTPException(status_code=400, detail="Recruiter profile required to create jobs.")

    company_name = payload.company or recruiter.company or "Hiring Company"

    job = models.Job(
        recruiter_id=recruiter.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        company=company_name,
        location=payload.location.strip(),
        employment_type=payload.employmentType or "Full-Time",
        skills_required=payload.skillsRequired,
        experience_required=payload.experienceRequired,
        status="OPEN",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {"success": True, "job": {"id": job.id, "title": job.title, "company": job.company}}

@router.put("/{job_id}")
def update_job(
    job_id: int,
    payload: UpdateJobPayload,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized.")

    if payload.title:
        job.title = payload.title
    if payload.description:
        job.description = payload.description
    if payload.location:
        job.location = payload.location
    if payload.employmentType:
        job.employment_type = payload.employmentType
    if payload.skillsRequired is not None:
        job.skills_required = payload.skillsRequired
    if payload.experienceRequired is not None:
        job.experience_required = payload.experienceRequired
    if payload.status:
        job.status = payload.status

    db.commit()
    return {"success": True, "message": "Job updated successfully."}

@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    current_user: models.User = Depends(require_role(["RECRUITER"])),
    db: Session = Depends(get_db)
):
    recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == current_user.id).first()
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.recruiter_id == recruiter.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized.")

    db.delete(job)
    db.commit()
    return {"success": True, "message": "Job deleted."}

@router.post("/{job_id}/apply")
def apply_to_job(
    job_id: int,
    payload: ApplyJobPayload,
    current_user: models.User = Depends(require_role(["STUDENT"])),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.status != "OPEN":
        raise HTTPException(status_code=400, detail="This job is closed or does not exist.")

    # Check for existing application
    existing = db.query(models.Application).filter(models.Application.job_id == job_id, models.Application.student_id == student.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this position.")

    app = models.Application(
        job_id=job.id,
        student_id=student.id,
        cover_note=payload.coverNote,
        resume_document_id=payload.resumeDocumentId,
        status="Applied",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {"success": True, "message": "Application submitted successfully.", "applicationId": app.id}

@router.get("/my/applications")
def get_my_applications(
    current_user: models.User = Depends(require_role(["STUDENT"])),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        return {"applications": []}

    apps = db.query(models.Application).filter(models.Application.student_id == student.id).order_by(models.Application.created_at.desc()).all()
    results = []
    for a in apps:
        j = a.job
        results.append({
            "id": a.id,
            "jobId": a.job_id,
            "jobTitle": j.title if j else "Position",
            "company": j.company if j else "Company",
            "location": j.location if j else "",
            "status": a.status,
            "appliedAt": a.created_at.isoformat() if a.created_at else None,
        })

    return {"applications": results}
