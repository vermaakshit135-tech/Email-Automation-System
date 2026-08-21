import smtplib
import os
import pandas as pd
from datetime import datetime
from email.message import EmailMessage


# ==========================================
# SEND EMAILS FUNCTION
# ==========================================

def send_emails(
    subject="Test Email from Python",
    contact_file="contacts.csv",
    attachment_path="attachments/resume.pdf"
):

    # ==========================================
    # GMAIL DETAILS
    # ==========================================

    sender_email = "vermaakshit135@gmail.com"
    app_password = "lzto gsrh jbnz utaf"


    # ==========================================
    # READ CONTACTS CSV
    # ==========================================

    df = pd.read_csv(contact_file)


    # ==========================================
    # READ EMAIL TEMPLATE
    # ==========================================

    with open("email_template.txt", "r") as file:
        template = file.read()


    # ==========================================
    # EMAIL LOGS
    # ==========================================

    logs = []


    # ==========================================
    # CONNECT TO GMAIL
    # ==========================================

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:

        smtp.login(
            sender_email,
            app_password
        )


        # ==========================================
        # SEND EMAIL TO EVERY CONTACT
        # ==========================================

        for index, row in df.iterrows():

            receiver_email = row["email"]
            name = row["name"]

            try:

                # Create email
                message = EmailMessage()


                # Subject
                message["Subject"] = subject


                # Sender
                message["From"] = sender_email


                # Receiver
                message["To"] = receiver_email


                # ==========================================
                # PERSONALIZED EMAIL BODY
                # ==========================================

                body = template.format(
                    name=name
                )

                message.set_content(body)


                # ==========================================
                # ATTACHMENT
                # ==========================================

                if attachment_path and os.path.exists(attachment_path):

                    with open(
                        attachment_path,
                        "rb"
                    ) as file:

                        file_data = file.read()


                    message.add_attachment(
                        file_data,
                        maintype="application",
                        subtype="pdf",
                        filename=os.path.basename(
                            attachment_path
                        )
                    )


                # ==========================================
                # SEND EMAIL
                # ==========================================

                smtp.send_message(message)


                print(
                    f"Email sent successfully to {name} "
                    f"({receiver_email})"
                )


                # ==========================================
                # SUCCESS LOG
                # ==========================================

                logs.append({

                    "name": name,

                    "email": receiver_email,

                    "status": "Sent",

                    "time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                })


            except Exception as error:

                print(
                    f"Failed to send email to {name}"
                )

                print(
                    "Error:",
                    error
                )


                # ==========================================
                # FAILED LOG
                # ==========================================

                logs.append({

                    "name": name,

                    "email": receiver_email,

                    "status": "Failed",

                    "time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                })


    # ==========================================
    # SAVE EMAIL LOGS
    # ==========================================

    log_df = pd.DataFrame(logs)

    log_df.to_csv(
        "email_logs.csv",
        index=False
    )


    print("\n==============================")
    print("Email process completed!")
    print("Email logs saved successfully!")
    print("==============================")


# ==========================================
# DIRECT TEST
# ==========================================

if __name__ == "__main__":

    send_emails()