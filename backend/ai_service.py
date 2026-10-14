import os
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("careeros.ai")

# OpenAI compatible client setup
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL") or os.getenv("QWEN_API_URL") or "https://maas.qwencloudapi.com/compatible-mode/v1"
QWEN_MODEL = os.getenv("QWEN_MODEL") or "qwen3.8-flash"

SYSTEM_INSTRUCTION = """You are the Career OS AI career analysis assistant.

Analyze only the information provided to you.

Never invent:
- academic qualifications
- marks
- projects
- employment
- internships
- certificates
- skills
- GitHub repositories
- LinkedIn experience
- achievements

Clearly distinguish:
1. User-provided information
2. OCR-extracted information
3. API-derived information
4. Verified information
5. AI-generated analysis

If information is missing, explicitly state that it is unavailable.

Do not present an inference as a verified fact.

Provide useful career guidance based only on available information.
Always respond in valid JSON format matching the requested schema.
"""

def get_openai_client():
    if not DASHSCOPE_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30.0,
        )
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI Qwen client: {e}")
        return None

def call_qwen_chat(prompt: str, json_schema_description: Optional[str] = None) -> Dict[str, Any]:
    """Invokes Qwen3 AI using OpenAI-compatible API with safe failure handling."""
    client = get_openai_client()
    if not client:
        return {
            "success": False,
            "available": False,
            "message": "AI analysis is currently unavailable. (API key not configured)"
        }

    full_prompt = prompt
    if json_schema_description:
        full_prompt += f"\n\nReturn your response strictly as valid JSON adhering to this schema:\n{json_schema_description}"

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": full_prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=messages,
            response_format={"type": "json_object"} if "flash" in QWEN_MODEL or "max" in QWEN_MODEL else None,
            temperature=0.3,
            max_tokens=1500,
        )
        content = response.choices[0].message.content.strip()

        # Parse JSON
        try:
            parsed = json.loads(content)
            return {"success": True, "available": True, "data": parsed, "raw": content}
        except json.JSONDecodeError:
            # Clean markdown codeblocks if present
            if "```" in content:
                cleaned = content.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
                try:
                    parsed = json.loads(cleaned)
                    return {"success": True, "available": True, "data": parsed, "raw": content}
                except Exception:
                    pass
            return {"success": True, "available": True, "data": {"text": content}, "raw": content}

    except Exception as e:
        logger.warning(f"Qwen AI call failed: {e}")
        return {
            "success": False,
            "available": False,
            "message": "AI analysis is currently unavailable."
        }

def analyze_github_data(username: str, repos: List[Dict[str, Any]], top_languages: List[str]) -> Dict[str, Any]:
    """Analyzes authenticated GitHub repositories via Qwen3."""
    if not repos:
        return {
            "success": True,
            "available": True,
            "data": {
                "summary": f"No public repositories found for @{username} to analyze.",
                "technicalStrengths": [],
                "areasForImprovement": ["Upload project code to GitHub repositories to showcase implementation skills."],
                "technologiesDemonstrated": top_languages,
                "readinessScoreImpact": "0 pts"
            }
        }

    simplified_repos = [
        {
            "name": r.get("name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stars", 0),
            "forks": r.get("forks", 0)
        }
        for r in repos[:10]
    ]

    prompt = f"""Analyze the following authorized GitHub profile for user @{username}:
Top Languages: {', '.join(top_languages) if top_languages else 'None listed'}
Repositories:
{json.dumps(simplified_repos, indent=2)}

Provide an objective code audit covering:
1. summary (objective 2-3 sentence overview)
2. technicalStrengths (list of 3-4 demonstrated engineering patterns based on observed repo topics/languages)
3. areasForImprovement (list of 2-3 concrete actionable engineering steps such as CI/CD, tests, docs)
4. technologiesDemonstrated (list of technologies clearly present in the repos)
5. careerRelevance (which software roles these projects best support)
"""
    schema = '{"summary": "...", "technicalStrengths": ["..."], "areasForImprovement": ["..."], "technologiesDemonstrated": ["..."], "careerRelevance": "..."}'
    res = call_qwen_chat(prompt, schema)
    if not res.get("success"):
        return res
    return res

def analyze_linkedin_data(headline: Optional[str], skills: List[str], experience: List[Any]) -> Dict[str, Any]:
    """Analyzes authorized LinkedIn profile information via Qwen3."""
    prompt = f"""Analyze this authorized professional profile:
Headline: {headline or 'Not provided'}
Skills: {', '.join(skills) if skills else 'None listed'}
Experience: {json.dumps(experience)}

Provide an assessment covering:
1. professionalStrengths (list of observed career strengths)
2. profileCompleteness (estimated percentage and missing profile dimensions)
3. careerAlignment (analysis of how skills align with modern industry requirements)
4. suggestedImprovements (concrete steps to improve professional visibility)
"""
    schema = '{"professionalStrengths": ["..."], "profileCompleteness": 80, "careerAlignment": "...", "suggestedImprovements": ["..."]}'
    res = call_qwen_chat(prompt, schema)
    if not res.get("success"):
        return res
    return res

