import contextlib
import html
import importlib.util
import io
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

LOG_FILE = "email_logs.csv"

# ====================================================================
# Template library
# Placeholders in {curly_braces} are filled from the "Details" form.
# {name} is special: it is personalised per contact when sending.
# ====================================================================
TEMPLATES = {
    "Invitation": {
        "icon": "🎉",
        "description": "Invite contacts to an event, party, webinar or launch.",
        "subject": "You're invited: {event_name}",
        "fields": [
            ("event_name", "Event name", "Annual Tech Meetup"),
            ("date", "Date", "15 November 2026"),
            ("time", "Time", "6:00 PM IST"),
            ("venue", "Venue / link", "Hotel Grand, Lucknow"),
            ("rsvp_date", "RSVP by", "10 November 2026"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Dear {name},\n\n"
            "I am delighted to invite you to {event_name}.\n\n"
            "Date: {date}\n"
            "Time: {time}\n"
            "Venue: {venue}\n\n"
            "It would be a pleasure to have you with us. Kindly confirm your "
            "attendance by {rsvp_date}.\n\n"
            "Warm regards,\n{sender_name}"
        ),
    },
    "Meeting Request": {
        "icon": "📅",
        "description": "Request a call or meeting with a clear agenda.",
        "subject": "Meeting request: {topic}",
        "fields": [
            ("topic", "Topic", "Project discussion"),
            ("date", "Proposed date", "20 October 2026"),
            ("time", "Proposed time", "11:00 AM IST"),
            ("duration", "Duration", "30 minutes"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Hi {name},\n\n"
            "I would like to schedule a meeting to discuss {topic}.\n\n"
            "Proposed date: {date}\n"
            "Proposed time: {time}\n"
            "Duration: {duration}\n\n"
            "Please let me know if this works for you, or suggest a time "
            "that suits you better.\n\n"
            "Best regards,\n{sender_name}"
        ),
    },
    "Follow-up": {
        "icon": "🔁",
        "description": "Politely follow up on a previous email or conversation.",
        "subject": "Following up: {topic}",
        "fields": [
            ("topic", "Regarding", "our previous conversation"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Hi {name},\n\n"
            "I hope you are doing well. I am following up regarding {topic}.\n\n"
            "I would really appreciate your thoughts when you get a moment. "
            "Please let me know if you need any additional information from my side.\n\n"
            "Thank you for your time.\n\n"
            "Kind regards,\n{sender_name}"
        ),
    },
    "Thank You": {
        "icon": "🙏",
        "description": "Express gratitude after an event, meeting or help.",
        "subject": "Thank you, {name}",
        "fields": [
            ("reason", "Thank them for", "your time and support"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Dear {name},\n\n"
            "Thank you very much for {reason}. It truly meant a lot to me.\n\n"
            "I look forward to staying in touch.\n\n"
            "Sincerely,\n{sender_name}"
        ),
    },
    "Job Application": {
        "icon": "💼",
        "description": "Reach out to recruiters or hiring managers.",
        "subject": "Application for {role}",
        "fields": [
            ("role", "Role", "Machine Learning Engineer"),
            ("skills", "Key skills", "Python, LangChain, RAG, Streamlit"),
            ("sender_name", "Your name", "Your Name"),
            ("phone", "Phone", "+91 00000 00000"),
        ],
        "body": (
            "Dear {name},\n\n"
            "I am writing to express my interest in the {role} position. "
            "I have hands-on experience with {skills}, and I am eager to "
            "contribute to your team.\n\n"
            "I have attached my resume for your review. I would welcome the "
            "opportunity to discuss how I can add value.\n\n"
            "Thank you for your consideration.\n\n"
            "Sincerely,\n{sender_name}\n{phone}"
        ),
    },
    "Announcement": {
        "icon": "📢",
        "description": "Share news, product updates or newsletters.",
        "subject": "{headline}",
        "fields": [
            ("headline", "Headline", "Big news from our team"),
            ("details", "Announcement details", "We have launched a new feature that makes your work faster."),
            ("link", "Link", "https://example.com"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Hello {name},\n\n"
            "{details}\n\n"
            "Learn more: {link}\n\n"
            "Best,\n{sender_name}"
        ),
    },
    "Reminder": {
        "icon": "⏰",
        "description": "Send a friendly reminder about a deadline or event.",
        "subject": "Reminder: {item}",
        "fields": [
            ("item", "Reminder about", "Registration deadline"),
            ("when", "Due date / time", "30 October 2026"),
            ("sender_name", "Your name", "Your Name"),
        ],
        "body": (
            "Hi {name},\n\n"
            "This is a friendly reminder about {item}, due on {when}.\n\n"
            "Please let me know if you have any questions.\n\n"
            "Thanks,\n{sender_name}"
        ),
    },
    "Custom": {
        "icon": "✍️",
        "description": "Write your own subject and message from scratch.",
        "subject": "Hello from {sender_name}",
        "fields": [("sender_name", "Your name", "Your Name")],
        "body": "Hi {name},\n\nWrite your message here.\n\nBest regards,\n{sender_name}",
    },
}


def fill(text, values):
    """Fill every placeholder except {name}, which is personalised at send time."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


# ====================================================================
# Load the user's sending script (the .py file that defines send_emails)
# ====================================================================
def load_sender_module():
    here = Path(__file__).resolve().parent
    for file in sorted(here.glob("*.py")):
        if file.name == Path(__file__).name:
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        if "def send_emails" in text:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


# ====================================================================
# Page config + theme (dark purple & cyan)
# ====================================================================
st.set_page_config(page_title="Email Automation System", page_icon="✉️", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --bg: #0f0720;
        --panel: rgba(124, 58, 237, 0.10);
        --border: rgba(167, 139, 250, 0.22);
        --purple: #7c3aed;
        --purple-soft: #a78bfa;
        --cyan: #22d3ee;
        --text: #ece9fb;
        --muted: #a79fc9;
    }
    .stApp {
        background:
            radial-gradient(900px 500px at 10% -10%, rgba(124,58,237,0.35), transparent 60%),
            radial-gradient(800px 500px at 100% 0%, rgba(34,211,238,0.18), transparent 55%),
            var(--bg);
        color: var(--text);
    }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2rem; max-width: 1250px; }
    h1, h2, h3, h4, label, p, span { color: var(--text); }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #170a33 0%, #0d0620 100%);
        border-right: 1px solid var(--border);
    }

    .hero {
        padding: 2rem 2.4rem; border-radius: 22px; margin-bottom: 1.6rem;
        background: linear-gradient(120deg, rgba(124,58,237,0.45), rgba(34,211,238,0.18));
        border: 1px solid var(--border);
        box-shadow: 0 18px 50px rgba(0,0,0,0.45);
    }
    .hero h1 {
        margin: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.5px;
        background: linear-gradient(90deg, #ffffff, var(--cyan));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero p { margin: .5rem 0 0; color: #cfc8ee; font-size: 1.05rem; }
    .badge {
        display: inline-block; padding: .2rem .7rem; border-radius: 999px; font-size: .75rem;
        font-weight: 600; margin-bottom: .8rem; letter-spacing: .6px;
        color: var(--cyan); border: 1px solid rgba(34,211,238,0.5); background: rgba(34,211,238,0.08);
    }

    .step {
        display: flex; align-items: center; gap: .7rem; margin: 1.2rem 0 .6rem;
        font-size: 1.15rem; font-weight: 700;
    }
    .step .num {
        width: 30px; height: 30px; border-radius: 50%; display: inline-flex;
        align-items: center; justify-content: center; font-size: .9rem; font-weight: 800;
        background: linear-gradient(135deg, var(--purple), var(--cyan)); color: #fff;
    }
    .tpl-info {
        padding: .8rem 1rem; border-radius: 12px; background: var(--panel);
        border: 1px solid var(--border); color: var(--muted); margin: .4rem 0 .8rem;
    }

    .mail-window {
        border-radius: 16px; overflow: hidden; border: 1px solid var(--border);
        box-shadow: 0 14px 40px rgba(0,0,0,0.5); background: #fbfaff;
    }
    .mail-bar {
        padding: .7rem 1.1rem; background: linear-gradient(90deg, #4c1d95, #0e7490);
        color: #fff; font-size: .85rem; line-height: 1.6;
    }
    .mail-bar b { color: #a5f3fc; }
    .mail-body {
        padding: 1.4rem 1.6rem; color: #1e1b3a; white-space: pre-wrap;
        font-family: "Segoe UI", Georgia, serif; line-height: 1.65; font-size: .98rem;
    }

    div[data-testid="stMetric"] {
        background: var(--panel); border: 1px solid var(--border);
        padding: .9rem 1.1rem; border-radius: 16px;
    }
    div[data-testid="stMetricValue"] { color: var(--cyan); }

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.05) !important; color: var(--text) !important;
        border: 1px solid var(--border) !important; border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--cyan) !important; box-shadow: 0 0 0 1px var(--cyan) !important;
    }
    div[data-testid="stFileUploader"] section {
        background: var(--panel); border: 1px dashed var(--purple-soft); border-radius: 14px;
    }

    .stButton > button, .stDownloadButton > button {
        border: none; border-radius: 12px; padding: .65rem 1.5rem; font-weight: 700; color: #fff;
        background: linear-gradient(90deg, var(--purple), #0891b2);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-2px); color: #fff;
        box-shadow: 0 10px 26px rgba(34,211,238,0.30);
    }
    .stButton > button:disabled { opacity: .45; }

    .stTabs [data-baseweb="tab-list"] { gap: .4rem; }
    .stTabs [data-baseweb="tab"] {
        background: var(--panel); border-radius: 10px 10px 0 0; padding: .5rem 1.2rem; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background: rgba(34,211,238,0.15); color: var(--cyan); }
    hr { border-color: var(--border); }
    .footer { text-align: center; color: var(--muted); font-size: .8rem; margin-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <span class="badge">GMAIL · SMTP · PERSONALISED</span>
        <h1>Email Automation System</h1>
        <p>Pick a template, personalise it, upload your contacts and send professional emails in minutes.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

sender_module = load_sender_module()
if sender_module is None:
    st.error(
        "Could not find your email script. Keep the file that contains `send_emails()` "
        "in the same folder as app.py."
    )
    st.stop()

EMAIL_REGEX = sender_module.EMAIL_REGEX
send_emails = sender_module.send_emails

# ====================================================================
# Sidebar: credentials
# ====================================================================
with st.sidebar:
    st.markdown("### 🔐 Gmail Account")
    sender = st.text_input("Gmail address", value=os.getenv("EMAIL_SENDER", ""), placeholder="you@gmail.com")
    password = st.text_input(
        "App Password",
        value=os.getenv("EMAIL_PASSWORD", ""),
        type="password",
        help="16-character Google App Password, not your normal Gmail password.",
    )
    if password and len(password.replace(" ", "")) != 16:
        st.warning("App Password should be 16 characters.")

    st.divider()
    st.markdown("### ⚙️ Options")
    debug = st.toggle("SMTP debug output", value=False)
    st.caption("A 2-second pause is added between emails to stay within Gmail limits.")

    st.divider()
    st.markdown("### 📄 Sample contacts file")
    sample = pd.DataFrame({"name": ["Alex", "Priya"], "email": ["alex@example.com", "priya@example.com"]})
    st.download_button("Download sample CSV", sample.to_csv(index=False), "contacts_sample.csv", "text/csv")


def run_send(contacts_df, subject, body, attachment_file):
    """Write temp files, call the user's send_emails(), and return (result, error, console)."""
    buffer = io.StringIO()
    result, error = None, None
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        contacts_path = tmp_path / "contacts.csv"
        template_path = tmp_path / "email_template.txt"
        contacts_df.to_csv(contacts_path, index=False)
        template_path.write_text(body, encoding="utf-8")

        attachment_path = None
        if attachment_file:
            attachment_path = tmp_path / attachment_file.name
            attachment_path.write_bytes(attachment_file.getvalue())

        os.environ["EMAIL_SENDER"] = sender
        os.environ["EMAIL_PASSWORD"] = password
        os.environ["SMTP_DEBUG"] = "1" if debug else "0"

        try:
            with contextlib.redirect_stdout(buffer):
                result = send_emails(
                    subject=subject,
                    contact_file=str(contacts_path),
                    attachment_path=str(attachment_path) if attachment_path else None,
                    template_file=str(template_path),
                    log_file=LOG_FILE,
                )
        except Exception as exc:
            error = exc
    return result, error, buffer.getvalue()


def show_result(result, error, console):
    if error:
        st.error(f"❌ {error}")
    elif result is not None:
        sent = int((result["status"] == "Sent").sum())
        failed = int((result["status"] == "Failed").sum())
        if failed == 0:
            st.success(f"All {sent} email(s) sent successfully.")
        else:
            st.warning(f"{sent} sent, {failed} failed.")
        c1, c2 = st.columns(2)
        c1.metric("Sent", sent)
        c2.metric("Failed", failed)
        st.dataframe(result, use_container_width=True)
    with st.expander("Console output"):
        st.code(console or "No output.")


# ====================================================================
# Main tabs
# ====================================================================
tab_compose, tab_logs = st.tabs(["✉️ Compose & Send", "📊 Delivery Logs"])

with tab_compose:
    left, right = st.columns([1.05, 1], gap="large")

    # ---------------- Step 1: template ----------------
    with left:
        st.markdown('<div class="step"><span class="num">1</span> Choose a template</div>', unsafe_allow_html=True)
        template_name = st.selectbox(
            "Email type",
            list(TEMPLATES.keys()),
            format_func=lambda t: f"{TEMPLATES[t]['icon']}  {t}",
            label_visibility="collapsed",
        )
        tpl = TEMPLATES[template_name]
        st.markdown(f'<div class="tpl-info">{html.escape(tpl["description"])}</div>', unsafe_allow_html=True)

        # ---------------- Step 2: details ----------------
        st.markdown('<div class="step"><span class="num">2</span> Fill in the details</div>', unsafe_allow_html=True)
        values = {}
        field_cols = st.columns(2)
        for i, (key, label, default) in enumerate(tpl["fields"]):
            with field_cols[i % 2]:
                if key in ("details",):
                    values[key] = st.text_area(label, value=default, key=f"{template_name}_{key}", height=100)
                else:
                    values[key] = st.text_input(label, value=default, key=f"{template_name}_{key}")

        subject_raw = st.text_input("Subject", value=tpl["subject"], key=f"{template_name}_subject")
        with st.expander("✏️ Edit message body (advanced)"):
            body_raw = st.text_area(
                "Use {name} for the contact's name",
                value=tpl["body"],
                height=260,
                key=f"{template_name}_body",
            )
    # Fill the template with the details (widgets inside an expander still return their values)
    subject_final = fill(subject_raw, values)
    body_final = fill(body_raw, values)

    # ---------------- Step 3: contacts ----------------
    with left:
        st.markdown('<div class="step"><span class="num">3</span> Upload contacts</div>', unsafe_allow_html=True)
        contacts_file = st.file_uploader(
            "CSV with `name` and `email` columns", type=["csv"], label_visibility="collapsed"
        )

        df = None
        if contacts_file:
            try:
                df = pd.read_csv(contacts_file, dtype=str).fillna("")
                df.columns = [str(c).strip().lower() for c in df.columns]
                if not {"name", "email"}.issubset(df.columns):
                    st.error("CSV must contain `name` and `email` columns.")
                    df = None
            except Exception as exc:
                st.error(f"Could not read CSV: {exc}")
                df = None

        if df is not None:
            valid_mask = df["email"].apply(lambda x: bool(EMAIL_REGEX.match(str(x).strip())))
            m1, m2, m3 = st.columns(3)
            m1.metric("Contacts", len(df))
            m2.metric("Valid emails", int(valid_mask.sum()))
            m3.metric("Invalid", int((~valid_mask).sum()))
            st.dataframe(df, use_container_width=True, height=180)

        st.markdown('<div class="step"><span class="num">4</span> Attachment (optional)</div>', unsafe_allow_html=True)
        attachment = st.file_uploader("Attach a file", key="attachment", label_visibility="collapsed")

    # ---------------- Right column: preview + send ----------------
    with right:
        st.markdown('<div class="step"><span class="num">5</span> Preview</div>', unsafe_allow_html=True)
        preview_name = df["name"].iloc[0] if df is not None and len(df) else "Alex"
        preview_body = body_final.replace("{name}", preview_name)
        preview_subject = subject_final.replace("{name}", preview_name)
        to_line = df["email"].iloc[0] if df is not None and len(df) else "recipient@example.com"
        attach_line = f"<br><b>Attachment:</b> {html.escape(attachment.name)}" if attachment else ""

        st.markdown(
            f"""
            <div class="mail-window">
                <div class="mail-bar">
                    <b>From:</b> {html.escape(sender or 'you@gmail.com')}<br>
                    <b>To:</b> {html.escape(to_line)}<br>
                    <b>Subject:</b> {html.escape(preview_subject)}{attach_line}
                </div>
                <div class="mail-body">{html.escape(preview_body)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="step"><span class="num">6</span> Review & send</div>', unsafe_allow_html=True)
        ready = bool(df is not None and sender and password and subject_final.strip() and body_final.strip())

        t1, t2 = st.columns(2)
        send_test = t1.button("🧪 Send test to myself", disabled=not (sender and password), use_container_width=True)
        confirm = st.checkbox("I have reviewed the preview, contacts and attachment.")
        send_all = t2.button(
            "🚀 Send to all contacts",
            disabled=not (ready and confirm),
            use_container_width=True,
        )

        if not ready:
            st.caption("Enter your Gmail login, upload a valid contacts CSV and complete the template to enable sending.")

        if send_test:
            test_df = pd.DataFrame({"name": ["Test"], "email": [sender]})
            with st.spinner("Sending test email..."):
                res, err, out = run_send(test_df, subject_final, body_final, attachment)
            show_result(res, err, out)

        if send_all:
            with st.spinner(f"Sending {len(df)} email(s)... please wait"):
                res, err, out = run_send(df, subject_final, body_final, attachment)
            if res is not None and not err and int((res["status"] == "Failed").sum()) == 0:
                st.balloons()
            show_result(res, err, out)

with tab_logs:
    st.markdown("### Delivery history")
    log_path = Path(LOG_FILE)
    if log_path.exists() and log_path.stat().st_size > 0:
        logs = pd.read_csv(log_path)
        total = len(logs)
        sent = int((logs["status"] == "Sent").sum())
        failed = int((logs["status"] == "Failed").sum())
        rate = f"{(sent / total * 100):.0f}%" if total else "0%"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", total)
        c2.metric("Sent", sent)
        c3.metric("Failed", failed)
        c4.metric("Success rate", rate)

        f1, f2 = st.columns([1, 2])
        status_filter = f1.multiselect("Status", ["Sent", "Failed"], default=["Sent", "Failed"])
        search = f2.text_input("Search name or email")

        view = logs[logs["status"].isin(status_filter)]
        if search:
            mask = view["name"].astype(str).str.contains(search, case=False, na=False) | view["email"].astype(
                str
            ).str.contains(search, case=False, na=False)
            view = view[mask]

        st.dataframe(view.iloc[::-1], use_container_width=True, height=380)
        st.download_button("⬇️ Download logs (CSV)", logs.to_csv(index=False), "email_logs.csv", "text/csv")
    else:
        st.info("No logs yet. Send your first batch and the history will appear here.")

st.markdown('<div class="footer">Email Automation System · Built with Streamlit</div>', unsafe_allow_html=True)