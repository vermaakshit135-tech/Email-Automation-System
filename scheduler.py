def schedule_button():

    subject = subject_entry.get()
    schedule_time = time_entry.get()

    if not subject:
        messagebox.showwarning(
            "Warning",
            "Please enter an email subject."
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

        schedule.every().day.at(schedule_time).do(
            send_emails,
            subject
        )

        status_label.config(
            text=f"Status: Scheduled for {schedule_time}"
        )

        messagebox.showinfo(
            "Scheduled",
            f"Email scheduled successfully for {schedule_time}"
        )

    except Exception as error:

        messagebox.showerror(
            "Error",
            f"Invalid time:\n{error}"
        )