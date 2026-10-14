import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
import models
from security import get_current_user, require_role
from routers.github import fetch_github_user_and_repos, analyze_github_data
from ai_service import analyze_linkedin_data

router = APIRouter(prefix="/student", tags=["student"])

class ProfileUpdatePayload(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    targetRole: Optional[str] = None
    department: Optional[str] = None
    collegeName: Optional[str] = None
    cgpa: Optional[float] = None
    bio: Optional[str] = None

class EducationPayload(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade_cgpa: Optional[str] = None
    is_current: Optional[bool] = False

class SkillPayload(BaseModel):
    name: str
    category: Optional[str] = "Technical"
    proficiency: Optional[str] = "Intermediate"

class ProjectPayload(BaseModel):
    title: str
    description: Optional[str] = None
    technologies: Optional[str] = None
    project_url: Optional[str] = None
    github_repo: Optional[str] = None

class ExperiencePayload(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[bool] = False

class PrivacySettingsPayload(BaseModel):
    profile_visible: Optional[bool] = None
    resume_visible: Optional[bool] = None
    github_visible: Optional[bool] = None
    linkedin_visible: Optional[bool] = None
    certificates_visible: Optional[bool] = None
    documents_visible: Optional[bool] = None
    projects_visible: Optional[bool] = None
    experience_visible: Optional[bool] = None

def get_or_create_student(user: models.User, db: Session) -> models.Student:
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        student = models.Student(
            user_id=user.id,
            target_role="Software Engineer",
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    return student

@router.get("/getDashboardData")
@router.post("/getDashboardData")
def get_dashboard_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)

    # Fetch real collections
    gh_profile = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    li_profile = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    projects = db.query(models.Project).filter(models.Project.student_id == student.id).all()
    education = db.query(models.Education).filter(models.Education.student_id == student.id).all()
    experiences = db.query(models.Experience).filter(models.Experience.student_id == student.id).all()
    internships = db.query(models.Internship).filter(models.Internship.student_id == student.id).all()
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()
    docs = db.query(models.Document).filter(models.Document.user_id == current_user.id).all()

    # Calculate evidence list from real items
    evidence_items = []
    evidence_counter = 1

    if gh_profile:
        evidence_items.append({
            "id": evidence_counter,
            "title": f"GitHub Repository Portfolio (@{gh_profile.username})",
            "type": "PROJECT",
            "source": "GitHub Public REST API",
            "verificationStatus": "VERIFIED",
            "verifiedAt": gh_profile.connected_at.strftime("%Y-%m-%d") if gh_profile.connected_at else "Recent",
            "url": gh_profile.profile_url,
            "scoreContribution": min(25, gh_profile.public_repos * 5 + 10),
        })
        evidence_counter += 1

    for c in certs:
        evidence_items.append({
            "id": evidence_counter,
            "title": c.title,
            "type": "CERTIFICATE",
            "source": f"PaddleOCR Verified ({c.issuer})",
            "verificationStatus": "VERIFIED" if c.verified else "PENDING",
            "verifiedAt": c.issue_date or (c.created_at.strftime("%Y-%m-%d") if c.created_at else "Recent"),
            "url": c.credential_url or "#",
            "scoreContribution": 15 if c.verified else 5,
        })
        evidence_counter += 1

    for exp in experiences + internships:
        evidence_items.append({
            "id": evidence_counter,
            "title": f"{exp.role} at {exp.company}",
            "type": "INTERNSHIP" if hasattr(exp, 'duration') else "EXPERIENCE",
            "source": "Student Submitted Record",
            "verificationStatus": "VERIFIED" if exp.verified else "CONSENTED",
            "verifiedAt": exp.created_at.strftime("%Y-%m-%d") if exp.created_at else "Recent",
            "url": "#",
            "scoreContribution": 15,
        })
        evidence_counter += 1

    # Deterministic pillar calculations based strictly on real data
    # 1. Academic (0 - 100)
    cgpa_val = student.cgpa
    if not cgpa_val and education:
        for e in education:
            try:
                cgpa_val = float(e.grade_cgpa)
                break
            except (ValueError, TypeError):
                pass

    if cgpa_val:
        # Scale 4.0 or 10.0 scale
        if cgpa_val <= 4.0:
            academic_score = round(min(100.0, (cgpa_val / 4.0) * 100))
        else:
            academic_score = round(min(100.0, (cgpa_val / 10.0) * 100))
    elif education:
        academic_score = 70
    else:
        academic_score = 0

    # 2. Projects (0 - 100)
    gh_repo_count = gh_profile.public_repos if gh_profile else 0
    total_projects = len(projects) + gh_repo_count
    projects_score = min(100, total_projects * 15 + (15 if gh_profile else 0))

    # 3. Evidence / Certifications (0 - 100)
    verified_evidence_count = sum(1 for e in evidence_items if e["verificationStatus"] == "VERIFIED")
    evidence_score = min(100, verified_evidence_count * 20 + len(docs) * 5)

    # 4. Skills (0 - 100)
    total_skills = len(skills) + (len(gh_profile.top_languages) if gh_profile and gh_profile.top_languages else 0)
    skills_score = min(100, total_skills * 10)

    # Overall weighted score
    if any([academic_score, projects_score, evidence_score, skills_score]):
        overall_score = round(
            (academic_score * 0.25) +
            (projects_score * 0.30) +
            (evidence_score * 0.25) +
            (skills_score * 0.20)
        )
    else:
        overall_score = 0

    # Profile completion
    completion_checks = [
        bool(student.target_role),
        bool(student.college_name or education),
        bool(skills),
        bool(projects or gh_profile),
        bool(certs or docs),
        bool(gh_profile),
        bool(li_profile),
    ]
    profile_completion = round((sum(completion_checks) / len(completion_checks)) * 100)

    full_name = f"{current_user.first_name} {current_user.last_name}".strip()

    top_skill_names = [s.name for s in skills]
    if gh_profile and gh_profile.top_languages:
        for lang in gh_profile.top_languages:
            if lang not in top_skill_names:
                top_skill_names.append(lang)

    return {
        "score": overall_score,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "role": current_user.role,
            "avatarUrl": student.avatar_url,
            "githubUsername": gh_profile.username if gh_profile else None,
        },
        "profile": {
            "id": student.id,
            "name": full_name,
            "targetRole": student.target_role or "Software Engineer",
            "department": student.department or (student.course or "General Engineering"),
            "employabilityScore": overall_score,
            "placementReadiness": overall_score,
            "verifiedEvidence": verified_evidence_count,
            "totalEvidence": len(evidence_items),
            "profileCompletion": profile_completion,
            "recruiterVisibility": "CONSENTED",
            "collegeName": student.college_name or "Not Specified",
            "cgpa": cgpa_val,
        },
        "assessment": {
            "overallScore": overall_score,
            "technicalScore": max(projects_score, skills_score),
            "evidenceStrengthScore": evidence_score,
            "problemSolvingScore": max(0, overall_score - 5),
            "academicScore": academic_score,
        },
        "pillars": {
            "academic": {"score": academic_score, "weight": 25, "verified": bool(education or cgpa_val)},
            "projects": {"score": projects_score, "weight": 30, "verified": bool(gh_profile or projects)},
            "evidence": {"score": evidence_score, "weight": 25, "verified": verified_evidence_count > 0},
            "skills": {"score": skills_score, "weight": 20, "verified": len(skills) > 0},
        },
        "evidence": evidence_items,
        "evidenceList": evidence_items,
        "skills": top_skill_names,
        "topSkills": top_skill_names[:8],
        "recommendations": {
            "recommendedRoles": [student.target_role or "Software Engineer", "Full-Stack Developer", "Systems Engineer"],
            "primaryRoleFitScore": overall_score,
            "missingSkills": [s for s in ["Docker", "Kubernetes", "System Design", "CI/CD", "Testing"] if s not in top_skill_names][:3],
            "recommendedActions": [
                {"title": "Connect GitHub repositories", "skill": "Version Control", "time": "1 hr", "reason": "Demonstrate public project code to recruiters"} if not gh_profile else
                {"title": "Upload course certificates", "skill": "Verification", "time": "30 mins", "reason": "Extract verified credentials using PaddleOCR"} if not certs else
                {"title": "Improve unit test coverage", "skill": "Quality Assurance", "time": "2 hrs", "reason": "Strengthen repository code quality grade"}
            ],
            "learningPriorities": [s for s in ["Distributed Systems", "Cloud Architecture", "Advanced TypeScript"] if s not in top_skill_names][:3],
            "readinessSummary": f"{full_name} has built a real career profile with {len(evidence_items)} evidence artifact(s) and {len(top_skill_names)} skill(s)." if len(evidence_items) > 0 else f"{full_name} has registered their Career OS account. Upload certificates or connect GitHub to calculate verified readiness.",
        },
        "recentActivities": [
            {"action": "Account verified and active", "timestamp": "Active", "icon": "ShieldCheck"},
        ] + ([{"action": f"GitHub account @{gh_profile.username} connected", "timestamp": "Synced", "icon": "Github"}] if gh_profile else [])
          + ([{"action": f"{len(certs)} certificate(s) uploaded and OCR parsed", "timestamp": "Completed", "icon": "FileCheck2"}] if certs else [])
    }

@router.get("/getProfessionalProfiles")
@router.post("/getProfessionalProfiles")
def get_professional_profiles(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)
    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    li = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()

    gh_dict = None
    if gh:
        repos = db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh.id).all()
        gh_dict = {
            "id": gh.id,
            "username": gh.username,
            "profileUrl": gh.profile_url,
            "avatarUrl": gh.avatar_url,
            "verified": True,
            "connectedAt": gh.connected_at.isoformat() if gh.connected_at else None,
            "data": {
                "name": f"{current_user.first_name} {current_user.last_name}",
                "bio": gh.bio,
                "avatar_url": gh.avatar_url,
                "public_repos": gh.public_repos,
                "followers": gh.followers,
                "following": gh.following,
                "topLanguages": gh.top_languages or [],
                "repos": [
                    {
                        "name": r.name,
                        "description": r.description or "No description",
                        "language": r.language or "Other",
                        "stargazers_count": r.stars,
                        "forks_count": r.forks,
                        "html_url": r.html_url,
                    }
                    for r in repos
                ],
            }
        }

    li_dict = None
    if li:
        li_dict = {
            "id": li.id,
            "username": li.username,
            "profileUrl": li.profile_url,
            "verified": True,
            "connectedAt": li.connected_at.isoformat() if li.connected_at else None,
            "data": {
                "headline": li.headline,
                "skills": li.skills or [],
                "experience": li.experience or [],
            }
        }

    return {"github": gh_dict, "linkedin": li_dict}

@router.post("/connectGithub")
def connect_github_student(
    payload: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    username = (payload.get("username") or "").strip().replace("https://github.com/", "").replace("/", "")
    if not username:
        raise HTTPException(status_code=400, detail="GitHub username is required.")

    student = get_or_create_student(current_user, db)
    gh_data = fetch_github_user_and_repos(username, payload.get("token"))

    gh_profile = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    if not gh_profile:
        gh_profile = models.GitHubProfile(student_id=student.id, username=gh_data["username"])
        db.add(gh_profile)

    gh_profile.username = gh_data["username"]
    gh_profile.profile_url = gh_data["profile_url"]
    gh_profile.avatar_url = gh_data["avatar_url"]
    gh_profile.bio = gh_data["bio"]
    gh_profile.public_repos = gh_data["public_repos"]
    gh_profile.followers = gh_data["followers"]
    gh_profile.following = gh_data["following"]
    gh_profile.top_languages = gh_data["top_languages"]

    db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh_profile.id).delete()
    db.flush()

    for r in gh_data["repos"]:
        db.add(models.GitHubRepository(
            github_profile_id=gh_profile.id,
            name=r["name"],
            description=r["description"],
            language=r["language"],
            stars=r["stars"],
            forks=r["forks"],
            html_url=r["html_url"],
            updated_at=r["updated_at"],
        ))

    db.commit()
    db.refresh(gh_profile)

    return {
        "success": True,
        "profile": {
            "id": gh_profile.id,
            "username": gh_profile.username,
            "profileUrl": gh_profile.profile_url,
            "verified": True,
            "data": gh_data,
        },
        "message": f"Successfully connected GitHub profile @{username}!",
    }

@router.post("/disconnectGithub")
def disconnect_github_student(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)
    db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).delete()
    db.commit()
    return {"success": True, "message": "GitHub profile disconnected."}

@router.post("/connectLinkedin")
def connect_linkedin_student(
    payload: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raw_url = (payload.get("profileUrl") or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="LinkedIn URL is required.")

    clean = raw_url.replace("https://www.linkedin.com/in/", "").replace("https://linkedin.com/in/", "").replace("/", "").strip()
    student = get_or_create_student(current_user, db)

    li = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    if not li:
        li = models.LinkedInProfile(student_id=student.id, username=clean)
        db.add(li)

    li.username = clean
    li.profile_url = f"https://www.linkedin.com/in/{clean}"
    li.headline = payload.get("headline") or "Verified Student Scholar"
    li.skills = payload.get("skills") or []
    li.experience = payload.get("experience") or []

    db.commit()
    db.refresh(li)

    return {
        "success": True,
        "profile": {
            "id": li.id,
            "username": li.username,
            "profileUrl": li.profile_url,
            "verified": True,
            "data": {
                "headline": li.headline,
                "skills": li.skills,
                "experience": li.experience,
            }
        },
        "message": f"Successfully connected LinkedIn profile @{clean}!",
    }

@router.post("/disconnectLinkedin")
def disconnect_linkedin_student(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)
    db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).delete()
    db.commit()
    return {"success": True, "message": "LinkedIn profile disconnected."}

@router.post("/analyzeGithub")
def analyze_github_student(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)
    gh = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    if not gh:
        raise HTTPException(status_code=400, detail="No GitHub account connected. Please connect your GitHub profile first.")

    repos = db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh.id).all()
    repo_dicts = [{"name": r.name, "description": r.description, "language": r.language, "stars": r.stars, "forks": r.forks} for r in repos]

    res = analyze_github_data(gh.username, repo_dicts, gh.top_languages or [])
    return res

