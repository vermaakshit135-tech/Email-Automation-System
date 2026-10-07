import base64
import hashlib
import io
import os
import re
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

import db
from main import send_emails

st.set_page_config(page_title="Mailroom", page_icon="✉️", layout="wide")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TEMPLATE_FILE = Path("email_template.txt")
PICS_DIR = Path("profile_pics")

if "auth_view" not in st.session_state:
    st.session_state.auth_view = "login"
if "pic_key" not in st.session_state:
    st.session_state.pic_key = 0


# ---------------- medium light purple theme (white text, no black anywhere) ----------------
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@500;600;700&display=swap');

:root {
    color-scheme: light !important;
    --bg-1: #8b70d9;
    --bg-2: #7b5fcc;
    --bg-3: #6c52bd;
    --panel: #8466d4;
    --panel-solid: #7d62ce;
    --field: #ffffff;
    --ink: #3b3b4f;
    --ink-soft: #6b6b80;
    --line: rgba(255, 255, 255, 0.40);
    --btn: #a98cf2;
    --btn-hover: #b9a0f7;
    --accent: #ffd9f3;
    --white: #ffffff;
    --white-soft: rgba(255, 255, 255, 0.82);
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: linear-gradient(160deg, var(--bg-1) 0%, var(--bg-2) 55%, var(--bg-3) 100%) !important;
    color: var(--white) !important;
}
[data-testid="stHeader"] { background: #8b70d9 !important; box-shadow: 0 1px 0 var(--line); }
[data-testid="stToolbar"] { background: transparent !important; }
.stAppDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }
[data-testid="stMainBlockContainer"], .block-container { padding-top: 4.5rem !important; }
[data-testid="stHeader"] * { color: var(--white) !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, #6e53bf 0%, #5d44ab 100%) !important;
    border-right: 1px solid var(--line);
}

/* all text white */
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label,
.stApp li, .stApp div, .stApp small, .stApp a, .stApp input, .stApp textarea, .stApp button {
    color: var(--white);
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: 'Playfair Display', Georgia, serif;
    letter-spacing: 0.01em;
}
.stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li, .stApp span {
    font-family: 'Inter', system-ui, sans-serif;
}
.stApp [data-testid="stCaptionContainer"], .stApp small { color: var(--white-soft) !important; }
[data-testid="stSidebar"] a { color: var(--white) !important; text-decoration: underline; }

/* cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--panel);
    border: 1px solid var(--line) !important;
    border-radius: 18px;
    box-shadow: 0 8px 28px rgba(80, 50, 140, 0.18);
}

/* text inputs, text areas, select boxes: WHITE blocks, light-black text */
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stTextInputRootElement"] *, [data-testid="stTextAreaRootElement"] *,
[data-baseweb="input"], [data-baseweb="input"] *, [data-baseweb="base-input"], [data-baseweb="base-input"] *,
[data-baseweb="textarea"], [data-baseweb="textarea"] *, [data-baseweb="select"] > div, [data-baseweb="select"] > div *,
div:has(> input), div:has(> div > input), div:has(> textarea), input, textarea {
    background-color: #ffffff !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--ink);
}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"] {
    border: 1px solid #ffffff !important;
    border-radius: 10px !important;
}
::placeholder { color: var(--ink-soft) !important; -webkit-text-fill-color: var(--ink-soft) !important; opacity: 1; }
[data-baseweb="input"]:focus-within, [data-baseweb="base-input"]:focus-within,
[data-baseweb="textarea"]:focus-within, [data-baseweb="select"]:focus-within > div {
    border-color: #ffd9f3 !important;
    box-shadow: 0 0 0 3px rgba(255, 217, 243, 0.55) !important;
}
[data-baseweb="select"] svg, [data-baseweb="input"] svg { fill: var(--ink) !important; color: var(--ink) !important; }
[data-baseweb="input"] button, [data-baseweb="input"] button:hover {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus, textarea:-webkit-autofill {
    -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
    -webkit-text-fill-color: var(--ink) !important;
}
[data-testid="stForm"] { background: transparent !important; border: none !important; }

/* dropdown lists and every popover panel: white, light-black text */
div[data-baseweb="popover"], div[data-baseweb="popover"] > div,
[data-baseweb="menu"], ul[role="listbox"], [data-testid="stPopoverBody"] {
    background: #ffffff !important;
    color: var(--ink) !important;
}
[data-baseweb="menu"] li, ul[role="listbox"] li { background: #ffffff !important; color: var(--ink) !important; }
[data-baseweb="menu"] li:hover, ul[role="listbox"] li:hover, ul[role="listbox"] li[aria-selected="true"] {
    background: #efe9ff !important;
}
[data-testid="stPopoverBody"] {
    border: 1px solid #d9ccf7;
    border-radius: 18px;
    box-shadow: 0 14px 36px rgba(40, 20, 90, 0.30);
}
[data-testid="stPopoverBody"] :is(p, span, label, h1, h2, h3, h4, div, li):not(button *) { color: var(--ink) !important; }
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] * { color: var(--ink-soft) !important; }

/* every button: medium purple, white text */
.stButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button,
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stFileUploaderDropzone"] button {
    background: var(--btn) !important;
    color: var(--white) !important;
    border: 1px solid rgba(255, 255, 255, 0.55) !important;
    border-radius: 999px !important;
    padding: 0.45rem 1.3rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    box-shadow: 0 3px 10px rgba(40, 20, 90, 0.28);
    white-space: nowrap;
}
.stButton > button *, .stFormSubmitButton > button *, [data-testid="stPopover"] button *,
[data-testid="stFileUploaderDropzone"] button * { color: var(--white) !important; fill: var(--white) !important; }
.stButton > button:hover, .stButton > button:active, .stButton > button:focus,
.stFormSubmitButton > button:hover, .stFormSubmitButton > button:active, .stFormSubmitButton > button:focus,
[data-testid="stPopover"] button:hover, [data-testid="stPopover"] button:active,
[data-testid="stPopover"] button:focus, [data-testid="stPopover"] button[aria-expanded="true"],
[data-testid="stFileUploaderDropzone"] button:hover, [data-testid="stFileUploaderDropzone"] button:active {
    background: var(--btn-hover) !important;
    color: var(--white) !important;
    border-color: #fff !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.35) !important;
}

