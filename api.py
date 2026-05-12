import traceback

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from dotenv import load_dotenv
from supabase import create_client

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

# CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://xhiremain.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "resumes"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    description: str = Form(...),
    min_experience: int = Form(0),
    max_experience: int = Form(10),
):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    
    with open(file_path, "rb") as resume_file:

        if file.filename.endswith(".pdf"):
            from utils import pdf_to_text
            resume_text = pdf_to_text(resume_file)

        elif file.filename.endswith(".docx"):
            from utils import docx_to_text
            resume_text = docx_to_text(file_path)

        else:
            resume_text = ""

        prompt = get_prompt(
            resume_text,
            description,
            min_experience,
            max_experience
        )

        score = get_ats_score(prompt, file.filename)

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

    except Exception:
        traceback.print_exc()

    return {
        "filename": file.filename,
        "score": score,
        "shortlisted": shortlisted,
        "candidate_name": name,
        "candidate_email": email,
        "candidate_phone": phone
    }