def analyze_certificate_data(cert_title: str, issuer: str, ocr_text: str, structured_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes an uploaded certificate and its OCR extraction via Qwen3."""
    prompt = f"""Analyze this certificate extraction:
Title: {cert_title}
Issuer: {issuer}
OCR Text:
{ocr_text[:1500]}
Structured Fields:
{json.dumps(structured_fields)}

Provide:
1. category (Course, Workshop, Hackathon, Professional Certification, Internship, or Academic)
2. skillsIdentified (list of verified skills or topics mentioned)
3. summary (brief factual summary)
4. careerRelevance (relevance to software/technical roles)
5. resumeBulletPoint (a concise, professional resume-ready bullet point)
6. missingFields (fields that could not be determined from the certificate)
"""
    schema = '{"category": "...", "skillsIdentified": ["..."], "summary": "...", "careerRelevance": "...", "resumeBulletPoint": "...", "missingFields": ["..."]}'
    res = call_qwen_chat(prompt, schema)
    if not res.get("success"):
        return res
    return res

def generate_career_guidance_and_gaps(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates career guidance, skill gap analysis, and readiness recommendations via Qwen3."""
    prompt = f"""Based solely on this student profile:
Education: {json.dumps(student_data.get('education', []))}
Skills: {json.dumps(student_data.get('skills', []))}
Projects: {json.dumps(student_data.get('projects', []))}
Certifications: {json.dumps(student_data.get('certifications', []))}
Internships: {json.dumps(student_data.get('internships', []))}
GitHub Summary: {json.dumps(student_data.get('github', {}))}
Target Role: {student_data.get('targetRole', 'Software Engineer')}

Analyze this student's career preparation:
1. recommendedRoles (top 3 suitable roles based on evidence)
2. primaryRoleFitScore (0 to 100 estimated fit for target role)
3. existingStrengths (list of evidenced capabilities)
4. missingSkills (critical skills needed for the target role that are not evidenced)
5. actionableNextSteps (3 practical steps with estimated hours and skill focus)
6. readinessSummary (evidence-grounded assessment)
"""
    schema = '{"recommendedRoles": ["..."], "primaryRoleFitScore": 85, "existingStrengths": ["..."], "missingSkills": ["..."], "actionableNextSteps": [{"title": "...", "skill": "...", "time": "2 hrs", "reason": "..."}], "readinessSummary": "..."}'
    res = call_qwen_chat(prompt, schema)
    if not res.get("success"):
        return res
    return res

def generate_ai_resume_content(student_data: Dict[str, Any], selected_cert_ids: List[int]) -> Dict[str, Any]:
    """Uses Qwen3 to polish and organize genuine student data into resume-ready copy."""
    certs = student_data.get("certifications", [])
    if selected_cert_ids:
        certs = [c for c in certs if c.get("id") in selected_cert_ids]

    prompt = f"""Format and polish the following student career information into professional, high-impact resume sections.
DO NOT invent any qualifications, skills, degrees, or companies not present in the input.

Candidate Name: {student_data.get('name', 'Student')}
Target Role: {student_data.get('targetRole', 'Software Engineer')}
Education: {json.dumps(student_data.get('education', []))}
Skills: {json.dumps(student_data.get('skills', []))}
Projects: {json.dumps(student_data.get('projects', []))}
Certifications: {json.dumps(certs)}
Internships & Experience: {json.dumps(student_data.get('experience', []) + student_data.get('internships', []))}
GitHub: {json.dumps(student_data.get('github', {}))}

Return structured sections:
1. professionalSummary (concise 3-4 sentence professional summary)
2. technicalSkills (categorized by Languages, Frameworks, Developer Tools, Databases)
3. projects (list of projects with polished action-oriented bullet points)
4. experience (list of internships/experience with polished bullet points)
5. education (formatted institution, degree, year, CGPA if present)
6. certifications (list of selected verified certifications)
"""
    schema = '{"professionalSummary": "...", "technicalSkills": {"Languages": ["..."], "Frameworks": ["..."], "Tools": ["..."]}, "projects": [{"title": "...", "technologies": "...", "bullets": ["..."]}], "experience": [{"company": "...", "role": "...", "period": "...", "bullets": ["..."]}], "education": [{"institution": "...", "degree": "...", "year": "...", "grade": "..."}], "certifications": [{"title": "...", "issuer": "...", "date": "..."}]}'
    res = call_qwen_chat(prompt, schema)
    if not res.get("success"):
        return res
    return res
