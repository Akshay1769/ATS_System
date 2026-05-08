import sys
import utils
import email_service
import streamlit as st
from io import StringIO
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_base_url():
    return os.getenv("BASE_URL", "http://localhost:3000")


sys.stdout = StringIO() 
st.set_page_config(page_title="X Hire", page_icon=":briefcase:", layout="centered")


def get_active_interviews():
    response = (
        supabase.table("interview")
        .select("id,name,objective,url,readable_slug")
        .eq("is_active", True)
        .execute()
    )

    return response.data


def store_candidate(email, ats_score, interview_link):
    existing = (
        supabase.table("candidates")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if existing.data:
        st.warning(f"Email already sent to {email}")
        return False

    supabase.table("candidates").insert({
        "email": email,
        "ats_score": ats_score,
        "shortlisted": True,
        "interview_link": interview_link,
        "email_sent": True
    }).execute()

    return True


def main():
    st.title("X Hire ∙ ATS (Applicant Tracking System)")
    st.markdown("---")

    st.subheader("Job Description and ATS Criteria")
    st.write("Select the job role for ATS filtering.")

    interviews = get_active_interviews()

    interview_options = {
        interview["name"]: interview
        for interview in interviews
    }

    role_names = ["Select a Job Role"] + list(interview_options.keys())

    selected_role = st.selectbox(
        "Select Job Role",
        role_names
    )

    description = ""
    interview_link = ""
    interview_id = ""

    if selected_role != "Select a Job Role":
        selected_interview = interview_options[selected_role]

        description = selected_interview["objective"]

        base_url = get_base_url()

        interview_link = (
            f"{base_url}/call/{selected_interview['readable_slug']}"
            if selected_interview["readable_slug"]
            else selected_interview["url"]
        )

        interview_id = selected_interview["id"]

    st.text_area(
        "Job Description:",
        value=description,
        height=150,
        disabled=True
    )

    min_experience = st.number_input("Minimum Years of Experience:", min_value=0, max_value=50, value=1, step=1)
    max_experience = st.number_input("Maximum Years of Experience:", min_value=0, max_value=50, value=3, step=1)
    ats_criteria = st.number_input("Enter ATS Score Criteria (difficulty level):", min_value=0, max_value=100, value=75, step=1)

    st.markdown("---")
    st.subheader("Upload Resumes")
    st.write("")  

    uploaded_files = st.file_uploader("Upload your resumes (PDF or DOCX)...", type=["pdf", "docx"], accept_multiple_files=True)

    if uploaded_files:
        st.success(f"{len(uploaded_files)} PDF(s) Uploaded Successfully.")

    submit = st.button("Process Resumes")
    st.markdown("---")
    if submit:
        if not description:
            st.error("Please provide a job description before processing resumes.")

        elif not uploaded_files:
            st.error("Please upload at least one resume to proceed.")
        else:
            process_and_email_resumes(
                description,
                ats_criteria,
                uploaded_files,
                min_experience,
                max_experience,
                interview_link,
                selected_role
            )
            
    with st.expander("Show Debug Logs"):
        captured_output = sys.stdout.getvalue()
        st.text_area("Debug Logs", captured_output, height=150)

def process_resumes(description, ats_criteria, uploaded_files, min_experience, max_experience):
    proceed_resumes = []
    for uploaded_file in uploaded_files:
        pdf_content = utils.file_to_text(uploaded_file)
        if not pdf_content:
            st.write(f"Rejected: {uploaded_file.name}")
            continue

        prompt = utils.get_prompt(pdf_content, description, min_experience, max_experience)
        ats_score = utils.get_ats_score(prompt=prompt, file_name=uploaded_file.name)

        if ats_score < int(ats_criteria):
            st.write(f"Rejected: {uploaded_file.name}, ats_score: {ats_score}")
            continue
        st.write(f'Passed: {uploaded_file.name} the ATS percentage criteria with {ats_score}')

        proceed_resumes.append({
            "Name": uploaded_file.name,
            "Score": ats_score,
            "Resume": uploaded_file.name,
            "ResumeFile": uploaded_file
        })

    if len(proceed_resumes) != 0:
        zip_buffer = utils.create_zip_file(proceed_resumes)
        current_date_str = utils.get_day_month_year()
        if zip_buffer: 
            st.download_button(
                label="Download Shortlisted Resumes as ZIP",
                data=zip_buffer,
                file_name=f"shortlisted-resumes-{current_date_str}.zip",
                mime="application/zip"
            )


def process_and_email_resumes(description, ats_criteria, uploaded_files, min_experience, max_experience, interview_link, role_name):
    proceed_resumes = []

    for uploaded_file in uploaded_files:
        pdf_content = utils.file_to_text(uploaded_file)

        if not pdf_content:
            st.write(f"Rejected: {uploaded_file.name}")
            continue

        prompt = utils.get_prompt(
            pdf_content,
            description,
            min_experience,
            max_experience
        )

        ats_score = utils.get_ats_score(
            prompt=prompt,
            file_name=uploaded_file.name
        )

        if ats_score < int(ats_criteria):
            st.write(f"Rejected: {uploaded_file.name}, ats_score: {ats_score}")
            continue

        st.write(
            f'Passed: {uploaded_file.name} the ATS percentage criteria with {ats_score}'
        )

        candidate_details_raw = utils.get_candidate_info(pdf_content)

        if candidate_details_raw == "":
            st.write(
                f"Rejected {uploaded_file.name} with ats_score: {ats_score} because no name/email found"
            )
            continue

        name = utils.extract_info_details_name(candidate_details_raw)
        email = utils.extract_info_details_email(candidate_details_raw)
        phone = utils.extract_info_details_phone(candidate_details_raw)

        if not name or not email:
            st.write(
                f"Rejected {uploaded_file.name} with ats_score: {ats_score} because no name/email found"
            )
            continue

        name = utils.make_text_plain(name)

        proceed_resumes.append({
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Score": ats_score,
            "Resume": uploaded_file.name,
            "ResumeFile": uploaded_file
        })

    if len(proceed_resumes) != 0:
        csv_path = utils.get_csv(proceed_resumes)

        for candidate in proceed_resumes:
            stored = store_candidate(
                candidate["Email"],
                candidate["Score"],
                interview_link
            )

            if stored:
                email_service.send_email_to(
                    to_email=candidate["Email"],
                    subject="Interview Invitation",
                    body_html=email_service.candidate_email_body(
                        candidate["Name"],
                        interview_link,
                        role_name
                    )
                )

        zip_buffer = utils.create_zip_file(proceed_resumes)
        current_date_str = utils.get_day_month_year()

        if zip_buffer:
            st.download_button(
                label="Download Shortlisted Resumes as ZIP",
                data=zip_buffer,
                file_name=f"shortlisted-resumes-{current_date_str}.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
