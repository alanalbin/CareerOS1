import os
import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from database import get_db
import models
from security import get_current_user, require_role
from ocr_service import process_file_with_ocr
from ai_service import analyze_certificate_data

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_MB", "25")) * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "text/plain",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt"}

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    return cleaned[:100]

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("certificate"),
    title: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Securely uploads and processes documents using PaddleOCR."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: PDF, JPG, PNG, WEBP, TXT."
        )

    mime = file.content_type or ""
    if mime and mime.lower() not in ALLOWED_MIME_TYPES and ext != ".txt":
        raise HTTPException(status_code=400, detail=f"Unsupported MIME type: {mime}")

    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
        )

    # Secure random filename
    unique_name = f"{uuid.uuid4().hex}_{sanitize_filename(file.filename)}"
    stored_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    # Save Document record
    doc = models.Document(
        user_id=current_user.id,
        filename=unique_name,
        original_filename=file.filename,
        file_path=stored_path,
        file_size=file_size,
        mime_type=mime or "application/octet-stream",
        category=category,
    )
    db.add(doc)
    db.flush()

    # Run OCR processing
    ocr_result = process_file_with_ocr(file_bytes, file.filename, mime)

    extraction = models.DocumentExtraction(
        document_id=doc.id,
        raw_text=ocr_result["raw_text"],
        structured_data=ocr_result["structured_data"],
        confidence=ocr_result["confidence"],
    )
    db.add(extraction)

    # If student uploaded a certificate, link to certifications table
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if student and category == "certificate":
        extracted = ocr_result["structured_data"]
        cert_name = title or extracted.get("certificateName") or os.path.splitext(file.filename)[0]
        issuer = extracted.get("issuer") or "Accredited Body"

        cert = models.Certification(
            student_id=student.id,
            title=cert_name,
            issuer=issuer,
            issue_date=extracted.get("date"),
            credential_id=extracted.get("certificateId"),
            document_id=doc.id,
            verified=(ocr_result["confidence"] >= 0.85),
        )
        db.add(cert)
        db.flush()

        # Add verification tracking record
        verif = models.CertificateVerification(
            document_id=doc.id,
            status="VERIFIED" if ocr_result["confidence"] >= 0.85 else "PENDING",
            verification_notes=f"PaddleOCR confidence: {int(ocr_result['confidence'] * 100)}%",
            verified_by="PaddleOCR Engine" if ocr_result["confidence"] >= 0.85 else None,
        )
        db.add(verif)

    db.commit()
    db.refresh(doc)

    return {
        "success": True,
        "document": {
            "id": doc.id,
            "filename": doc.original_filename,
            "category": doc.category,
            "fileSize": doc.file_size,
            "createdAt": doc.created_at.isoformat(),
            "confidence": ocr_result["confidence"],
            "structuredFields": ocr_result["structured_data"],
            "extractedTextSnippet": ocr_result["raw_text"][:300] if ocr_result["raw_text"] else "No text extracted",
        }
    }

@router.get("")
def list_documents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists all documents uploaded by the current user."""
    docs = db.query(models.Document).filter(models.Document.user_id == current_user.id).order_by(models.Document.created_at.desc()).all()

    items = []
    for d in docs:
        extraction = db.query(models.DocumentExtraction).filter(models.DocumentExtraction.document_id == d.id).first()
        verif = db.query(models.CertificateVerification).filter(models.CertificateVerification.document_id == d.id).first()

        items.append({
            "id": d.id,
            "filename": d.original_filename,
            "category": d.category,
            "fileSize": d.file_size,
            "mimeType": d.mime_type,
            "createdAt": d.created_at.isoformat() if d.created_at else None,
            "ocrStatus": "Completed" if extraction else "Pending",
            "confidence": extraction.confidence if extraction else 0.0,
            "verificationStatus": verif.status if verif else ("VERIFIED" if (extraction and extraction.confidence >= 0.85) else "PENDING"),
            "structuredData": extraction.structured_data if extraction else None,
        })

    return {"documents": items}

@router.get("/{doc_id}")
def get_document_file(doc_id: int, request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Serves the actual stored certificate/document securely with access checks."""
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Authorization check
    if doc.user_id != current_user.id:
        # Check if caller is recruiter or college with permission
        if current_user.role == "RECRUITER":
            student = db.query(models.Student).filter(models.Student.user_id == doc.user_id).first()
            if student:
                vis = db.query(models.StudentVisibilitySetting).filter(models.StudentVisibilitySetting.student_id == student.id).first()
                if vis and not vis.certificates_visible:
                    raise HTTPException(status_code=403, detail="Student has not granted permission to view this document.")
        elif current_user.role not in ["COLLEGE", "COLLEGE_ADMIN"]:
            raise HTTPException(status_code=403, detail="Access denied to this document.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on storage.")

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )

@router.delete("/{doc_id}")
def delete_document(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes an uploaded document and removes it from disk and database."""
    doc = db.query(models.Document).filter(models.Document.id == doc_id, models.Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or unauthorized.")

    # Delete linked certifications
    db.query(models.Certification).filter(models.Certification.document_id == doc.id).delete()

    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()

    return {"success": True, "message": "Document deleted successfully."}

@router.post("/{doc_id}/ocr")
def rerun_ocr(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-runs OCR analysis on an uploaded document."""
    doc = db.query(models.Document).filter(models.Document.id == doc_id, models.Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file missing on disk.")

    with open(doc.file_path, "rb") as f:
        file_bytes = f.read()

    ocr_result = process_file_with_ocr(file_bytes, doc.original_filename, doc.mime_type)

    extraction = db.query(models.DocumentExtraction).filter(models.DocumentExtraction.document_id == doc.id).first()
    if extraction:
        extraction.raw_text = ocr_result["raw_text"]
        extraction.structured_data = ocr_result["structured_data"]
        extraction.confidence = ocr_result["confidence"]
    else:
        extraction = models.DocumentExtraction(
            document_id=doc.id,
            raw_text=ocr_result["raw_text"],
            structured_data=ocr_result["structured_data"],
            confidence=ocr_result["confidence"],
        )
        db.add(extraction)

    db.commit()
    return {"success": True, "ocr": ocr_result}

@router.post("/{doc_id}/analyze")
def analyze_document_ai(doc_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sends structured certificate extraction to Qwen3 AI for deep analysis."""
    doc = db.query(models.Document).filter(models.Document.id == doc_id, models.Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    extraction = db.query(models.DocumentExtraction).filter(models.DocumentExtraction.document_id == doc.id).first()
    if not extraction or not extraction.raw_text:
        raise HTTPException(status_code=400, detail="Please perform OCR on this document first.")

    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    cert = db.query(models.Certification).filter(models.Certification.document_id == doc.id).first()
    cert_title = cert.title if cert else doc.original_filename
    issuer = cert.issuer if cert else "Issuing Organization"

    ai_result = analyze_certificate_data(
        cert_title=cert_title,
        issuer=issuer,
        ocr_text=extraction.raw_text,
        structured_fields=extraction.structured_data or {},
    )

    if student and ai_result.get("success"):
        record = models.AIAnalysis(
            student_id=student.id,
            analysis_type="certificate",
            content={"documentId": doc.id, "analysis": ai_result.get("data")},
            model_used="qwen3.8-flash",
        )
        db.add(record)
        db.commit()

    return ai_result
