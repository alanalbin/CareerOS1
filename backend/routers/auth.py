import re
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from database import get_db
import models
from security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_optional,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class StudentRegisterSchema(BaseModel):
    fullName: str
    email: EmailStr
    phone: Optional[str] = None
    college: Optional[str] = None
    studentId: Optional[str] = None
    course: Optional[str] = None
    graduationYear: Optional[int] = None
    password: str
    confirmPassword: str

class CollegeRegisterSchema(BaseModel):
    collegeName: str
    officialEmail: EmailStr
    collegeId: Optional[str] = None
    contactPerson: str
    phone: Optional[str] = None
    password: str
    confirmPassword: str

class RecruiterRegisterSchema(BaseModel):
    recruiterName: str
    company: str
    officialEmail: EmailStr
    phone: Optional[str] = None
    designation: Optional[str] = None
    password: str
    confirmPassword: str

class GenericRegisterRequest(BaseModel):
    role: Optional[str] = "STUDENT"
    # Common
    email: Optional[str] = None
    password: Optional[str] = None
    confirmPassword: Optional[str] = None
    # Student specific
    fullName: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    studentId: Optional[str] = None
    course: Optional[str] = None
    graduationYear: Optional[int] = None
    department: Optional[str] = None
    targetRole: Optional[str] = None
    # College specific
    collegeName: Optional[str] = None
    officialEmail: Optional[str] = None
    collegeId: Optional[str] = None
    contactPerson: Optional[str] = None
    institutionName: Optional[str] = None
    # Recruiter specific
    recruiterName: Optional[str] = None
    company: Optional[str] = None
    companyName: Optional[str] = None
    designation: Optional[str] = None

class LoginRequest(BaseModel):
    identifier: Optional[str] = None
    email: Optional[str] = None
    password: str
    role: Optional[str] = None

def serialize_user(user: models.User, db: Session) -> Dict[str, Any]:
    role = (user.role or "STUDENT").upper()
    data = {
        "id": user.id,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": role,
        "phone": user.phone,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }

    if role == "STUDENT":
        student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if student:
            data.update({
                "studentId": student.id,
                "collegeName": student.college_name,
                "studentIdNumber": student.student_id_number,
                "course": student.course,
                "graduationYear": student.graduation_year,
                "cgpa": student.cgpa,
                "targetRole": student.target_role,
                "department": student.department,
                "bio": student.bio,
                "avatarUrl": student.avatar_url,
            })
    elif role in ["COLLEGE", "COLLEGE_ADMIN"]:
        college = db.query(models.College).filter(models.College.user_id == user.id).first()
        if college:
            data.update({
                "collegeId": college.id,
                "collegeName": college.college_name,
                "officialEmail": college.official_email,
                "collegeIdCode": college.college_id_code,
                "contactPerson": college.contact_person,
            })
    elif role == "RECRUITER":
        recruiter = db.query(models.Recruiter).filter(models.Recruiter.user_id == user.id).first()
        if recruiter:
            data.update({
                "recruiterId": recruiter.id,
                "recruiterName": recruiter.recruiter_name,
                "company": recruiter.company,
                "officialEmail": recruiter.official_email,
                "designation": recruiter.designation,
            })

    return data

@router.post("/register")
def register(payload: GenericRegisterRequest, response: Response, db: Session = Depends(get_db)):
    role = (payload.role or "STUDENT").upper()
    if role == "COLLEGE_ADMIN":
        role = "COLLEGE"

    email = (payload.email or payload.officialEmail or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Official email address is required.")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    if payload.confirmPassword and payload.password != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Check if user already exists
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    pwd_hash = hash_password(payload.password)

    if role == "STUDENT":
        full_name = (payload.fullName or f"{payload.email.split('@')[0]}").strip()
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        user = models.User(
            email=email,
            password_hash=pwd_hash,
            role="STUDENT",
            first_name=first_name,
            last_name=last_name,
            phone=payload.phone,
        )
        db.add(user)
        db.flush()

        student = models.Student(
            user_id=user.id,
            college_name=payload.college,
            student_id_number=payload.studentId,
            course=payload.course,
            graduation_year=payload.graduationYear,
            department=payload.department,
            target_role=payload.targetRole or "Software Engineer",
        )
        db.add(student)
        db.flush()

        # Initialize default visibility settings
        vis = models.StudentVisibilitySetting(
            student_id=student.id,
            profile_visible=True,
            resume_visible=True,
            github_visible=True,
            linkedin_visible=True,
            certificates_visible=True,
            documents_visible=False,
            projects_visible=True,
            experience_visible=True,
        )
        db.add(vis)
        db.commit()
        db.refresh(user)

    elif role in ["COLLEGE", "COLLEGE_ADMIN"]:
        contact_person = (payload.contactPerson or "Administrator").strip()
        parts = contact_person.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        college_name = (payload.collegeName or payload.institutionName or "Partner College").strip()

        user = models.User(
            email=email,
            password_hash=pwd_hash,
            role="COLLEGE",
            first_name=first_name,
            last_name=last_name,
            phone=payload.phone,
        )
        db.add(user)
        db.flush()

        college = models.College(
            user_id=user.id,
            college_name=college_name,
            official_email=email,
            college_id_code=payload.collegeId,
            contact_person=contact_person,
            phone=payload.phone,
        )
        db.add(college)
        db.commit()
        db.refresh(user)

    elif role == "RECRUITER":
        recruiter_name = (payload.recruiterName or "Recruiter").strip()
        parts = recruiter_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        company = (payload.company or payload.companyName or "Hiring Partner").strip()

        user = models.User(
            email=email,
            password_hash=pwd_hash,
            role="RECRUITER",
            first_name=first_name,
            last_name=last_name,
            phone=payload.phone,
        )
        db.add(user)
        db.flush()

        recruiter = models.Recruiter(
            user_id=user.id,
            recruiter_name=recruiter_name,
            company=company,
            official_email=email,
            phone=payload.phone,
            designation=payload.designation,
        )
        db.add(recruiter)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    response.set_cookie(
        key="careeros_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
    )

    return {
        "status": "success",
        "token": token,
        "user": serialize_user(user, db),
    }

@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = (payload.identifier or payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Incorrect email or password.")
    if not payload.password:
        raise HTTPException(status_code=400, detail="Incorrect email or password.")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    # Role validation if specified
    if payload.role:
        expected = payload.role.upper()
        user_role = (user.role or "").upper()
        if expected in ["COLLEGE", "COLLEGE_ADMIN"] and user_role not in ["COLLEGE", "COLLEGE_ADMIN"]:
            raise HTTPException(status_code=403, detail=f"This account is registered as {user.role}, not {expected}.")
        elif expected not in ["COLLEGE", "COLLEGE_ADMIN"] and user_role != expected:
            raise HTTPException(status_code=403, detail=f"This account is registered as {user.role}, not {expected}.")

    token = create_access_token({"sub": str(user.id), "role": user.role, "email": user.email})
    response.set_cookie(
        key="careeros_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
    )

    return {
        "status": "success",
        "token": token,
        "user": serialize_user(user, db),
    }

@router.get("/me")
@router.post("/me")
@router.get("/session")
def get_session(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return {"user": None, "profile": None}
    return {
        "user": serialize_user(user, db),
        "profile": serialize_user(user, db),
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("careeros_token")
    return {"status": "success", "message": "Successfully logged out."}

@router.post("/requestPasswordReset")
def request_password_reset(payload: Dict[str, Any]):
    return {"message": "If that email is registered, password reset instructions have been sent."}
