import io
import os
import re
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import db
from main import send_emails

st.set_page_config(page_title="Mailroom", page_icon="✉️", layout="wide")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TEMPLATE_FILE = Path("email_template.txt")

if "auth_view" not in st.session_state:
    st.session_state.auth_view = "login"


@st.cache_resource
def setup_database():
    db.init_db()
    return True


def show(view):
    st.session_state.auth_view = view


# ---------------- sign up / log in ----------------
def login_form(flash):
    st.subheader("Log in")
    if flash:
        st.success(flash)
    with st.form("login_form", border=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        go = st.form_submit_button("Log in", type="primary")
    if go:
        user = db.authenticate(username.strip(), password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Username or password is incorrect. Check both and try again.")
    st.divider()
    st.caption("New here?")
    st.button("Create an account", on_click=show, args=("signup",))


def signup_form():
    st.subheader("Create account")
    with st.form("signup_form", border=False):
        username = st.text_input("Username")
        email = st.text_input("Email", placeholder="name@company.com")
        password = st.text_input("Password", type="password", help="At least 8 characters")
        confirm = st.text_input("Confirm password", type="password")
        go = st.form_submit_button("Create account", type="primary")
    if go:
        if not (username and email and password):
            st.error("Fill in every field to continue.")
        elif not EMAIL_RE.match(email.strip()):
            st.error("Enter an email address like name@company.com.")
        elif len(password) < 8:
            st.error("Use a password with at least 8 characters.")
        elif password != confirm:
            st.error("The two passwords don't match.")
        else:
            ok, message = db.create_user(username.strip(), email.strip(), password)
            if ok:
                st.session_state.flash = "Account created. Log in to continue."
                st.session_state.auth_view = "login"
                st.rerun()
            else:
                st.error(message)
    st.divider()
    st.button("Back to log in", on_click=show, args=("login",))


def auth_page():
    _, centre, _ = st.columns([1, 1.6, 1])
    with centre:
        st.title("✉️ Mailroom")
        st.caption("Send emails to a contact list and keep a history of every send.")
        flash = st.session_state.pop("flash", None)
        with st.container(border=True):
            if st.session_state.auth_view == "login":
                login_form(flash)
            else:
                signup_form()


# ---------------- send emails ----------------
def read_contacts_upload(data):
    df = pd.read_csv(io.BytesIO(data), dtype=str).fillna("")
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = {"name", "email"} - set(df.columns)
    if missing:
        raise ValueError(f"Your CSV needs name and email columns. Missing: {sorted(missing)}")
    return df


def send_page(user):
    st.header("Send emails")
    st.caption("Upload a contacts file, write your message, and send it to everyone on the list.")

    default_body = (
        TEMPLATE_FILE.read_text(encoding="utf-8") if TEMPLATE_FILE.exists() else "Hello {name},\n\n"
    )

    with st.container(border=True):
        subject = st.text_input("Subject")
        contacts_file = st.file_uploader("Contacts file (CSV with name and email columns)", type="csv")
        body = st.text_area("Message", value=default_body, height=220,
                            help="Write {name} where each person's name should appear.")
        attachment = st.file_uploader("Attachment (optional)")

        contacts = None
        if contacts_file:
            try:
                contacts = read_contacts_upload(contacts_file.getvalue())
                st.caption(f"{len(contacts)} contacts found. First rows:")
                st.dataframe(contacts.head(5), hide_index=True)
            except Exception as e:
                st.error(f"Couldn't read that file: {e}")

        go = st.button("📨 Send emails", type="primary")

    if not go:
        return
    if not subject.strip():
        st.error("Add a subject before sending.")
        return
    if contacts is None or contacts.empty:
        st.error("Upload a contacts CSV that has at least one row.")
        return
    if not body.strip():
        st.error("Write a message before sending.")
        return

    total = len(contacts)
    temp_files = []
    campaign_id = db.create_campaign(user["id"], subject.strip())
    bar = st.progress(0.0, text="Connecting to Gmail...")
    results = []

    def on_result(entry):
        db.log_email(campaign_id, user["id"], entry["name"], entry["email"],
                     entry["status"], entry["error"])
        results.append(entry)
        bar.progress(len(results) / total, text=f"{len(results)} of {total} processed")

    try:
        csv_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        csv_tmp.write(contacts_file.getvalue())
        csv_tmp.close()
        temp_files.append(csv_tmp.name)

        attachment_path = None
        if attachment:
            att_dir = tempfile.mkdtemp()
            attachment_path = os.path.join(att_dir, attachment.name)
            Path(attachment_path).write_bytes(attachment.getvalue())
            temp_files.append(attachment_path)

        send_emails(
            subject=subject.strip(),
            contact_file=csv_tmp.name,
            attachment_path=attachment_path,
            template_text=body,
            on_result=on_result,
        )
    except Exception as e:
        st.error(f"Sending stopped: {e}")
    finally:
        for path in temp_files:
            try:
                os.remove(path)
            except OSError:
                pass
        db.delete_campaign_if_empty(campaign_id)

    if results:
        sent = sum(1 for r in results if r["status"] == "Sent")
        bar.empty()
        st.success(f"Done. {sent} sent, {len(results) - sent} failed. See History for the full list.")


# ---------------- history ----------------
def history_page(user):
    st.header("History")
    st.caption("Every send from your account, newest first.")

    campaigns = db.get_campaigns(user["id"])
    if not campaigns:
        st.info("No emails sent yet. Open Send emails in the menu to send your first batch.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Emails processed", sum(c["total"] for c in campaigns), border=True)
    c2.metric("Sent", sum(c["sent"] for c in campaigns), border=True)
    c3.metric("Failed", sum(c["failed"] for c in campaigns), border=True)

    df = pd.DataFrame(
        {
            "Date": [c["created_at"] for c in campaigns],
            "Subject": [c["subject"] for c in campaigns],
            "Contacts": [c["total"] for c in campaigns],
            "Sent": [c["sent"] for c in campaigns],
            "Failed": [c["failed"] for c in campaigns],
        }
    )
    st.dataframe(
        df,
        hide_index=True,
        column_config={"Date": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm")},
    )

    st.subheader("Recipients")
    labels = {
        c["id"]: f"{c['created_at']:%d %b %Y, %H:%M}  ·  {c['subject']}" for c in campaigns
    }
    chosen = st.selectbox("Choose a send", list(labels), format_func=labels.get)
    logs = db.get_campaign_logs(chosen, user["id"])
    st.dataframe(
        pd.DataFrame(
            {
                "Name": [r["contact_name"] for r in logs],
                "Email": [r["contact_email"] for r in logs],
                "Status": ["🟢 Sent" if r["status"] == "Sent" else "🔴 Failed" for r in logs],
                "Error": [r["error_message"] or "" for r in logs],
                "Time": [r["sent_at"] for r in logs],
            }
        ),
        hide_index=True,
        column_config={"Time": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm:ss")},
    )


# ---------------- app shell ----------------
def main_app():
    user = st.session_state.user
    with st.sidebar:
        st.title("✉️ Mailroom")
        page = st.radio("Menu", ["📨 Send emails", "🗂️ History"], label_visibility="collapsed")
        st.divider()
        st.write(f"**{user['username']}**")
        st.caption(user["email"])
        if st.button("Log out"):
            del st.session_state.user
            st.rerun()

    if page.endswith("Send emails"):
        send_page(user)
    else:
        history_page(user)


setup_database()
if "user" not in st.session_state:
    auth_page()
else:
    main_app()