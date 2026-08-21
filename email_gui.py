import tkinter as tk
from tkinter import messagebox, filedialog
import schedule
import threading
import time

from main import send_emails


# ==========================================
# MAIN WINDOW
# ==========================================

window = tk.Tk()

window.title("Email Automation System")
window.geometry("650x650")


# ==========================================
# TITLE
# ==========================================

title = tk.Label(
    window,
    text="EMAIL AUTOMATION SYSTEM",
    font=("Arial", 20, "bold")
)

title.pack(pady=20)


# ==========================================
# SUBJECT
# ==========================================

subject_label = tk.Label(
    window,
    text="Email Subject:",
    font=("Arial", 11)
)

subject_label.pack()

subject_entry = tk.Entry(
    window,
    width=55
)

subject_entry.pack(pady=8)


# ==========================================
# CONTACT CSV
# ==========================================

contact_file = tk.StringVar(
    value="contacts.csv"
)

contact_label = tk.Label(
    window,
    text="Contacts CSV:",
    font=("Arial", 11)
)

contact_label.pack(pady=(10, 0))

contact_entry = tk.Entry(
    window,
    textvariable=contact_file,
    width=55
)

contact_entry.pack(pady=8)


def select_contacts():

    file_path = filedialog.askopenfilename(
        title="Select Contacts CSV",
        filetypes=[
            ("CSV Files", "*.csv")
        ]
    )

    if file_path:
        contact_file.set(file_path)


contact_button = tk.Button(
    window,
    text="SELECT CONTACTS",
    command=select_contacts,
    width=20
)

contact_button.pack(pady=5)


# ==========================================
# ATTACHMENT
# ==========================================

attachment_file = tk.StringVar(
    value="attachments/resume.pdf"
)

attachment_label = tk.Label(
    window,
    text="Attachment:",
    font=("Arial", 11)
)

attachment_label.pack(pady=(10, 0))

attachment_entry = tk.Entry(
    window,
    textvariable=attachment_file,
    width=55
)

attachment_entry.pack(pady=8)


def select_attachment():

    file_path = filedialog.askopenfilename(
        title="Select Attachment",
        filetypes=[
            ("PDF Files", "*.pdf"),
            ("All Files", "*.*")
        ]
    )

    if file_path:
        attachment_file.set(file_path)


attachment_button = tk.Button(
    window,
    text="SELECT ATTACHMENT",
    command=select_attachment,
    width=20
)

attachment_button.pack(pady=5)


# ==========================================
# SCHEDULE TIME
# ==========================================

time_label = tk.Label(
    window,
    text="Schedule Time (HH:MM):",
    font=("Arial", 11)
)

time_label.pack(pady=(15, 0))

time_entry = tk.Entry(
    window,
    width=25
)

time_entry.pack(pady=8)


# ==========================================
# SEND EMAIL
# ==========================================

def send_button():

    subject = subject_entry.get().strip()
    contacts = contact_file.get().strip()
    attachment = attachment_file.get().strip()

    if not subject:

        messagebox.showwarning(
            "Warning",
            "Please enter an email subject."
        )

        return

    if not contacts:

        messagebox.showwarning(
            "Warning",
            "Please select a contacts CSV file."
        )

        return

    try:

        status_label.config(
            text="Status: Sending emails..."
        )

        window.update()

        send_emails(
            subject,
            contacts,
            attachment
        )

        status_label.config(
            text="Status: Emails sent successfully!"
        )

        messagebox.showinfo(
            "Success",
            "Emails sent successfully!"
        )

    except Exception as error:

        status_label.config(
            text="Status: Failed"
        )

        messagebox.showerror(
            "Error",
            f"Email sending failed:\n{error}"
        )


# ==========================================
# SEND BUTTON
# ==========================================

send_btn = tk.Button(
    window,
    text="SEND EMAIL NOW",
    command=send_button,
    width=25,
    height=2
)

send_btn.pack(pady=15)


# ==========================================
# SCHEDULE EMAIL
# ==========================================

def schedule_button():

    subject = subject_entry.get().strip()
    contacts = contact_file.get().strip()
    attachment = attachment_file.get().strip()
    schedule_time = time_entry.get().strip()

    if not subject:

        messagebox.showwarning(
            "Warning",
            "Please enter an email subject."
        )

        return

    if not contacts:

        messagebox.showwarning(
            "Warning",
            "Please select a contacts CSV file."
        )

        return

    if not schedule_time:

        messagebox.showwarning(
            "Warning",
            "Please enter schedule time."
        )

        return

    try:

        schedule.clear()

        schedule.every().day.at(
            schedule_time
        ).do(
            send_emails,
            subject,
            contacts,
            attachment
        )

        status_label.config(
            text=f"Status: Scheduled for {schedule_time}"
        )

        messagebox.showinfo(
            "Scheduled",
            f"Email scheduled for {schedule_time}"
        )

    except Exception as error:

        messagebox.showerror(
            "Error",
            f"Invalid time format:\n{error}"
        )


# ==========================================
# SCHEDULE BUTTON
# ==========================================

schedule_btn = tk.Button(
    window,
    text="SCHEDULE EMAIL",
    command=schedule_button,
    width=25,
    height=2
)

schedule_btn.pack(pady=5)


# ==========================================
# STATUS
# ==========================================

status_label = tk.Label(
    window,
    text="Status: Ready",
    font=("Arial", 11, "bold")
)

status_label.pack(pady=20)


# ==========================================
# BACKGROUND SCHEDULER
# ==========================================

def run_scheduler():

    while True:

        schedule.run_pending()

        time.sleep(1)


scheduler_thread = threading.Thread(
    target=run_scheduler,
    daemon=True
)

scheduler_thread.start()


# ==========================================
# START GUI
# ==========================================

window.mainloop()