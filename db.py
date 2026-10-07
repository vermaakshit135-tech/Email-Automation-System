import os

import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "email_automation")


def _config(with_db=True):
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    if with_db:
        cfg["database"] = DB_NAME
    return cfg


def get_connection():
    return mysql.connector.connect(**_config())


def init_db():
    """Create the database and tables the first time the app runs."""
    conn = mysql.connector.connect(**_config(with_db=False))
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    conn.database = DB_NAME
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # one row per "send emails" click
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            subject VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    # one row per person in the contacts file
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS email_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            campaign_id INT NOT NULL,
            user_id INT NOT NULL,
            contact_name VARCHAR(255),
            contact_email VARCHAR(255) NOT NULL,
            status VARCHAR(10) NOT NULL,
            error_message TEXT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------- users ----------
def create_user(username, email, password):
    """Returns (ok, message)."""
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, pw_hash),
        )
        conn.commit()
        return True, "Account created."
    except mysql.connector.IntegrityError:
        return False, "That username or email is already registered."
    finally:
        cur.close()
        conn.close()


def authenticate(username, password):
    """Returns the user as a dict, or None if the login is wrong."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, username, email, password_hash FROM users WHERE username = %s",
        (username,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return {"id": user["id"], "username": user["username"], "email": user["email"]}
    return None


# ---------- sending history ----------
def create_campaign(user_id, subject):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO campaigns (user_id, subject) VALUES (%s, %s)",
        (user_id, subject),
    )
    conn.commit()
    campaign_id = cur.lastrowid
    cur.close()
    conn.close()
    return campaign_id


def log_email(campaign_id, user_id, name, email, status, error_message=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO email_logs (campaign_id, user_id, contact_name, contact_email, status, error_message) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (campaign_id, user_id, name, email, status, error_message or None),
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_campaign_if_empty(campaign_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM campaigns WHERE id = %s "
        "AND NOT EXISTS (SELECT 1 FROM email_logs WHERE campaign_id = %s)",
        (campaign_id, campaign_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_campaigns(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT c.id, c.subject, c.created_at,
               COUNT(l.id) AS total,
               COALESCE(SUM(l.status = 'Sent'), 0) AS sent,
               COALESCE(SUM(l.status = 'Failed'), 0) AS failed
        FROM campaigns c
        LEFT JOIN email_logs l ON l.campaign_id = c.id
        WHERE c.user_id = %s
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for r in rows:
        r["sent"], r["failed"] = int(r["sent"]), int(r["failed"])
    return rows


def get_campaign_logs(campaign_id, user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT contact_name, contact_email, status, error_message, sent_at "
        "FROM email_logs WHERE campaign_id = %s AND user_id = %s ORDER BY id",
        (campaign_id, user_id),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows