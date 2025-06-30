import random
from flask import Flask, render_template, request, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
from datetime import datetime, timedelta
from flask import session


load_dotenv()  # Load the .env file

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# List of possible colors for subjects
color_palette = [
    "bg-blue-500", "bg-green-500", "bg-yellow-500", "bg-red-500", 
    "bg-purple-500", "bg-pink-500", "bg-teal-500", "bg-indigo-500"
]

# Store colors for subjects (to ensure same subject always gets the same color)
subject_colors = {}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form["exam_info"]

        response = client.chat.completions.create(
            model="ft:gpt-3.5-turbo-0125:personal::BMDsQVEj",
            messages=[
                {"role": "system", "content": "You are a study schedule generator."},
                {"role": "user", "content": user_input}
            ]
        )

        schedule = response.choices[0].message.content
        # Pass the schedule and current day to the next page
        session["schedule"] = schedule
        session["current_day"] = datetime.today().strftime('%A')
        return redirect(url_for("show_schedule"))

    
    return render_template("index.html")

@app.route("/schedule")
def show_schedule():
    schedule = session.get("schedule", "")
    
    # Get current date and calculate next day
    today = datetime.today()
    next_day = (today + timedelta(days=1)).strftime('%A')
    
    study_slots = parse_schedule(schedule, next_day)
    
    # Calculate the correct order of days starting from next_day
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    start_index = days_order.index(next_day)
    ordered_days = days_order[start_index:] + days_order[:start_index]
    
    return render_template("schedule.html", 
                         study_slots=study_slots,
                         start_day=next_day,
                         ordered_days=ordered_days)

def parse_schedule(schedule_text, start_day):
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    start_index = days_order.index(start_day)
    ordered_days = days_order[start_index:] + days_order[:start_index]

    # Find all "day X" headers and their content
    day_blocks = re.findall(r"(day\s*\d+)\s*:\s*(.*?)(?=day\s*\d+\s*:|$)", schedule_text, re.IGNORECASE | re.DOTALL)

    study_slots = []

    for i, (day_label, content) in enumerate(day_blocks):
        weekday = ordered_days[i % 7]
        tasks = re.split(r",\s*|\n+", content.strip())

        current_subject = None
        subject_topic_map = {}

        for task in tasks:
            if ":" in task:
                subject, topic = task.split(":", 1)
                current_subject = subject.strip()
                topic = topic.strip()
            else:
                # If task doesn't include a subject, it's probably a continuation
                if current_subject:
                    subject = current_subject
                    topic = task.strip()
                else:
                    continue  # skip malformed lines

            if subject not in subject_topic_map:
                subject_topic_map[subject] = []

            if topic:
                subject_topic_map[subject].append(topic)

        for subject, topics in subject_topic_map.items():
            if subject not in subject_colors:
                subject_colors[subject] = random.choice(color_palette)

            study_slots.append({
                "subject": subject,
                "day": weekday,
                "time": ", ".join(topics),
                "color": subject_colors[subject]
            })

    return study_slots

if __name__ == "__main__":
    app.run(debug=True)