import mimetypes
import os
import re
import smtplib
import ssl
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)

SMTP_HOST = "smtp.gmail.com"
SMTP_TIMEOUT = 30

DEFAULT_SUBJECT = "Test Email from Python"
DEFAULT_CONTACT_FILE = "contacts.csv"
DEFAULT_TEMPLATE_FILE = "email_template.txt"
DEFAULT_LOG_FILE = "email_logs.csv"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean(value):
    return (value or "").strip().strip('"').strip("'").strip()


def get_email_credentials():
    sender_email = _clean(os.getenv("EMAIL_SENDER") or os.getenv("GMAIL_SENDER"))
    app_password = _clean(os.getenv("EMAIL_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")).replace(" ", "")

    if not sender_email or not app_password:
        raise ValueError(
            "Missing Gmail credentials. Put your real values in the .env file: "
            "EMAIL_SENDER and EMAIL_PASSWORD."
        )

    if len(app_password) != 16:
        print(
            "WARNING: Gmail App Password should be 16 characters. "
            "Use a real App Password from Google, not your normal Gmail password."
        )

    return sender_email, app_password


def read_contacts(contact_file):
    contact_path = Path(contact_file)
    if not contact_path.exists():
        raise FileNotFoundError(f"Contacts file not found: {contact_path}")

    df = pd.read_csv(contact_path, dtype=str).fillna("")
    df.columns = [str(col).strip().lower() for col in df.columns]

    required = {"name", "email"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Contacts CSV must contain name and email columns. "
            f"Missing: {sorted(missing)}"
        )

    return df


def load_email_template(template_file):
    template_path = Path(template_file)
    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _close_quietly(smtp):
    if smtp is None:
        return
    try:
        smtp.quit()
    except Exception:
        try:
            smtp.close()
        except Exception:
            pass


def connect_smtp(sender_email, app_password, debug=False):
    context = ssl.create_default_context()
    errors = []

    for mode in ("SSL 465", "STARTTLS 587"):
        smtp = None
        try:
            if mode == "SSL 465":
                smtp = smtplib.SMTP_SSL(SMTP_HOST, 465, context=context, timeout=SMTP_TIMEOUT)
                smtp.set_debuglevel(1 if debug else 0)
            else:
                smtp = smtplib.SMTP(SMTP_HOST, 587, timeout=SMTP_TIMEOUT)
                smtp.set_debuglevel(1 if debug else 0)
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()

            smtp.login(sender_email, app_password)
            print(f"Connected to Gmail using {mode}")
            return smtp

        except smtplib.SMTPAuthenticationError as error:
            _close_quietly(smtp)
            raise ValueError(
                "Gmail login rejected. Check that EMAIL_SENDER is your real Gmail "
                "address and EMAIL_PASSWORD is a valid 16-character App Password."
            ) from error

        except (smtplib.SMTPException, OSError) as error:
            _close_quietly(smtp)
            errors.append(f"{mode}: {type(error).__name__}: {error}")
            print(f"{mode} failed -> {type(error).__name__}: {error}")

    raise ConnectionError(
        "Gmail connection failed. Turn off antivirus email scanning or try a different network.\n"
        + "\n".join(errors)
    )


def build_message(sender_email, receiver_email, subject, body, attachment_data, attachment_name, maintype, subtype):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.set_content(body)

    if attachment_data:
        message.add_attachment(
            attachment_data,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_name,
        )
    return message


def send_emails(
    subject=DEFAULT_SUBJECT,
    contact_file=DEFAULT_CONTACT_FILE,
    attachment_path=None,
    template_file=DEFAULT_TEMPLATE_FILE,
    log_file=DEFAULT_LOG_FILE,
):
    sender_email, app_password = get_email_credentials()
    df = read_contacts(contact_file)
    template = load_email_template(template_file)
    debug = os.getenv("SMTP_DEBUG", "0").strip() == "1"

    attachment_data = None
    attachment_name = None
    maintype, subtype = "application", "octet-stream"

    if attachment_path:
        attachment = Path(attachment_path)
        if not attachment.exists():
            raise FileNotFoundError(f"Attachment not found: {attachment}")
        attachment_data = attachment.read_bytes()
        attachment_name = attachment.name
        guessed_type, _ = mimetypes.guess_type(attachment.name)
        if guessed_type:
            maintype, subtype = guessed_type.split("/", 1)

    logs = []
    log_path = Path(log_file)

    def save_logs():
        if not logs:
            return
        file_has_data = log_path.exists() and log_path.stat().st_size > 0
        pd.DataFrame(logs).to_csv(
            log_path,
            mode="a",
            header=not file_has_data,
            index=False,
        )

    smtp = None
    try:
        smtp = connect_smtp(sender_email, app_password, debug=debug)

        for _, row in df.iterrows():
            receiver_email = str(row["email"]).strip()
            name = str(row["name"]).strip() or "there"
            status = "Sent"

            try:
                if not EMAIL_REGEX.match(receiver_email):
                    raise ValueError(f"Invalid email address: {receiver_email}")

                body = template.replace("{name}", name)
                message = build_message(
                    sender_email,
                    receiver_email,
                    subject,
                    body,
                    attachment_data,
                    attachment_name,
                    maintype,
                    subtype,
                )

                try:
                    smtp.send_message(message)
                except smtplib.SMTPServerDisconnected:
                    print("Connection dropped, reconnecting...")
                    _close_quietly(smtp)
                    smtp = connect_smtp(sender_email, app_password, debug=debug)
                    smtp.send_message(message)

                print(f"Email sent successfully to {name} ({receiver_email})")

            except Exception as error:
                status = "Failed"
                print(f"Failed to send email to {name} ({receiver_email}): {error}")

            logs.append(
                {
                    "name": name,
                    "email": receiver_email,
                    "status": status,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            time.sleep(2)
    finally:
        _close_quietly(smtp)
        save_logs()

    print("\n==============================")
    print("Email process completed!")
    print("Email logs saved successfully!")
    print("==============================")

    return pd.DataFrame(logs)


if __name__ == "__main__":
    send_emails()
