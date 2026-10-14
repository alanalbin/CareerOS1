import os
import io
import re
import tempfile
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("careeros.ocr")

_paddle_ocr_instance = None

def get_paddle_ocr():
    global _paddle_ocr_instance
    if _paddle_ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            try:
                _paddle_ocr_instance = PaddleOCR(use_textline_orientation=True, lang='en')
            except TypeError:
                try:
                    _paddle_ocr_instance = PaddleOCR(use_angle_cls=True, lang='en')
                except Exception:
                    _paddle_ocr_instance = PaddleOCR(lang='en')
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"PaddleOCR initialization deferred or unavailable: {e}")
            _paddle_ocr_instance = None
    return _paddle_ocr_instance

def extract_structured_certificate_fields(text: str) -> Dict[str, Any]:
    """Extracts structured fields like student name, issuer, course, dates, and ID from raw text."""
    fields: Dict[str, Any] = {
        "candidateName": None,
        "certificateName": None,
        "issuer": None,
        "course": None,
        "date": None,
        "duration": None,
        "certificateId": None,
        "skills": [],
        "cgpa": None,
        "achievement": None,
    }

    # Certificate / Course ID
    id_match = re.search(r'(?:Certificate\s*ID|Credential\s*ID|License\s*ID|ID|Verification\s*Code)[:\s#]*([A-Z0-9\-_]{6,30})', text, re.IGNORECASE)
    if id_match:
        fields["certificateId"] = id_match.group(1).strip()

    # Date extraction (e.g. May 2024, 2024-05-12, 12/05/2024)
    date_match = re.search(r'(?:Date|Issued|Completed|Awarded\s*on)[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},\s*[0-9]{4}|[A-Za-z]+\s+[0-9]{4})', text, re.IGNORECASE)
    if date_match:
        fields["date"] = date_match.group(1).strip()
    else:
        general_date = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', text, re.IGNORECASE)
        if general_date:
            fields["date"] = general_date.group(0).strip()

    # Issuer detection
    issuers = [
        "Amazon Web Services", "AWS", "Google Cloud", "Google", "Microsoft", "Meta",
        "Coursera", "edX", "Udemy", "Stanford", "MIT", "Harvard", "Oracle",
        "Cisco", "IBM", "HackerRank", "LeetCode", "freeCodeCamp", "DeepLearning.AI"
    ]
    for iss in issuers:
        if re.search(r'\b' + re.escape(iss) + r'\b', text, re.IGNORECASE):
            fields["issuer"] = iss
            break

    # Student name detection patterns
    # Typically follows: "This is to certify that [Name]" or "Presented to [Name]"
    name_match = re.search(r'(?:certify that|presented to|awarded to|this certificate is proudly presented to|certifies that)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', text, re.IGNORECASE)
    if name_match:
        fields["candidateName"] = name_match.group(1).strip()

    # CGPA or Grade detection
    cgpa_match = re.search(r'(?:CGPA|GPA|Grade Point)[:\s]*([0-9]\.[0-9]{1,2})', text, re.IGNORECASE)
    if cgpa_match:
        try:
            fields["cgpa"] = float(cgpa_match.group(1))
        except ValueError:
            pass

    # Duration detection (e.g., 8 weeks, 40 hours)
    duration_match = re.search(r'([0-9]+\s*(?:hours|weeks|months|days))', text, re.IGNORECASE)
    if duration_match:
        fields["duration"] = duration_match.group(1)

    # Skills detection
    skill_dictionary = [
        "Python", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js",
        "FastAPI", "Django", "Flask", "SQL", "PostgreSQL", "MongoDB", "MySQL",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "Linux",
        "Machine Learning", "Deep Learning", "Data Science", "Artificial Intelligence",
        "Natural Language Processing", "Computer Vision", "Cybersecurity", "DevOps",
        "System Design", "Agile", "Scrum", "REST APIs", "GraphQL"
    ]
    detected_skills = []
    for skill in skill_dictionary:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            if skill not in detected_skills:
                detected_skills.append(skill)
    fields["skills"] = detected_skills

    return fields

def process_file_with_ocr(file_bytes: bytes, filename: str, mime_type: str) -> Dict[str, Any]:
    """Runs PaddleOCR on the file with fallbacks to PyPDF / text extraction."""
    extracted_lines: List[str] = []
    total_conf = 0.0
    conf_count = 0

    ocr = get_paddle_ocr()

    # If PaddleOCR is available and it's an image or image-like
    if ocr is not None:
        try:
            suffix = os.path.splitext(filename)[1] or ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                results = ocr.ocr(tmp_path, cls=True)
                if results and len(results) > 0 and results[0]:
                    for item in results[0]:
                        if len(item) > 1 and len(item[1]) > 1:
                            text_line = item[1][0]
                            conf_val = float(item[1][1])
                            extracted_lines.append(text_line)
                            total_conf += conf_val
                            conf_count += 1
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"PaddleOCR processing error: {e}")

    # Fallback to PDF extraction if no lines or PDF file
    if len(extracted_lines) == 0:
        if "pdf" in mime_type.lower() or filename.lower().endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        extracted_lines.append(txt)
                total_conf = 0.92
                conf_count = 1
            except Exception as e:
                logger.warning(f"PDF extraction error: {e}")
        elif "text" in mime_type.lower() or filename.lower().endswith(".txt"):
            try:
                text_content = file_bytes.decode("utf-8", errors="ignore")
                extracted_lines.append(text_content)
                total_conf = 0.95
                conf_count = 1
            except Exception:
                pass

    raw_text = "\n".join(extracted_lines).strip()
    avg_confidence = round(total_conf / conf_count, 2) if conf_count > 0 else 0.0
    structured = extract_structured_certificate_fields(raw_text)

    return {
        "raw_text": raw_text,
        "confidence": avg_confidence,
        "line_count": len(extracted_lines),
        "structured_data": structured,
    }
