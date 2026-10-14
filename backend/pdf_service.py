import io
import os
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

def generate_resume_pdf(
    student_data: Dict[str, Any],
    selected_cert_ids: Optional[List[int]] = None,
    template_name: str = "Modern"
) -> io.BytesIO:
    """Generates an authentic, selectable-text A4 PDF resume using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []
    styles = getSampleStyleSheet()

    # Define color scheme based on template
    primary_color = colors.HexColor("#135f52")  # Career OS emerald
    text_color = colors.HexColor("#14221f")
    subtext_color = colors.HexColor("#4a5d56")
    line_color = colors.HexColor("#dce7e1")

    if template_name == "Minimal":
        primary_color = colors.HexColor("#222222")
    elif template_name == "Technical":
        primary_color = colors.HexColor("#1e3a8a")  # Deep Navy
    elif template_name == "Student":
        primary_color = colors.HexColor("#0f766e")

    # Typography styles
    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=0,
    )

    role_style = ParagraphStyle(
        "ResumeRole",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=subtext_color,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=subtext_color,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceAfter=4,
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=text_color,
    )

    body_text = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=text_color,
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_color,
        leftIndent=14,
        firstLineIndent=-10,
    )

    full_name = student_data.get("name") or "Career OS Scholar"
    target_role = student_data.get("targetRole") or "Software Engineer"
    email = student_data.get("email") or ""
    phone = student_data.get("phone") or ""
    college_name = student_data.get("collegeName") or ""
    github = student_data.get("github") or {}
    linkedin = student_data.get("linkedin") or {}

    contact_parts = []
    if email:
        contact_parts.append(email)
    if phone:
        contact_parts.append(phone)
    if github.get("username"):
        contact_parts.append(f"github.com/{github.get('username')}")
    if linkedin.get("username"):
        contact_parts.append(f"linkedin.com/in/{linkedin.get('username')}")
    if college_name:
        contact_parts.append(college_name)

    contact_str = " &nbsp;|&nbsp; ".join(contact_parts)

    # 1. Header
    story.append(Paragraph(full_name, name_style))
    story.append(Paragraph(target_role, role_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(contact_str, contact_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=line_color, spaceAfter=12))

    # 2. Professional Summary
    summary = student_data.get("summary") or student_data.get("bio")
    if summary:
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
        story.append(Paragraph(summary, body_text))
        story.append(Spacer(1, 10))

    # 3. Education
    education = student_data.get("education", [])
    if education:
        story.append(Paragraph("EDUCATION", section_heading))
        for edu in education:
            inst = edu.get("institution", "")
            deg = edu.get("degree", "")
            field = edu.get("field_of_study", "")
            years = f"{edu.get('start_year', '')} - {edu.get('end_year', '')}".strip(" -")
            cgpa = edu.get("grade_cgpa", "")

            degree_line = f"<b>{deg}</b>" + (f" in {field}" if field else "")
            story.append(Paragraph(f"{degree_line} &nbsp;—&nbsp; {inst} ({years})", body_text))
            if cgpa:
                story.append(Paragraph(f"CGPA / Academic Score: <b>{cgpa}</b>", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # 4. Verified Skills
    skills = student_data.get("skills", [])
    if skills:
        story.append(Paragraph("SKILLS & COMPETENCIES", section_heading))
        if isinstance(skills, list):
            skill_names = [s.get("name") if isinstance(s, dict) else str(s) for s in skills]
            skill_text = ", ".join(skill_names)
            story.append(Paragraph(f"<b>Core Capabilities:</b> {skill_text}", body_text))
        elif isinstance(skills, dict):
            for cat, items in skills.items():
                if items:
                    story.append(Paragraph(f"<b>{cat}:</b> {', '.join(items)}", body_text))
        story.append(Spacer(1, 10))

    # 5. Projects
    projects = student_data.get("projects", [])
    if projects:
        story.append(Paragraph("PROJECTS & REPOSITORIES", section_heading))
        for p in projects[:5]:
            title = p.get("title") or p.get("name", "Project")
            tech = p.get("technologies") or p.get("language", "")
            desc = p.get("description", "")
            url = p.get("project_url") or p.get("html_url", "")

            title_row = f"<b>{title}</b>"
            if tech:
                title_row += f" &nbsp;|&nbsp; <i>{tech}</i>"
            if url:
                title_row += f" &nbsp;[<font color='blue'><a href='{url}'>Code</a></font>]"
            
            story.append(Paragraph(title_row, body_text))
            if desc:
                story.append(Paragraph(f"• {desc}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # 6. Internships & Experience
    experiences = student_data.get("experience", []) + student_data.get("internships", [])
    if experiences:
        story.append(Paragraph("EXPERIENCE & INTERNSHIPS", section_heading))
        for exp in experiences[:4]:
            comp = exp.get("company", "Company")
            role = exp.get("role", "Engineer")
            dur = exp.get("duration") or exp.get("period", "")
            desc = exp.get("description", "")

            story.append(Paragraph(f"<b>{role}</b> &nbsp;—&nbsp; {comp} {f'({dur})' if dur else ''}", body_text))
            if desc:
                story.append(Paragraph(f"• {desc}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # 7. Selected Certifications
    certs = student_data.get("certifications", [])
    if selected_cert_ids:
        certs = [c for c in certs if c.get("id") in selected_cert_ids]

    if certs:
        story.append(Paragraph("VERIFIED CERTIFICATIONS", section_heading))
        for c in certs:
            ctitle = c.get("title", "Certificate")
            issuer = c.get("issuer", "Issuing Body")
            date = c.get("issue_date") or c.get("date", "")
            cid = c.get("credential_id", "")

            cert_str = f"• <b>{ctitle}</b> &nbsp;—&nbsp; {issuer}"
            if date:
                cert_str += f" ({date})"
            if cid:
                cert_str += f" [ID: {cid}]"
            story.append(Paragraph(cert_str, bullet_style))
        story.append(Spacer(1, 8))

    # Build document
    doc.build(story)
    buffer.seek(0)
    return buffer