/* file uploader: white block, ONE clean button label (the double text overlapped) */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] > div {
    background: #ffffff !important;
    border: 1px dashed #b9a4ec !important;
    border-radius: 12px;
}
[data-testid="stFileUploaderDropzone"] :is(span, small, p, div, section):not(button *) { color: var(--ink) !important; }
[data-testid="stFileUploaderDropzone"] button {
    position: relative;
    font-size: 0 !important;
    min-width: 140px;
    min-height: 40px;
    padding: 0 !important;
    white-space: nowrap;
}
[data-testid="stFileUploaderDropzone"] button * { display: none !important; }
[data-testid="stFileUploaderDropzone"] button::after {
    content: "📁 Browse files";
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stFileUploaderFile"], [data-testid="stFileUploaderFile"] * { color: var(--ink) !important; background: transparent !important; }

/* radio menu in the sidebar: purple dots instead of black */
[data-baseweb="radio"] > div:first-child {
    background-color: rgba(255, 255, 255, 0.25) !important;
    border: 2px solid #fff !important;
}
[data-baseweb="radio"] input:checked + div, [data-baseweb="radio"] [aria-checked="true"] > div:first-child {
    background-color: var(--btn) !important;
    border-color: #fff !important;
}
[data-baseweb="radio"] > div:first-child > div { background-color: #fff !important; }
[data-testid="stRadio"] label p { color: var(--white) !important; }

/* progress, alerts, dividers, metrics, tables */
[data-testid="stProgress"] > div > div { background-color: rgba(255, 255, 255, 0.3) !important; }
[data-testid="stProgress"] > div > div > div { background-color: #fff !important; }
[data-testid="stAlert"] { background: #ffffff !important; border: 1px solid var(--line); border-radius: 12px; }
[data-testid="stAlert"] * { color: var(--ink) !important; }
hr { border-color: var(--line) !important; }
[data-testid="stMetric"] { background: #ffffff; border-radius: 14px; padding: 8px 12px; }
[data-testid="stMetricValue"] { font-family: 'Playfair Display', Georgia, serif; color: var(--ink) !important; }
[data-testid="stMetricLabel"] * { color: var(--ink-soft) !important; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid var(--line); }
[data-testid="stTooltipIcon"], [data-testid="stTooltipIcon"] * { color: #ffffff !important; background: transparent !important; }

/* top bar + profile card */
.greeting { font-family: 'Playfair Display', Georgia, serif; font-size: 1.35rem; color: var(--white); }
.greeting span { color: var(--accent); font-style: italic; }
.topbar { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
.topbar .greeting { line-height: 1.25; overflow-wrap: anywhere; min-width: 0; }
.topbar .avatar-wrap { flex: none; }
.avatar-wrap { display: flex; justify-content: center; }
.avatar-img {
    display: block;
    flex: none;
    max-width: none !important;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    border-radius: 50%;
    border: 2px solid #fff;
    box-sizing: border-box;
    box-shadow: 0 3px 12px rgba(40, 20, 90, 0.40);
}
.cred-row {
    display: flex; justify-content: space-between; gap: 12px;
    padding: 8px 12px; margin: 6px 0;
    background: #f4f0ff; border: 1px solid #d9ccf7; border-radius: 10px;
    font-family: 'Inter', system-ui, sans-serif; font-size: 0.9rem; color: var(--ink);
}
.cred-row b { color: #6a4fbd !important; font-weight: 600; }
.cred-row span { color: var(--ink) !important; word-break: break-all; text-align: right; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


@st.cache_resource
def setup_database():
    db.init_db()
    return True


def show(view):
    st.session_state.auth_view = view


# ---------------- profile picture / unique avatar ----------------
BG_COLOURS = [
    ("#ffd6e3", "#f7b6cb"),
    ("#ffe3d6", "#f8c4b0"),
    ("#fde1f0", "#e9b5d6"),
    ("#e8defa", "#cdbdf0"),
    ("#d9f0ee", "#b3dfda"),
    ("#fff0c9", "#f7dc94"),
]
SKIN_TONES = ["#fde3d1", "#f8d2b8", "#efbf98", "#dca47a", "#c08460", "#94603f"]
HAIR_COLOURS = ["#2b1b17", "#4a2c20", "#7a4a2a", "#b5651d", "#d9a441", "#c2456f", "#5b3f8c", "#1f2a44"]
SHIRT_COLOURS = ["#c2456f", "#9d2f55", "#7a5ea8", "#e07a9f", "#3b6f8f", "#d98f4e"]


def avatar_svg(seed):
    """A small illustrated face. The same username always gives the same face,
    and different usernames give different hair, skin, eyes, mouth, glasses and colours."""
    h = hashlib.md5(seed.encode()).digest()
    bg1, bg2 = BG_COLOURS[h[0] % len(BG_COLOURS)]
    skin = SKIN_TONES[h[1] % len(SKIN_TONES)]
    hair = HAIR_COLOURS[h[2] % len(HAIR_COLOURS)]
    hair_style = h[3] % 4  # 0 short, 1 long, 2 bun, 3 curly
    eyes_style = h[4] % 3
    mouth_style = h[5] % 3
    extra = h[6] % 3  # 0 none, 1 glasses, 2 blush
    shirt = SHIRT_COLOURS[h[7] % len(SHIRT_COLOURS)]
    ink = "#2b1b17"

    p = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">',
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient></defs>',
        '<rect width="100" height="100" fill="url(#g)"/>',
    ]
    if hair_style == 1:
        p.append(f'<rect x="26" y="26" width="48" height="58" rx="22" fill="{hair}"/>')
    p.append(f'<ellipse cx="50" cy="100" rx="34" ry="24" fill="{shirt}"/>')
    p.append(f'<rect x="44" y="62" width="12" height="16" rx="4" fill="{skin}"/>')
    p.append(f'<ellipse cx="50" cy="44" rx="20" ry="23" fill="{skin}"/>')
    if hair_style == 2:
        p.append(f'<circle cx="50" cy="14" r="8" fill="{hair}"/>')
    if hair_style == 3:
        for cx, cy, r in [(33, 30, 9), (44, 22, 10), (57, 22, 10), (68, 30, 9)]:
            p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{hair}"/>')
    p.append(f'<path d="M29 42 Q27 17 50 17 Q73 17 71 42 Q62 30 50 30 Q38 30 29 42Z" fill="{hair}"/>')

    if eyes_style == 0:
        p.append(f'<circle cx="42" cy="46" r="2.4" fill="{ink}"/><circle cx="58" cy="46" r="2.4" fill="{ink}"/>')
    elif eyes_style == 1:
        p.append(f'<path d="M38.5 47 Q42 42.5 45.5 47" stroke="{ink}" stroke-width="2" fill="none" stroke-linecap="round"/>')
        p.append(f'<path d="M54.5 47 Q58 42.5 61.5 47" stroke="{ink}" stroke-width="2" fill="none" stroke-linecap="round"/>')
    else:
        p.append(f'<path d="M39 46 L45 46 M55 46 L61 46" stroke="{ink}" stroke-width="2" stroke-linecap="round"/>')

    if extra == 1:
        p.append(f'<circle cx="42" cy="46" r="6.5" fill="none" stroke="{ink}" stroke-width="1.6"/>')
        p.append(f'<circle cx="58" cy="46" r="6.5" fill="none" stroke="{ink}" stroke-width="1.6"/>')
        p.append(f'<path d="M48.5 46 L51.5 46" stroke="{ink}" stroke-width="1.6"/>')
    elif extra == 2:
        p.append('<ellipse cx="36" cy="53" rx="4" ry="2.5" fill="#f48fb1" opacity="0.55"/>')
        p.append('<ellipse cx="64" cy="53" rx="4" ry="2.5" fill="#f48fb1" opacity="0.55"/>')

    if mouth_style == 0:
        p.append('<path d="M43 55 Q50 62 57 55" stroke="#8a3b3b" stroke-width="2" fill="none" stroke-linecap="round"/>')
    elif mouth_style == 1:
        p.append('<path d="M42 54 Q50 65 58 54Z" fill="#8a3b3b"/>')
    else:
        p.append('<path d="M46 56.5 Q50 59 54 56.5" stroke="#8a3b3b" stroke-width="2" fill="none" stroke-linecap="round"/>')

    p.append("</svg>")
    return "".join(p)


def pic_path(user):
    return PICS_DIR / f"{user['id']}.png"


def avatar_html(user, size=44):
    """Round profile photo if the user uploaded one, otherwise their unique avatar."""
    src = None
    path = pic_path(user)
    if path.exists():
        try:
            src = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
        except OSError:
            src = None
    if src is None:
        svg = avatar_svg(user["username"])
        src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return (
        f'<div class="avatar-wrap"><img class="avatar-img" src="{src}" alt="avatar" '
        f'style="width:{size}px;height:{size}px;min-width:{size}px;"></div>'
    )


def save_profile_picture(user, data):
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (256, 256), Image.LANCZOS)  # centre-crop to a square
    PICS_DIR.mkdir(exist_ok=True)
    img.save(pic_path(user), format="PNG")


def remove_profile_picture(user):
    try:
        pic_path(user).unlink()
    except FileNotFoundError:
        pass


def photo_controls(user, scope):
    upload = st.file_uploader(
        "Upload a photo",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key=f"pic_upload_{scope}_{st.session_state.pic_key}",
    )
    if upload and st.button("Save photo", type="primary", key=f"save_pic_{scope}"):
        try:
            save_profile_picture(user, upload.getvalue())
            st.session_state.pic_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't use that image: {e}")
    if pic_path(user).exists():
        if st.button("Remove photo", key=f"remove_pic_{scope}"):
            remove_profile_picture(user)
            st.session_state.pic_key += 1
            st.rerun()
    else:
        st.caption("No photo yet, so your own avatar is shown.")


def top_bar(user):
    campaigns = db.get_campaigns(user["id"])
    sent = sum(c["sent"] for c in campaigns)
    failed = sum(c["failed"] for c in campaigns)

    st.markdown(
        f'<div class="topbar">{avatar_html(user, 56)}'
        f'<div class="greeting">Welcome back,<br><span>{user["username"]}</span></div></div>',
        unsafe_allow_html=True,
    )
    cam, right = st.columns(2)
    with cam:
        with st.popover("📷 Photo", use_container_width=True):
            st.markdown(avatar_html(user, 88), unsafe_allow_html=True)
            st.caption("Choose a picture to use as your profile photo.")
            photo_controls(user, "top")
    with right:
        with st.popover(f"✉️ {sent} mails sent", use_container_width=True):
            st.markdown(avatar_html(user, 96), unsafe_allow_html=True)
            st.markdown(
                f"<h3 style='text-align:center;margin:8px 0 12px;color:#3b3b4f'>{user['username']}</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="cred-row"><b>Username</b><span>{user['username']}</span></div>
                <div class="cred-row"><b>Email</b><span>{user['email']}</span></div>
                <div class="cred-row"><b>Password</b><span>•••••••• (never shown)</span></div>
                """,
                unsafe_allow_html=True,
            )
            m1, m2 = st.columns(2)
            m1.metric("Sent", sent)
            m2.metric("Failed", failed)
            st.divider()
            st.caption("Profile photo")
            photo_controls(user, "card")


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
        st.markdown(avatar_html(user, 64), unsafe_allow_html=True)
        st.write(f"**{user['username']}**")
        st.caption(user["email"])
        if st.button("Log out"):
            del st.session_state.user
            st.rerun()

    top_bar(user)

    if page.endswith("Send emails"):
        send_page(user)
    else:
        history_page(user)


setup_database()
if "user" not in st.session_state:
    auth_page()
else:
    main_app()