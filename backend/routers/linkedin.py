import os
import requests
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from database import get_db
import models
from security import get_current_user
from ai_service import analyze_linkedin_data

load_dotenv()

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

class ConnectLinkedinPayload(BaseModel):
    profileUrl: str
    headline: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    code: Optional[str] = None

@router.post("/connect")
def connect_linkedin(
    payload: ConnectLinkedinPayload,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Only student accounts can connect a LinkedIn profile.")

    raw_url = payload.profileUrl.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="LinkedIn profile URL or vanity username is required.")

    clean_handle = (
        raw_url.replace("https://www.linkedin.com/in/", "")
        .replace("https://linkedin.com/in/", "")
        .replace("/", "")
        .strip()
    )
    if not clean_handle:
        clean_handle = "professional"

    canonical_url = f"https://www.linkedin.com/in/{clean_handle}"

    headline = payload.headline or ""
    skills = payload.skills or []
    experience = payload.experience or []

    # If OAuth code is provided and LinkedIn API credentials exist, exchange for token & fetch permitted profile
    if payload.code and LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET:
        try:
            token_res = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": payload.code,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                    "redirect_uri": "http://localhost:5173/auth/linkedin/callback",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            if token_res.status_code == 200:
                access_token = token_res.json().get("access_token")
                # Query userinfo
                u_res = requests.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if u_res.status_code == 200:
                    u_data = u_res.json()
                    headline = u_data.get("name") or headline
        except Exception:
            pass

    li_profile = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    if not li_profile:
        li_profile = models.LinkedInProfile(student_id=student.id, username=clean_handle)
        db.add(li_profile)

    li_profile.username = clean_handle
    li_profile.profile_url = canonical_url
    li_profile.headline = headline
    li_profile.skills = skills
    li_profile.experience = experience
    li_profile.last_synced_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(li_profile)

    return {
        "success": True,
        "profile": {
            "id": li_profile.id,
            "username": li_profile.username,
            "profileUrl": li_profile.profile_url,
            "headline": li_profile.headline,
            "skills": li_profile.skills,
            "experience": li_profile.experience,
            "connectedAt": li_profile.connected_at.isoformat() if li_profile.connected_at else None,
            "lastSyncedAt": li_profile.last_synced_at.isoformat() if li_profile.last_synced_at else None,
        }
    }

@router.get("/profile")
def get_linkedin_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        return {"profile": None}

    li_profile = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    if not li_profile:
        return {"profile": None}

    return {
        "profile": {
            "id": li_profile.id,
            "username": li_profile.username,
            "profileUrl": li_profile.profile_url,
            "headline": li_profile.headline,
            "skills": li_profile.skills,
            "experience": li_profile.experience,
            "connectedAt": li_profile.connected_at.isoformat() if li_profile.connected_at else None,
            "lastSyncedAt": li_profile.last_synced_at.isoformat() if li_profile.last_synced_at else None,
        }
    }

@router.post("/disconnect")
def disconnect_linkedin(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if student:
        db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).delete()
        db.commit()
    return {"success": True, "message": "LinkedIn profile disconnected."}

@router.post("/analyze")
def analyze_linkedin(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    li_profile = db.query(models.LinkedInProfile).filter(models.LinkedInProfile.student_id == student.id).first()
    if not li_profile:
        raise HTTPException(status_code=400, detail="No LinkedIn account connected.")

    res = analyze_linkedin_data(
        headline=li_profile.headline,
        skills=li_profile.skills or [],
        experience=li_profile.experience or [],
    )

    if res.get("success"):
        record = models.AIAnalysis(
            student_id=student.id,
            analysis_type="linkedin",
            content=res.get("data"),
            model_used="qwen3.8-flash",
        )
        db.add(record)
        db.commit()

    return res
