import os
import re
import sys
import time
import random
import string
import tempfile
from unittest import result
import fitz
import traceback

import zipfile
import pdfplumber
import unicodedata
import pandas as pd
from docx import Document
from datetime import datetime
from io import BytesIO, StringIO
from groq import Groq

# original_stdout = sys.stdout
# sys.stdout = StringIO()

def extract_info_details_name(candidate_details_raw):
    name_match = re.search(r"(?i)name[:\s]*([A-Za-z\s]+)", candidate_details_raw)
    return name_match.group(1).strip() if name_match else None

def extract_info_details_email(candidate_details_raw):
    email_match = re.search(r"(?i)email[:\s]*([\w\.-]+@[\w\.-]+)", candidate_details_raw)
    return email_match.group(1).strip() if email_match else None

def extract_info_details_phone(candidate_details_raw):
    phone_match = re.search(r"(?i)phone[:\s]*([\(\+\)\d\s-]+)", candidate_details_raw)
    return phone_match.group(1).strip() if phone_match else None

def get_model():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_prompt(text, description, min_experience, max_experience):
    text = make_text_plain(text)
    return f"""
You are an ATS (Applicant Tracking System).

STRICT OUTPUT RULE:
- Return ONLY a number between 0 and 100
- No explanation, no text, no symbols

SCORING LOGIC (IMPORTANT):
- Match candidate's skills with job description (highest weight)
- Match experience relevance to job role
- Match projects and work experience
- Match education relevance

GENERAL RULES:
- Strong alignment between resume and job description → 80–100
- Partial alignment → 40–70
- Weak or unrelated → 0–30

- If candidate lacks key skills required in job description → low score
- If resume is irrelevant to job description → return 0
- If resume text is corrupted or unreadable → return 0
- If candidate is overqualified beyond required experience → slightly reduce score

Job Description:
{description}

Resume:
{text}

FINAL OUTPUT:
"""


def groq_call(prompt):
    try:
        client = get_model()

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    except Exception:
        traceback.print_exc()
        return ""



def get_candidate_info_prompt(text):
    return f"""
    Extract the candidate's name, email, and phone number from the following resume text.
    Anything happens the format should strictly be like this the format "Name: ..., Email: ..., Phone: ...

    Resume Text:
    {text}
    """

def make_text_plain(text):
    try:
        text = unicodedata.normalize('NFKD', text)
        text = text.lower().title()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        if text:
            return text.strip()
        return text
    except Exception:
        traceback.print_exc()
        return ""

def pdf_to_text(file):
    text = ""
    try:
        import fitz

        file.seek(0)
        file_bytes = file.read()

        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text

        # fallback if still empty
        if not text.strip():
            print("Fallback to pdfplumber...")
            import pdfplumber
            file.seek(0)
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

        return text

    except Exception:
        traceback.print_exc()
        return text
    
def file_to_text(file):
    pdf_content = None
    if file.name.endswith(".pdf"):
        pdf_content = pdf_to_text(file)
    elif file.name.endswith(".docx"):
        pdf_content = docx_to_text(file)
    return pdf_content

def docx_to_text(docx_file):
    text = ''
    try:
        doc = Document(docx_file)

        for para in doc.paragraphs:
            text += para.text + '\n'

        return text

    except Exception:
        traceback.print_exc()
        return text

def get_candidate_info(resume):
    try:
        prompt = get_candidate_info_prompt(resume)
        response = groq_call(prompt)
        return response if response else ""
    except Exception:
        traceback.print_exc()
        return ""

def get_ats_score_deprecated(prompt):
    try:
        response = get_model().generate_content(prompt)
        return int(response.text.strip())
    except Exception:
        traceback.print_exc()
        return 0
    
def rate_limit(delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(delay=1)
def get_ats_score(prompt, file_name, retries=10, delay=5):
    print(f"Processing {file_name}")
    if not prompt or len(prompt.strip()) < 50:
        return 0
    attempt = 0

    while attempt < retries:
        try:
            result = groq_call(prompt)

            if not result:
                print("Empty AI response")
                return 0

            numbers = re.findall(r"\d+", str(result))

            if numbers:
                score = int(numbers[0])

                if score > 100:
                    score = 100

                return score

            print("Invalid AI response:", result)
            return 0

        except Exception:
            traceback.print_exc()
            time.sleep(delay)
            attempt += 1

    print(f"Exceeded maximum retries for {file_name}. Returning 0.")
    return 0

def get_day_month_year():
    return datetime.now().strftime("%d-%m-%Y")

def create_zip_file(resumes):
    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for resume in resumes:
                resume_file = resume["ResumeFile"]
                resume_file.seek(0)  
                zip_file.writestr(resume["Resume"], resume_file.read())
        zip_buffer.seek(0)
        return zip_buffer
    except Exception:
        traceback.print_exc()
        return None

def get_csv(results):
    csv_path = ""
    try:
        df = pd.DataFrame(results)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='') as tmp_file:
            df.to_csv(tmp_file.name, index=False)
            csv_path = tmp_file.name
        return csv_path
    except Exception:
        traceback.print_exc()
        return csv_path

def generate_random_string(length=16):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def chatgpt_model(prompt, model="gpt-3.5-turbo"):
    return groq_call(prompt)
