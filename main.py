import schedule
import time
from datetime import datetime, timedelta
import subprocess
import sys
import os
import json
import requests
from dotenv import load_dotenv


load_dotenv()


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


# Load constants globally
config = load_config("config.json")
SCHEDULED_TIMES = config["scheduled_times"]
SCHEDULED_DAYS = config["scheduled_days"]
PRIMARY_URL = config["primary_url"]
FALLBACK_URL = config["fallback_url"]
FULL_DURATION_SECONDS = config["full_duration_seconds"]
FULL_DURATION_MINUTES = FULL_DURATION_SECONDS // 60
FFMPEG_PATH = config["ffmpeg_path"]
MIN_RETRY_DURATION = config["min_retry_duration"]
EMAIL_SENDER = config["email_sender"]
EMAIL_RECIPIENTS = config["email_recipients"]
EMAIL_SUBJECT = config["email_subject"]
EMAIL_CONTENT = config["email_content"]


def send_email(filename):

    # Set the API key
    api_key = os.environ.get("MAILGUN_API_KEY")

    # Create and send the email
    with open (filename, "rb") as attachment:
        requests.post(
            "https://api.mailgun.net/v3/jacobarychuk.me/messages",
            auth=("api", api_key),
            data={
                "from": EMAIL_SENDER,
                "to": ", ".join(EMAIL_RECIPIENTS),
                "subject": EMAIL_SUBJECT,
                "text": EMAIL_CONTENT,
            },
            files={"attachment": attachment},
        )

    os.remove(filename)


def record_for_duration(url, duration, attempt_type):

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.mp3"

    # FFmpeg command
    command = [FFMPEG_PATH, "-i", url, "-t", str(duration), filename]

    print(f"Starting {attempt_type} recording for {duration} seconds...")

    # Run the command
    with open(os.devnull, 'w') as devnull:
        subprocess.run(command, check=True, stdout=devnull, stderr=devnull)

    print(f"{attempt_type.capitalize()} recording completed: {filename}")

    return filename


def retry_recording(remaining_time):
    if remaining_time <= 0:
        print("No remaining time to retry.")
    elif remaining_time > MIN_RETRY_DURATION:
        print(f"Retrying for remaining duration: {remaining_time} seconds")
        try:
            return record_for_duration(FALLBACK_URL, remaining_time, "retry")
        except subprocess.CalledProcessError as e:
            print(f"Retry also failed: {e}", file=sys.stderr)
    else:
         print("Not enough time remaining to retry.")


def job():

    # Calculate the target end time
    target_end_time = datetime.now() + timedelta(minutes=FULL_DURATION_MINUTES)

    # Record the stream
    try:
        filename = record_for_duration(PRIMARY_URL, FULL_DURATION_SECONDS, "full")
        send_email(filename)
    except subprocess.CalledProcessError as e:
        print(f"Error recording stream: {e}", file=sys.stderr)
        remaining_time = int((target_end_time - datetime.now()).total_seconds())
        filename = retry_recording(remaining_time)
        if filename is not None:
            send_email(filename)


def main():

    # Add jobs to the schedule
    for scheduled_day in SCHEDULED_DAYS:
        for scheduled_time in SCHEDULED_TIMES:
            getattr(schedule.every(), scheduled_day).at(scheduled_time).do(job)

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
