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
