import pytest
from services.resume_parser import ResumeParser

SAMPLE_RESUME = """
Alex Johnson
alex.johnson@example.com | (555) 123-4567 | San Francisco, CA
Senior Full Stack Engineer

Professional Summary
Results-driven software engineer with 5 years of experience developing scalable web applications using Python, Flask, and React.

Technical Skills
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: Flask, Django, React, FastAPI, Node.js
Cloud & Databases: PostgreSQL, MongoDB, Docker, AWS, Git, Redis

Work Experience
Senior Software Engineer - Tech Solutions Inc. (2021 - Present)
* Architected and deployed microservices handling 50k+ daily requests using Python and Flask.
* Reduced API latency by 35% through Redis caching and PostgreSQL query optimization.
* Led a cross-functional team of 5 engineers using Agile methodologies.

Full Stack Developer - Web Innovations (2019 - 2021)
* Developed responsive user interfaces in React and TypeScript.
* Built RESTful APIs backed by PostgreSQL databases.

Projects
Job Search Agent (2023)
* Engineered automated job search aggregator in Python with ATS scoring.

Education
Bachelor of Science in Computer Science - University of California, Berkeley (2015 - 2019)
"""

def test_resume_parser_contact_info():
    parser = ResumeParser()
    data = parser.parse(SAMPLE_RESUME)
    
    assert data["name"] == "Alex Johnson"
    assert data["email"] == "alex.johnson@example.com"
    assert "555" in data["phone"]
    assert "San Francisco" in data["location"]

def test_resume_parser_skills():
    parser = ResumeParser()
    data = parser.parse(SAMPLE_RESUME)
    
    skills = data["skills"]
    assert "Python" in skills
    assert "Flask" in skills
    assert "React" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "AWS" in skills

def test_resume_parser_experience_years():
    parser = ResumeParser()
    data = parser.parse(SAMPLE_RESUME)
    
    assert data["experience_years"] >= 4.0

def test_resume_parser_education():
    parser = ResumeParser()
    data = parser.parse(SAMPLE_RESUME)
    
    edu = data["education"]
    assert len(edu) > 0
    assert any("Bachelor" in e.get("degree", "") for e in edu)

def test_file_validation_rejections():
    import io
    from utils.file_validation import validate_uploaded_file
    from werkzeug.datastructures import FileStorage

    # 1. Invalid extension
    fs_txt = FileStorage(stream=io.BytesIO(b"Hello world"), filename="test.txt")
    valid, err, _ = validate_uploaded_file(fs_txt)
    assert not valid
    assert "Unsupported file type" in err

    # 2. Fake PDF (wrong magic bytes)
    fs_fake_pdf = FileStorage(stream=io.BytesIO(b"not a real pdf"), filename="test.pdf")
    valid, err, _ = validate_uploaded_file(fs_fake_pdf)
    assert not valid
    assert "Invalid PDF" in err

    # 3. Empty file
    fs_empty = FileStorage(stream=io.BytesIO(b""), filename="empty.pdf")
    valid, err, _ = validate_uploaded_file(fs_empty)
    assert not valid
    assert "empty" in err

    # 4. Oversized file
    fs_oversized = FileStorage(stream=io.BytesIO(b"x" * 200), filename="large.pdf")
    valid, err, _ = validate_uploaded_file(fs_oversized, max_size=100)
    assert not valid
    assert "exceeds" in err

    # 5. Valid PDF
    fs_valid_pdf = FileStorage(stream=io.BytesIO(b"%PDF-1.4 sample content here"), filename="valid.pdf")
    valid, err, ext = validate_uploaded_file(fs_valid_pdf)
    assert valid
    assert ext == "pdf"

def test_skill_extractor_canonicalization_and_categories():
    from services.skill_extractor import skill_extractor
    text = (
        "Experienced engineer skilled in postgres, react.js, rest apis, "
        "k8s, sklearn, and golang. Also worked with AWS, Docker, and PyTorch."
    )
    skills = skill_extractor.extract_skills(text)
    assert "PostgreSQL" in skills
    assert "React" in skills
    assert "REST APIs" in skills
    assert "Kubernetes" in skills
    assert "Scikit-Learn" in skills
    assert "Go" in skills
    assert "AWS" in skills
    assert "Docker" in skills
    assert "PyTorch" in skills

    categories = skill_extractor.extract_skills_by_category(text)
    assert "Languages" in categories
    assert "Go" in categories["Languages"]
    assert "Frontend & UI Libraries" in categories
    assert "React" in categories["Frontend & UI Libraries"]
    assert "Cloud Platforms & Serverless" in categories
    assert "AWS" in categories["Cloud Platforms & Serverless"]
    assert "DevOps & Containerization" in categories
    assert "Kubernetes" in categories["DevOps & Containerization"]
    assert "Relational & SQL Databases" in categories
    assert "PostgreSQL" in categories["Relational & SQL Databases"]
    assert "Data Science & Machine Learning" in categories
    assert "Scikit-Learn" in categories["Data Science & Machine Learning"]

def test_pdf_two_column_and_link_extraction(tmp_path):
    import pymupdf
    from utils.text_extraction import extract_text_from_pdf

    pdf_path = str(tmp_path / "two_column_resume.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)

    # Column 0 (left column: x0=50, mid_x=300)
    page.insert_text((50, 100), "Left Col 1: Contact & Summary")
    page.insert_text((50, 200), "Left Col 2: Skills - Python, SQL")

    # Column 1 (right column: x0=350, mid_x=300)
    page.insert_text((350, 100), "Right Col 1: Work Experience")
    page.insert_text((350, 200), "Right Col 2: Education & Projects")

    # Add embedded link
    rect = pymupdf.Rect(50, 300, 200, 320)
    page.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": "https://linkedin.com/in/alexjohnson"})

    doc.save(pdf_path)
    doc.close()

    extracted, err = extract_text_from_pdf(pdf_path)
    assert err is None
    assert "Left Col 1" in extracted
    assert "Right Col 1" in extracted
    assert "https://linkedin.com/in/alexjohnson" in extracted

def test_scanned_pdf_check(tmp_path):
    import pymupdf
    from utils.text_extraction import extract_text_from_pdf

    pdf_path = str(tmp_path / "scanned_or_short.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    # Insert tiny text (< 50 chars)
    page.insert_text((50, 100), "Hello")
    doc.save(pdf_path)
    doc.close()

    extracted, err = extract_text_from_pdf(pdf_path)
    assert extracted == ""
    assert "insufficient extractable text" in err
