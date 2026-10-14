from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from database import get_db
import models
from security import get_current_user

router = APIRouter(prefix="/verification", tags=["verification"])

class ResolveDiscrepancyRequest(BaseModel):
    field: str
    newValue: str
    reason: str

@router.get("/getMatrix")
@router.post("/getMatrix")
@router.get("/matrix")
def get_verification_matrix(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student account required for verification matrix.")

    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    li = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    docs = db.query(models.Document).filter(models.Document.user_id == current_user.id).all()
    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    education = db.query(models.Education).filter(models.Education.student_id == student.id).all()
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()

    # Aggregate OCR structured extractions
    ocr_names = []
    ocr_skills = []
    ocr_degrees = []
    ocr_cgpas = []
    ocr_issuers = []

    for d in docs:
        ext = db.query(models.DocumentExtraction).filter(models.DocumentExtraction.document_id == d.id).first()
        if ext and ext.structured_data:
            sdata = ext.structured_data
            if sdata.get("candidateName"):
                ocr_names.append(sdata.get("candidateName"))
            if sdata.get("skills"):
                ocr_skills.extend(sdata.get("skills"))
            if sdata.get("cgpa"):
                ocr_cgpas.append(str(sdata.get("cgpa")))
            if sdata.get("issuer"):
                ocr_issuers.append(sdata.get("issuer"))

    user_full_name = f"{current_user.first_name} {current_user.last_name}".strip()
    account_skills = ", ".join([s.name for s in skills]) if skills else "No skills entered"

    gh_username = gh.username if gh else None
    gh_repos = gh.public_repos if gh else 0
    top_langs = ", ".join(gh.top_languages) if (gh and gh.top_languages) else ("—" if not gh else "None listed")

    li_username = li.username if li else None
    li_skills = ", ".join(li.skills) if (li and li.skills) else ("—" if not li else "None listed")

    ocr_name_val = ocr_names[0] if ocr_names else "—"
    ocr_skills_val = ", ".join(list(set(ocr_skills))[:5]) if ocr_skills else "—"
    ocr_cgpa_val = ocr_cgpas[0] if ocr_cgpas else "—"

    # College records
    college_name = student.college_name or (education[0].institution if education else "—")
    degree_major = (student.course or (education[0].degree if education else "—"))
    cgpa_val = str(student.cgpa) if student.cgpa else (education[0].grade_cgpa if education and education[0].grade_cgpa else "—")

    # Determine Name verification status
    name_sources = ["Account"]
    if ocr_name_val != "—":
        name_sources.append("OCR")
    if li:
        name_sources.append("LinkedIn")
    if gh:
        name_sources.append("GitHub")

    name_status = "VERIFIED" if (ocr_name_val != "—" and ocr_name_val.lower() == user_full_name.lower()) or (gh and li) else ("PARTIALLY_VERIFIED" if (gh or li or ocr_name_val != "—") else "PENDING")

    # Skills status
    skills_sources = ["Account"]
    if ocr_skills_val != "—":
        skills_sources.append("OCR")
    if gh:
        skills_sources.append("GitHub")
    if li:
        skills_sources.append("LinkedIn")
    skills_status = "VERIFIED" if (gh or li or ocr_skills_val != "—") and skills else "NEEDS_REVIEW"

    # Repos status
    repo_sources = ["Account"]
    if gh:
        repo_sources.append("GitHub")
    repo_status = "VERIFIED" if gh else "PENDING"

    # Degree status
    degree_sources = ["Account"]
    if college_name != "—":
        degree_sources.append("College")
    if ocr_degrees:
        degree_sources.append("OCR")
    degree_status = "VERIFIED" if (college_name != "—" and degree_major != "—") else "PENDING"

    # CGPA status
    cgpa_sources = ["Account"]
    if cgpa_val != "—":
        cgpa_sources.append("College")
    if ocr_cgpa_val != "—":
        cgpa_sources.append("OCR")
    cgpa_status = "VERIFIED" if (cgpa_val != "—" and ocr_cgpa_val != "—" and cgpa_val == ocr_cgpa_val) else ("CONSISTENT" if cgpa_val != "—" else "PENDING")

    return {
        "accounts": {
            "github": bool(gh),
            "githubData": {
                "username": gh_username,
                "publicRepos": gh_repos,
            } if gh else None,
            "linkedin": bool(li),
            "linkedinData": {
                "username": li_username,
            } if li else None,
        },
        "rows": [
            {
                "field": "Full Name",
                "sources": name_sources,
                "careerOsValue": user_full_name,
                "ocrValue": ocr_name_val,
                "linkedinValue": user_full_name if li else "—",
                "githubValue": gh.username if gh else "—",
                "status": name_status,
            },
            {
                "field": "Primary Skills",
                "sources": skills_sources,
                "careerOsValue": account_skills,
                "ocrValue": ocr_skills_val,
                "linkedinValue": li_skills,
                "githubValue": top_langs,
                "status": skills_status,
            },
            {
                "field": "Repository Count",
                "sources": repo_sources,
                "careerOsValue": f"{gh_repos} Projects" if gh else f"{len(student.projects)} Projects",
                "ocrValue": "—",
                "linkedinValue": "—",
                "githubValue": f"{gh_repos} Public Repos" if gh else "—",
                "status": repo_status,
            },
            {
                "field": "Degree & Major",
                "sources": degree_sources,
                "careerOsValue": degree_major,
                "ocrValue": ocr_degrees[0] if ocr_degrees else "—",
                "linkedinValue": degree_major if li else "—",
                "githubValue": "—",
                "status": degree_status,
            },
            {
                "field": "Cumulative GPA",
                "sources": cgpa_sources,
                "careerOsValue": cgpa_val,
                "ocrValue": ocr_cgpa_val,
                "linkedinValue": "—",
                "githubValue": "—",
                "status": cgpa_status,
            },
        ]
    }

@router.post("/resolveDiscrepancy")
def resolve_discrepancy(
    payload: ResolveDiscrepancyRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    # Log audit entry
    audit = models.AuditLog(
        user_id=current_user.id,
        action=f"RESOLVE_DISCREPANCY_{payload.field.upper().replace(' ', '_')}",
        details=f"Updated to '{payload.newValue}'. Reason: {payload.reason}",
    )
    db.add(audit)

    # Apply updates based on field
    if payload.field.lower() == "full name":
        parts = payload.newValue.strip().split(" ", 1)
        current_user.first_name = parts[0]
        current_user.last_name = parts[1] if len(parts) > 1 else ""
    elif payload.field.lower() == "cumulative gpa":
        try:
            student.cgpa = float(payload.newValue.strip())
        except ValueError:
            pass
    elif payload.field.lower() == "degree & major":
        student.course = payload.newValue.strip()

    db.commit()

    return {
        "success": True,
        "message": f"Successfully updated and verified '{payload.field}' with audit reason logged.",
    }
