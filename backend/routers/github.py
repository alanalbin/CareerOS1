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
from ai_service import analyze_github_data

load_dotenv()

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

class ConnectGithubPayload(BaseModel):
    username: str
    token: Optional[str] = None
    code: Optional[str] = None

def fetch_github_user_and_repos(username: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Queries official GitHub REST API with real headers and token if provided."""
    headers = {
        "User-Agent": "Career-OS-Platform",
        "Accept": "application/vnd.github.v3+json",
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    # Fetch user profile
    u_res = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=12)
    if u_res.status_code == 404:
        raise HTTPException(status_code=404, detail=f'GitHub user "{username}" was not found.')
    if u_res.status_code in [403, 429]:
        raise HTTPException(
            status_code=429,
            detail="GitHub API rate limit reached. Please provide a Personal Access Token or OAuth code."
        )
    if u_res.status_code != 200:
        raise HTTPException(status_code=400, detail="GitHub data is currently unavailable.")

    gh_user = u_res.json()

    # Fetch repos
    repos_res = requests.get(
        f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30",
        headers=headers,
        timeout=12
    )
    repos = []
    languages: Dict[str, int] = {}

    if repos_res.status_code == 200:
        for r in repos_res.json():
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
            repos.append({
                "name": r.get("name"),
                "description": r.get("description"),
                "language": lang or "Other",
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "html_url": r.get("html_url"),
                "updated_at": r.get("updated_at"),
            })

    top_langs = sorted(languages.keys(), key=lambda l: languages[l], reverse=True)[:6]

    return {
        "username": gh_user.get("login") or username,
        "profile_url": gh_user.get("html_url") or f"https://github.com/{username}",
        "avatar_url": gh_user.get("avatar_url"),
        "bio": gh_user.get("bio") or "",
        "public_repos": gh_user.get("public_repos", len(repos)),
        "followers": gh_user.get("followers", 0),
        "following": gh_user.get("following", 0),
        "top_languages": top_langs,
        "repos": repos,
    }

@router.post("/connect")
def connect_github(
    payload: ConnectGithubPayload,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Only student accounts can connect a GitHub portfolio.")

    clean_username = payload.username.strip().replace("https://github.com/", "").replace("/", "")
    if not clean_username:
        raise HTTPException(status_code=400, detail="GitHub username is required.")

    # Exchange OAuth code for token if provided and secrets configured
    token = payload.token
    if payload.code and GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
        try:
            token_res = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": payload.code,
                },
                timeout=10,
            )
            if token_res.status_code == 200:
                token_data = token_res.json()
                token = token_data.get("access_token")
        except Exception:
            pass

    gh_data = fetch_github_user_and_repos(clean_username, token)

    # Persist or update GitHubProfile
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
    gh_profile.last_synced_at = datetime.datetime.utcnow()

    # Clear old repos and add fresh repos
    db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh_profile.id).delete()
    db.flush()

    for r in gh_data["repos"]:
        repo_rec = models.GitHubRepository(
            github_profile_id=gh_profile.id,
            name=r["name"],
            description=r["description"],
            language=r["language"],
            stars=r["stars"],
            forks=r["forks"],
            html_url=r["html_url"],
            updated_at=r["updated_at"],
        )
        db.add(repo_rec)

    # Update student avatar if not set
    if not student.avatar_url:
        student.avatar_url = gh_data["avatar_url"]

    db.commit()
    db.refresh(gh_profile)

    return {
        "success": True,
        "profile": {
            "id": gh_profile.id,
            "username": gh_profile.username,
            "profileUrl": gh_profile.profile_url,
            "avatarUrl": gh_profile.avatar_url,
            "publicRepos": gh_profile.public_repos,
            "followers": gh_profile.followers,
            "topLanguages": gh_profile.top_languages,
            "connectedAt": gh_profile.connected_at.isoformat() if gh_profile.connected_at else None,
            "lastSyncedAt": gh_profile.last_synced_at.isoformat() if gh_profile.last_synced_at else None,
            "repos": gh_data["repos"],
        }
    }

@router.get("/profile")
def get_github_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        return {"profile": None}

    gh_profile = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    if not gh_profile:
        return {"profile": None}

    repos = db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh_profile.id).all()

    return {
        "profile": {
            "id": gh_profile.id,
            "username": gh_profile.username,
            "profileUrl": gh_profile.profile_url,
            "avatarUrl": gh_profile.avatar_url,
            "bio": gh_profile.bio,
            "publicRepos": gh_profile.public_repos,
            "followers": gh_profile.followers,
            "following": gh_profile.following,
            "topLanguages": gh_profile.top_languages,
            "connectedAt": gh_profile.connected_at.isoformat() if gh_profile.connected_at else None,
            "lastSyncedAt": gh_profile.last_synced_at.isoformat() if gh_profile.last_synced_at else None,
            "repos": [
                {
                    "name": r.name,
                    "description": r.description,
                    "language": r.language,
                    "stars": r.stars,
                    "forks": r.forks,
                    "html_url": r.html_url,
                    "updated_at": r.updated_at,
                }
                for r in repos
            ],
        }
    }

@router.post("/disconnect")
def disconnect_github(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if student:
        db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).delete()
        db.commit()
    return {"success": True, "message": "GitHub profile disconnected."}

@router.post("/analyze")
def analyze_github(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required.")

    gh_profile = db.query(models.GitHubProfile).filter(models.GitHubProfile.student_id == student.id).first()
    if not gh_profile:
        raise HTTPException(status_code=400, detail="No GitHub account connected.")

    repos = db.query(models.GitHubRepository).filter(models.GitHubRepository.github_profile_id == gh_profile.id).all()
    repo_dicts = [{"name": r.name, "description": r.description, "language": r.language, "stars": r.stars, "forks": r.forks} for r in repos]

    res = analyze_github_data(
        username=gh_profile.username,
        repos=repo_dicts,
        top_languages=gh_profile.top_languages or [],
    )

    if res.get("success"):
        record = models.AIAnalysis(
            student_id=student.id,
            analysis_type="github",
            content=res.get("data"),
            model_used="qwen3.8-flash",
        )
        db.add(record)
        db.commit()

    return res
