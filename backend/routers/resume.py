from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
import models
from security import get_current_user
from ai_service import generate_ai_resume_content
from pdf_service import generate_resume_pdf

router = APIRouter(prefix="/resume", tags=["resume"])

class GenerateResumeRequest(BaseModel):
    selectedCertificateIds: Optional[List[int]] = None
    template: Optional[str] = "Modern"

class GeneratePdfRequest(BaseModel):
    selectedCertificateIds: Optional[List[int]] = None
    template: Optional[str] = "Modern"
    customData: Optional[Dict[str, Any]] = None

def aggregate_student_resume_data(user: models.User, student: models.Student, db: Session) -> Dict[str, Any]:
    education = db.query(models.Education).filter(models.Education.student_id == student.id).all()
    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    projects = db.query(models.Project).filter(models.Project.student_id == student.id).all()
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()
    exp = db.query(models.Experience).filter(models.Experience.student_id == student.id).all()
    internships = db.query(models.Internship).filter(models.Internship.student_id == student.id).all()
    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    li = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()

    return {
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "phone": user.phone or "",
        "collegeName": student.college_name or "",
        "targetRole": student.target_role or "Software Engineer",
        "summary": student.bio or "",
        "education": [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "start_year": e.start_year,
                "end_year": e.end_year,
                "grade_cgpa": e.grade_cgpa,
            }
            for e in education
        ],
        "skills": [s.name for s in skills],
        "projects": [
            {
                "title": p.title,
                "description": p.description,
                "technologies": p.technologies,
                "project_url": p.project_url,
            }
            for p in projects
        ] + ([
            {
                "title": f"GitHub Portfolio (@{gh.username})",
                "description": f"Verified public repository portfolio with {gh.public_repos} projects in {', '.join(gh.top_languages or [])}.",
                "technologies": ", ".join(gh.top_languages or []),
                "project_url": gh.profile_url,
            }
        ] if gh else []),
        "certifications": [
            {
                "id": c.id,
                "title": c.title,
                "issuer": c.issuer,
                "issue_date": c.issue_date,
                "credential_id": c.credential_id,
                "credential_url": c.credential_url,
            }
            for c in certs
        ],
        "experience": [
            {
                "company": x.company,
                "role": x.role,
                "period": f"{x.start_date or ''} - {x.end_date or 'Present'}",
                "description": x.description,
            }
            for x in exp
        ],
        "internships": [
            {
                "company": i.company,
                "role": i.role,
                "duration": i.duration,
                "description": i.description,
            }
            for i in internships
        ],
        "github": {"username": gh.username, "profileUrl": gh.profile_url} if gh else {},
        "linkedin": {"username": li.username, "profileUrl": li.profile_url} if li else {},
    }

@router.get("/data")
def get_resume_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    data = aggregate_student_resume_data(current_user, student, db)
    return {"success": True, "resumeData": data}

@router.post("/generate")
def generate_resume_content(
    payload: GenerateResumeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    raw_data = aggregate_student_resume_data(current_user, student, db)
    ai_resp = generate_ai_resume_content(raw_data, payload.selectedCertificateIds or [])

    # If AI is unavailable, format real student data deterministically
    if not ai_resp.get("success"):
        certs_to_include = [c for c in raw_data["certifications"] if not payload.selectedCertificateIds or c["id"] in payload.selectedCertificateIds]

        markdown_lines = [
            f"# {raw_data['name']}",
            f"**{raw_data['targetRole']}** | {raw_data['email']}" + (f" | {raw_data['phone']}" if raw_data['phone'] else ""),
            "",
            "### Summary",
            raw_data.get("summary") or f"Dedicated {raw_data['targetRole']} with proven project artifacts and verified credentials.",
            "",
            "### Education",
        ]
        for e in raw_data["education"]:
            markdown_lines.append(f"- **{e['degree']}** — {e['institution']} ({e.get('start_year', '')}-{e.get('end_year', '')})")

        markdown_lines.extend(["", "### Skills", ", ".join(raw_data["skills"]) if raw_data["skills"] else "None listed", "", "### Projects"])
        for p in raw_data["projects"]:
            markdown_lines.append(f"- **{p['title']}**: {p.get('description', '')} *(Stack: {p.get('technologies', '')})*")

        if certs_to_include:
            markdown_lines.extend(["", "### Verified Certifications"])
            for c in certs_to_include:
                markdown_lines.append(f"- **{c['title']}** — {c['issuer']} ({c.get('issue_date', 'Verified')})")

        fallback_md = "\n".join(markdown_lines)
        return {
            "success": True,
            "resumeMarkdown": fallback_md,
            "resumeData": raw_data,
            "aiUsed": False,
        }

    return {
        "success": True,
        "aiData": ai_resp.get("data"),
        "resumeData": raw_data,
        "aiUsed": True,
    }

@router.post("/pdf")
def download_resume_pdf(
    payload: GeneratePdfRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates an authentic, selectable-text A4 PDF resume and streams it as a genuine attachment."""
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    student_data = payload.customData or aggregate_student_resume_data(current_user, student, db)
    pdf_buffer = generate_resume_pdf(
        student_data=student_data,
        selected_cert_ids=payload.selectedCertificateIds,
        template_name=payload.template or "Modern",
    )

    clean_name = f"{current_user.first_name}_{current_user.last_name}_Resume.pdf".replace(" ", "_")

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}"',
            "Cache-Control": "no-cache",
        },
    )
