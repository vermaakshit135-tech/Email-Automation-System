# Email Automation System

A Python desktop and web-based email automation project that reads recipients from a CSV file, personalizes a message template, and sends emails through Gmail SMTP.

## Features

- Send emails to multiple people from a CSV file
- Personalized templates using `{name}` placeholders
- Optional PDF or file attachment support
- GUI version with Tkinter
- Web version with Streamlit
- Gmail SMTP connection with retry handling
- Email logs saved to CSV
- Credentials kept in `.env`

## Tech Stack

- Python 3
- Pandas
- Tkinter
- Streamlit
- Gmail SMTP
- python-dotenv

## Project Structure

```text
Email-Automation-System/
├── main.py
├── email_gui.py
├── app.py
├── test_csv.py
├── contacts.csv
├── email_template.txt
├── email_logs.csv
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── attachments/
└── .venv/
```

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
```

2. Activate it:

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:

```env
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
```

> Use a real Gmail App Password. Do not use your normal Gmail password.

## Run the desktop app

```bash
python email_gui.py
```

## Run the Streamlit app

```bash
streamlit run app.py
```

## Run the contact validator

```bash
python test_csv.py
```

## CSV format

```csv
name,email
John Doe,john@example.com
Jane Smith,jane@example.com
```

## Template format

```text
Hello {name},

Thank you for your time.

Best regards,
Your Team
```

## Notes

- Gmail requires 2-Step Verification and an App Password for SMTP scripts.
- Keep `.env` private and never commit it to Git.
- Log files are stored in `email_logs.csv`.

## License

This project is for learning and personal use.
