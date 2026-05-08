from fastapi import FastAPI, UploadFile, File
import shutil
import os
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

from utils import (
    file_to_text,
    get_prompt,
    get_ats_score,
    get_candidate_info,
    extract_info_details_name,
    extract_info_details_email,
    extract_info_details_phone,
)

app = FastAPI()

UPLOAD_FOLDER = "resumes"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

JOB_DESCRIPTION = """
Python Developer with FastAPI, React, SQL, APIs, and AI integration experience.
"""

@app.post("/analyze")
async def analyze_resume(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # reopen file for parsing
    with open(file_path, "rb") as resume_file:

        if file.filename.endswith(".pdf"):
            from utils import pdf_to_text
            resume_text = pdf_to_text(resume_file)

        elif file.filename.endswith(".docx"):
            from utils import docx_to_text
            resume_text = docx_to_text(file_path)

        else:
            resume_text = ""

        print("========== RESUME TEXT ==========")
        print(resume_text[:2000])
        print("================================")

        # Build ATS prompt
        prompt = get_prompt(
            resume_text,
            JOB_DESCRIPTION,
            0,
            10
        )

        # Get ATS score
        score = get_ats_score(prompt, file.filename)

        # Extract candidate details
        candidate_info = get_candidate_info(resume_text)

        name = extract_info_details_name(candidate_info)
        email = extract_info_details_email(candidate_info)
        phone = extract_info_details_phone(candidate_info)

    shortlisted = score >= 70



    try:
        supabase.table("candidates").upsert({
            "email": email,
            "ats_score": score,
            "shortlisted": shortlisted,
            "email_sent": False
        }).execute()

    except Exception as e:
        print("Supabase insert error:", e)

    return {
        "filename": file.filename,
        "score": score,
        "shortlisted": shortlisted,
        "candidate_name": name,
        "candidate_email": email,
        "candidate_phone": phone
    }