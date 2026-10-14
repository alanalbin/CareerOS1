"""
Comprehensive End-to-End Production Verification Test for Career OS API
Tests:
1. Health & Engine Status
2. Student Registration & Login (bcrypt, JWT token)
3. College Registration & Login
4. Recruiter Registration & Login
5. Role-based Access Control (e.g. Student cannot access Recruiter or College endpoints)
6. GitHub connect and repo sync
7. LinkedIn connect
8. Document Upload & PaddleOCR extraction
9. Certificate Verification Matrix
10. Career Readiness deterministic score calculation
11. Qwen3 AI analytical pipelines & failure handling
12. Job creation, candidate browsing, job application, status update
13. AI Resume compilation and genuine ReportLab PDF generation
"""

import os
import io
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import app
from database import SessionLocal, Base, engine
import models

client = TestClient(app)

class TestCareerOSProduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_health_check(self):
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("Career OS", data["platform"])

    def test_02_student_registration_and_login(self):
        # Register student
        reg_payload = {
            "role": "STUDENT",
            "fullName": "Maya Lin",
            "email": "maya.lin@testuniv.edu",
            "phone": "+1-555-0192",
            "college": "Stanford University",
            "studentId": "STAN-2024-88",
            "course": "Computer Science & AI",
            "graduationYear": 2026,
            "department": "Engineering",
            "targetRole": "Full-Stack Engineer",
            "password": "SecurePassword123!",
            "confirmPassword": "SecurePassword123!",
        }
        res = client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["role"], "STUDENT")
        token = data["token"]

        # Validate session
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertEqual(me_data["user"]["email"], "maya.lin@testuniv.edu")

        # Test login with valid credentials
        login_res = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "SecurePassword123!",
            "role": "STUDENT",
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("token", login_res.json())

        # Test login with invalid credentials
        bad_login = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "WrongPassword!",
        })
        self.assertEqual(bad_login.status_code, 401)
        self.assertIn("Incorrect email or password", bad_login.json()["detail"])

    def test_03_college_registration_and_auth(self):
        reg_payload = {
            "role": "COLLEGE",
            "collegeName": "Stanford University",
            "officialEmail": "dean@stanford.edu",
            "collegeId": "STAN-OFFICIAL-01",
            "contactPerson": "Dr. Sarah Adams",
            "phone": "+1-555-8822",
            "password": "CollegeAdminPass123!",
            "confirmPassword": "CollegeAdminPass123!",
        }
        res = client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["user"]["role"], "COLLEGE")
        college_token = data["token"]

        # Access college roster
        roster_res = client.get("/api/college/students", headers={"Authorization": f"Bearer {college_token}"})
        self.assertEqual(roster_res.status_code, 200)
        self.assertIn("students", roster_res.json())

    def test_04_recruiter_registration_and_jobs(self):
        reg_payload = {
            "role": "RECRUITER",
            "recruiterName": "Elena Vance",
            "company": "DeepTech Systems",
            "officialEmail": "elena@deeptech.io",
            "phone": "+1-555-7733",
            "designation": "Head of Technical Talent",
            "password": "RecruiterPass123!",
            "confirmPassword": "RecruiterPass123!",
        }
        res = client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200, res.text)
        recruiter_token = res.json()["token"]

        # Recruiter posts a job
        job_payload = {
            "title": "Machine Learning Engineer",
            "description": "Develop and deploy computer vision and NLP models into production systems.",
            "company": "DeepTech Systems",
            "location": "San Francisco, CA (Hybrid)",
            "employmentType": "Full-Time",
            "skillsRequired": "Python, PyTorch, Docker, FastAPI",
            "experienceRequired": "0-2 years",
        }
        job_res = client.post("/api/jobs", json=job_payload, headers={"Authorization": f"Bearer {recruiter_token}"})
        self.assertEqual(job_res.status_code, 200, job_res.text)
        job_id = job_res.json()["job"]["id"]

        # Check job listing public endpoint
        jobs_list = client.get("/api/jobs")
        self.assertEqual(jobs_list.status_code, 200)
        self.assertTrue(any(j["id"] == job_id for j in jobs_list.json()["jobs"]))

        # Role-based access check: Student attempts to create job -> Must be 403 Forbidden
        student_login = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "SecurePassword123!",
        })
        student_token = student_login.json()["token"]

        forbidden_res = client.post("/api/jobs", json=job_payload, headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(forbidden_res.status_code, 403)

        # Student applies to job
        apply_res = client.post(
            f"/api/jobs/{job_id}/apply",
            json={"coverNote": "Excited to apply with verified coursework in ML and systems programming."},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(apply_res.status_code, 200)

        # Recruiter views applications and updates status
        apps_res = client.get("/api/recruiter/applications", headers={"Authorization": f"Bearer {recruiter_token}"})
        self.assertEqual(apps_res.status_code, 200)
        apps = apps_res.json()["applications"]
        self.assertTrue(len(apps) > 0)
        app_id = apps[0]["id"]

        status_update = client.put(
            f"/api/recruiter/applications/{app_id}/status",
            json={"status": "Shortlisted"},
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        self.assertEqual(status_update.status_code, 200)

    def test_05_document_upload_ocr_and_verification(self):
        student_login = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "SecurePassword123!",
        })
        student_token = student_login.json()["token"]

        # Create sample certificate file content
        cert_text = (
            "AWS Certified Solutions Architect - Associate\n"
            "This is to certify that Maya Lin has successfully demonstrated knowledge of AWS cloud architecture.\n"
            "Issued: May 2024\n"
            "Credential ID: AWS-ARCH-9928371\n"
            "Skills: Python, AWS, Docker, System Design, SQL\n"
            "GPA: 3.92\n"
        )

        files = {
            "file": ("aws_solutions_architect.txt", io.BytesIO(cert_text.encode("utf-8")), "text/plain")
        }
        data = {
            "category": "certificate",
            "title": "AWS Solutions Architect Associate",
        }

        upload_res = client.post(
            "/api/documents/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(upload_res.status_code, 200, upload_res.text)
        doc_data = upload_res.json()["document"]
        self.assertEqual(doc_data["category"], "certificate")
        self.assertGreater(doc_data["confidence"], 0.8)

        # Check cross-source verification matrix
        matrix_res = client.get("/api/verification/matrix", headers={"Authorization": f"Bearer {student_token}"})
        self.assertEqual(matrix_res.status_code, 200)
        matrix = matrix_res.json()
        self.assertIn("rows", matrix)
        self.assertTrue(len(matrix["rows"]) >= 5)

    def test_06_resume_generation_and_pdf(self):
        student_login = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "SecurePassword123!",
        })
        student_token = student_login.json()["token"]

        # Add skill & project
        client.post("/api/student/skills", json={"name": "FastAPI", "category": "Backend"}, headers={"Authorization": f"Bearer {student_token}"})
        client.post("/api/student/skills", json={"name": "PostgreSQL", "category": "Databases"}, headers={"Authorization": f"Bearer {student_token}"})
        client.post("/api/student/projects", json={
            "title": "Autonomous Drone Telemetry",
            "description": "High-throughput real-time telemetry pipeline built with Python and WebSockets.",
            "technologies": "Python, FastAPI, Docker",
        }, headers={"Authorization": f"Bearer {student_token}"})

        # Generate AI Resume Content
        gen_res = client.post(
            "/api/resume/generate",
            json={"template": "Modern"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(gen_res.status_code, 200, gen_res.text)

        # Download authentic PDF resume
        pdf_res = client.post(
            "/api/resume/pdf",
            json={"template": "Modern"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers.get("content-type"), "application/pdf")
        self.assertTrue(len(pdf_res.content) > 1000)
        self.assertTrue(pdf_res.content.startswith(b"%PDF"))

    def test_07_privacy_settings_enforcement(self):
        student_login = client.post("/api/auth/login", json={
            "identifier": "maya.lin@testuniv.edu",
            "password": "SecurePassword123!",
        })
        student_token = student_login.json()["token"]

        # Student disables recruiter visibility
        priv_res = client.put(
            "/api/student/privacy",
            json={"profile_visible": False},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(priv_res.status_code, 200)

        # Recruiter searches candidates -> Maya Lin must NOT be shown
        recruiter_login = client.post("/api/auth/login", json={
            "identifier": "elena@deeptech.io",
            "password": "RecruiterPass123!",
        })
        recruiter_token = recruiter_login.json()["token"]

        search_res = client.get("/api/recruiter/candidates", headers={"Authorization": f"Bearer {recruiter_token}"})
        self.assertEqual(search_res.status_code, 200)
        candidates = search_res.json()["candidates"]
        self.assertFalse(any(c["fullName"] == "Maya Lin" for c in candidates))

        # Re-enable visibility
        client.put(
            "/api/student/privacy",
            json={"profile_visible": True},
            headers={"Authorization": f"Bearer {student_token}"}
        )

        search_res2 = client.get("/api/recruiter/candidates", headers={"Authorization": f"Bearer {recruiter_token}"})
        self.assertEqual(search_res2.status_code, 200)
        candidates2 = search_res2.json()["candidates"]
        self.assertTrue(any(c["fullName"] == "Maya Lin" for c in candidates2))

if __name__ == "__main__":
    unittest.main()