@router.put("/profile")
def update_student_profile(
    payload: ProfileUpdatePayload,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)

    if payload.firstName:
        current_user.first_name = payload.firstName
    if payload.lastName:
        current_user.last_name = payload.lastName
    if payload.phone:
        current_user.phone = payload.phone
    if payload.targetRole:
        student.target_role = payload.targetRole
    if payload.department:
        student.department = payload.department
    if payload.collegeName:
        student.college_name = payload.collegeName
    if payload.cgpa is not None:
        student.cgpa = payload.cgpa
    if payload.bio:
        student.bio = payload.bio

    db.commit()
    return {"success": True, "message": "Profile updated successfully."}

@router.get("/skills")
def list_skills(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    skills = db.query(models.Skill).filter(models.Skill.student_id == student.id).all()
    return {"skills": [{"id": s.id, "name": s.name, "category": s.category, "proficiency": s.proficiency, "verified": s.verified} for s in skills]}

@router.post("/skills")
def add_skill(payload: SkillPayload, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    skill = models.Skill(
        student_id=student.id,
        name=payload.name.strip(),
        category=payload.category or "Technical",
        proficiency=payload.proficiency or "Intermediate",
        source="Account",
    )
    db.add(skill)
    db.commit()
    return {"success": True, "skill": {"id": skill.id, "name": skill.name, "category": skill.category}}

@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    db.query(models.Skill).filter(models.Skill.id == skill_id, models.Skill.student_id == student.id).delete()
    db.commit()
    return {"success": True, "message": "Skill removed."}

@router.get("/projects")
def list_projects(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    projs = db.query(models.Project).filter(models.Project.student_id == student.id).all()
    return {"projects": [{"id": p.id, "title": p.title, "description": p.description, "technologies": p.technologies, "project_url": p.project_url} for p in projs]}

@router.post("/projects")
def add_project(payload: ProjectPayload, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    p = models.Project(
        student_id=student.id,
        title=payload.title.strip(),
        description=payload.description,
        technologies=payload.technologies,
        project_url=payload.project_url,
        github_repo=payload.github_repo,
    )
    db.add(p)
    db.commit()
    return {"success": True, "project": {"id": p.id, "title": p.title}}

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    db.query(models.Project).filter(models.Project.id == project_id, models.Project.student_id == student.id).delete()
    db.commit()
    return {"success": True, "message": "Project deleted."}

@router.get("/certifications")
def list_certifications(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    certs = db.query(models.Certification).filter(models.Certification.student_id == student.id).all()
    return {
        "certifications": [
            {
                "id": c.id,
                "title": c.title,
                "issuer": c.issuer,
                "issueDate": c.issue_date,
                "credentialId": c.credential_id,
                "credentialUrl": c.credential_url,
                "verified": c.verified,
                "documentId": c.document_id,
            }
            for c in certs
        ]
    }

@router.get("/privacy")
def get_privacy(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = get_or_create_student(current_user, db)
    vis = db.query(models.StudentVisibilitySetting).filter(models.StudentVisibilitySetting.student_id == student.id).first()
    if not vis:
        vis = models.StudentVisibilitySetting(student_id=student.id)
        db.add(vis)
        db.commit()
        db.refresh(vis)

    return {
        "profile": vis.profile_visible,
        "resume": vis.resume_visible,
        "github": vis.github_visible,
        "linkedin": vis.linkedin_visible,
        "certificates": vis.certificates_visible,
        "documents": vis.documents_visible,
        "projects": vis.projects_visible,
        "experience": vis.experience_visible,
    }

@router.put("/privacy")
@router.post("/updatePrivacy")
def update_privacy(
    payload: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = get_or_create_student(current_user, db)
    vis = db.query(models.StudentVisibilitySetting).filter(models.StudentVisibilitySetting.student_id == student.id).first()
    if not vis:
        vis = models.StudentVisibilitySetting(student_id=student.id)
        db.add(vis)

    if "profile" in payload or "profile_visible" in payload:
        vis.profile_visible = payload.get("profile", payload.get("profile_visible"))
    if "resume" in payload or "resume_visible" in payload:
        vis.resume_visible = payload.get("resume", payload.get("resume_visible"))
    if "github" in payload or "github_visible" in payload:
        vis.github_visible = payload.get("github", payload.get("github_visible"))
    if "linkedin" in payload or "linkedin_visible" in payload:
        vis.linkedin_visible = payload.get("linkedin", payload.get("linkedin_visible"))
    if "certificates" in payload or "certificates_visible" in payload:
        vis.certificates_visible = payload.get("certificates", payload.get("certificates_visible"))
    if "documents" in payload or "documents_visible" in payload:
        vis.documents_visible = payload.get("documents", payload.get("documents_visible"))
    if "projects" in payload or "projects_visible" in payload:
        vis.projects_visible = payload.get("projects", payload.get("projects_visible"))
    if "experience" in payload or "experience_visible" in payload:
        vis.experience_visible = payload.get("experience", payload.get("experience_visible"))

    db.commit()
    return {"success": True, "message": "Privacy settings updated."}
