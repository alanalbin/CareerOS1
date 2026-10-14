import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # STUDENT, COLLEGE, RECRUITER
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    college_profile = relationship("College", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recruiter_profile = relationship("Recruiter", back_populates="user", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    college_name = Column(String(255), nullable=True)
    student_id_number = Column(String(100), nullable=True)
    course = Column(String(255), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    cgpa = Column(Float, nullable=True)
    target_role = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="student_profile")
    education_records = relationship("Education", back_populates="student", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="student", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="student", cascade="all, delete-orphan")
    experience_records = relationship("Experience", back_populates="student", cascade="all, delete-orphan")
    internships = relationship("Internship", back_populates="student", cascade="all, delete-orphan")
    leadership_records = relationship("Leadership", back_populates="student", cascade="all, delete-orphan")
    certifications = relationship("Certification", back_populates="student", cascade="all, delete-orphan")
    github_profile = relationship("GitHubProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    linkedin_profile = relationship("LinkedInProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    visibility_settings = relationship("StudentVisibilitySetting", back_populates="student", uselist=False, cascade="all, delete-orphan")
    readiness_records = relationship("CareerReadiness", back_populates="student", cascade="all, delete-orphan")
    ai_analyses = relationship("AIAnalysis", back_populates="student", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="student", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="student", cascade="all, delete-orphan")


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    college_name = Column(String(255), nullable=False)
    official_email = Column(String(255), nullable=False)
    college_id_code = Column(String(100), nullable=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="college_profile")


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    recruiter_name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    official_email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    designation = Column(String(255), nullable=True)
    company_website = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recruiter_profile")
    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), nullable=False)
    field_of_study = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    grade_cgpa = Column(String(50), nullable=True)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="education_records")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(100), default="Technical")
    proficiency = Column(String(50), default="Intermediate")
    verified = Column(Boolean, default=False)
    source = Column(String(50), default="Account")  # Account, GitHub, LinkedIn, OCR, College
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="skills")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    technologies = Column(String(500), nullable=True)
    project_url = Column(String(500), nullable=True)
    github_repo = Column(String(500), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="projects")


class Experience(Base):
    __tablename__ = "experience"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="experience_records")


class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    duration = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    certificate_id = Column(String(100), nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="internships")


class Leadership(Base):
    __tablename__ = "leadership"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    role_title = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="leadership_records")


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    title = Column(String(255), nullable=False)
    issuer = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=True)
    expiration_date = Column(String(50), nullable=True)
    credential_id = Column(String(255), nullable=True)
    credential_url = Column(String(500), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="certifications")
    document = relationship("Document")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    category = Column(String(50), default="certificate")  # certificate, transcript, resume, other
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="documents")
    extractions = relationship("DocumentExtraction", back_populates="document", cascade="all, delete-orphan")
    verification = relationship("CertificateVerification", back_populates="document", uselist=False, cascade="all, delete-orphan")


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    raw_text = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="extractions")


class CertificateVerification(Base):
    __tablename__ = "certificate_verifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, VERIFIED, REJECTED, NEEDS_REVIEW
    verification_notes = Column(Text, nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="verification")


class GitHubProfile(Base):
    __tablename__ = "github_profiles"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    profile_url = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    public_repos = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    top_languages = Column(JSON, default=list)
    connected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_synced_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="github_profile")
    repositories = relationship("GitHubRepository", back_populates="profile", cascade="all, delete-orphan")


class GitHubRepository(Base):
    __tablename__ = "github_repositories"

    id = Column(Integer, primary_key=True, index=True)
    github_profile_id = Column(Integer, ForeignKey("github_profiles.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(100), nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    html_url = Column(String(500), nullable=False)
    updated_at = Column(String(100), nullable=True)

    profile = relationship("GitHubProfile", back_populates="repositories")


class LinkedInProfile(Base):
    __tablename__ = "linkedin_profiles"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    profile_url = Column(String(255), nullable=False)
    headline = Column(String(255), nullable=True)
    skills = Column(JSON, default=list)
    experience = Column(JSON, default=list)
    connected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_synced_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="linkedin_profile")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)  # Career OS, OCR, LinkedIn, GitHub, College
    reported_value = Column(Text, nullable=True)
    verified_value = Column(Text, nullable=True)
    status = Column(String(50), default="Needs Review")  # Verified, Consistent, Partially Verified, Mismatch, Needs Review, Unable to Verify
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="verification_results")


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    analysis_type = Column(String(100), nullable=False)  # github, linkedin, certificate, career_guidance, skill_gap, readiness, resume
    content = Column(JSON, nullable=False)
    model_used = Column(String(100), default="qwen3.8-flash")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="ai_analyses")


class CareerReadiness(Base):
    __tablename__ = "career_readiness"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    overall_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    academic_score = Column(Float, default=0.0)
    evidence_score = Column(Float, default=0.0)
    soft_skills_score = Column(Float, default=0.0)
    breakdown = Column(JSON, nullable=True)
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student", back_populates="readiness_records")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    employment_type = Column(String(50), default="Full-Time")  # Full-Time, Internship, Contract, Remote
    skills_required = Column(Text, nullable=True)
    experience_required = Column(String(100), nullable=True)
    status = Column(String(50), default="OPEN")  # OPEN, CLOSED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    recruiter = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    status = Column(String(50), default="Applied")  # Applied, Under Review, Shortlisted, Interview, Selected, Rejected, Withdrawn
    cover_note = Column(Text, nullable=True)
    resume_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="applications")
    student = relationship("Student", back_populates="applications")


class StudentVisibilitySetting(Base):
    __tablename__ = "student_visibility_settings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    profile_visible = Column(Boolean, default=True)
    resume_visible = Column(Boolean, default=True)
    github_visible = Column(Boolean, default=True)
    linkedin_visible = Column(Boolean, default=True)
    certificates_visible = Column(Boolean, default=True)
    documents_visible = Column(Boolean, default=False)
    projects_visible = Column(Boolean, default=True)
    experience_visible = Column(Boolean, default=True)

    student = relationship("Student", back_populates="visibility_settings")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
