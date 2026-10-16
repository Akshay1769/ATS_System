
# ATS System


## Project Structure

```
project/
│
├── main.py               # Core application logic
├── utils.py              # Utility functions for processing resumes and files
├── email_service.py      # Email handling for notifications
├── .env                  # Environment variables (API keys, email config)
└── README.md             # Project documentation
```

---

## Dependencies
Install all dependencies using:

```bash
pip install -r requirements.txt
```

---

## Configuration

1. Create a `.env` file with the following variables:
   ```
   GMAIL_SENDER=your_authorized_gmail_address
   GMAIL_CLIENT_ID=your_oauth_client_id
   GMAIL_CLIENT_SECRET=your_oauth_client_secret
   GMAIL_REFRESH_TOKEN=your_oauth_refresh_token
   
   GEMINI_API_KEY=your_key
   OPENAI_API_KEY=your_key
   
   AWS_SES_FROM_EMAIL_ID=your_aws_ses_from_email
   ```
   Configure these Gmail OAuth values as environment variables in Render.

## Run the Application

Start the application using Streamlit:

```bash
streamlit run main.py
```

open in your browser at `http://localhost:8501`.
