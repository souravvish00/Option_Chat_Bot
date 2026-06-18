from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
import os
import csv
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()

# --------------------------------
# App Setup
# --------------------------------

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")

STATE_FILE = "user_states.json"
LEAD_FILE = "leads.csv"

# --------------------------------
# Google Sheets Setup
# --------------------------------

def get_sheet():
    """Connect to Google Sheets and return the first worksheet."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE, scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        logger.error(f"Google Sheets connection failed: {e}")
        return None


def ensure_sheet_headers(sheet):
    """Add headers if the sheet is empty."""
    try:
        first_row = sheet.row_values(1)
        if not first_row:
            sheet.append_row([
                "Timestamp", "Phone", "Name", "Program", "Course", "UG Completed"
            ])
            logger.info("Google Sheet headers created.")
    except Exception as e:
        logger.error(f"Failed to set sheet headers: {e}")


def save_to_google_sheet(data):
    """Append a lead row to Google Sheets."""
    sheet = get_sheet()
    if sheet is None:
        logger.warning("Skipping Google Sheets — not connected.")
        return
    ensure_sheet_headers(sheet)
    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("phone", ""),
            data.get("name", ""),
            data.get("program", ""),
            data.get("course", ""),
            data.get("ug", "N/A")
        ])
        logger.info(f"Lead saved to Google Sheet for {data.get('phone')}")
    except Exception as e:
        logger.error(f"Failed to save to Google Sheets: {e}")


# --------------------------------
# State Management
# --------------------------------

def load_states():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"State file read error: {e}")
            return {}
    return {}


def save_states(data):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logger.error(f"State file write error: {e}")


# --------------------------------
# Save Lead to CSV (backup)
# --------------------------------

def save_lead_csv(data):
    file_exists = os.path.exists(LEAD_FILE)
    try:
        with open(LEAD_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "Phone", "Name", "Program", "Course", "UG Completed"
                ])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data.get("phone", ""),
                data.get("name", ""),
                data.get("program", ""),
                data.get("course", ""),
                data.get("ug", "N/A")
            ])
        logger.info(f"Lead saved to CSV for {data.get('phone')}")
    except IOError as e:
        logger.error(f"CSV write error: {e}")


def save_lead(data):
    """Save lead to both CSV (backup) and Google Sheets."""
    save_lead_csv(data)
    save_to_google_sheet(data)


# --------------------------------
# WhatsApp Message Sender
# --------------------------------

def send_message(phone, text):
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text}
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Message sent to {phone}")
    except requests.RequestException as e:
        logger.error(f"Failed to send message to {phone}: {e}")


# --------------------------------
# Course Details
# --------------------------------

COURSE_DETAILS = {
    "B.Sc": (
        "📘 *B.Sc Details*\n\n"
        "⏳ Duration: 3 Years\n"
        "🎓 Eligibility: 12th Science\n"
        "💰 Fee: ₹50,000/year"
    ),
    "BCA": (
        "💻 *BCA Details*\n\n"
        "⏳ Duration: 3 Years\n"
        "🎓 Eligibility: 12th Pass\n"
        "💰 Fee: ₹60,000/year"
    ),
    "MBA": (
        "📊 *MBA Details*\n\n"
        "⏳ Duration: 2 Years\n"
        "🎓 Eligibility: Graduation\n"
        "💰 Fee: ₹1,50,000/year"
    )
}


# --------------------------------
# Conversation Flow
# --------------------------------

def handle_message(phone, text):
    users = load_states()

    # New user
    if phone not in users:
        users[phone] = {"step": "program"}
        send_message(
            phone,
            "👋 Welcome to Admissions Bot!\n\nPlease choose a Program:\n1️⃣ UG Program\n2️⃣ PG Program"
        )
        save_states(users)
        return

    user = users[phone]
    step = user.get("step")

    # --- Step: Program ---
    if step == "program":
        if text == "1":
            user["program"] = "UG"
            user["step"] = "course_ug"
            send_message(
                phone,
                "📚 Select UG Course:\n1️⃣ B.Sc\n2️⃣ BCA"
            )
        elif text == "2":
            user["program"] = "PG"
            user["step"] = "ug_check"
            send_message(
                phone,
                "🎓 Have you completed your UG degree?\n1️⃣ Yes\n2️⃣ No"
            )
        else:
            send_message(
                phone,
                "⚠️ Please reply with *1* for UG or *2* for PG."
            )

    # --- Step: UG Eligibility Check (for PG) ---
    elif step == "ug_check":
        if text == "1":
            user["ug"] = "Yes"
            user["step"] = "course_pg"
            send_message(
                phone,
                "📚 Select PG Course:\n1️⃣ MBA"
            )
        elif text == "2":
            send_message(
                phone,
                "❌ Sorry, UG completion is required to apply for MBA.\n\nReply *hi* or any message to start again."
            )
            del users[phone]
        else:
            send_message(
                phone,
                "⚠️ Please reply *1* for Yes or *2* for No."
            )

    # --- Step: UG Course Selection ---
    elif step == "course_ug":
        if text == "1":
            user["course"] = "B.Sc"
        elif text == "2":
            user["course"] = "BCA"
        else:
            send_message(phone, "⚠️ Please reply *1* for B.Sc or *2* for BCA.")
            save_states(users)
            return
        user["ug"] = "N/A"
        user["step"] = "name"
        send_message(phone, "✏️ Please enter your full name:")

    # --- Step: PG Course Selection ---
    elif step == "course_pg":
        if text == "1":
            user["course"] = "MBA"
        else:
            send_message(phone, "⚠️ Please reply *1* for MBA.")
            save_states(users)
            return
        user["step"] = "name"
        send_message(phone, "✏️ Please enter your full name:")

    # --- Step: Name ---
    elif step == "name":
        if len(text) < 2:
            send_message(phone, "⚠️ Please enter a valid name.")
            save_states(users)
            return

        user["name"] = text
        user["phone"] = phone

        save_lead(user)

        course = user.get("course", "")
        details = COURSE_DETAILS.get(course, "Details not available.")

        send_message(
            phone,
            f"✅ Thank you, *{user['name']}*! Your enquiry has been recorded.\n\n{details}\n\n📞 Our team will contact you shortly."
        )

        logger.info(f"Lead captured: {user}")
        del users[phone]

    else:
        # Unknown step — reset
        logger.warning(f"Unknown step '{step}' for {phone}. Resetting.")
        del users[phone]
        send_message(
            phone,
            "⚠️ Something went wrong. Let's start over.\n\nReply with any message to begin."
        )

    save_states(users)


# --------------------------------
# Webhook Routes
# --------------------------------

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return challenge, 200
    logger.warning("Webhook verification failed.")
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return "Bad Request", 400

    try:
        entry = data.get("entry", [])
        if not entry:
            return "OK", 200

        changes = entry[0].get("changes", [])
        if not changes:
            return "OK", 200

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return "OK", 200

        message = messages[0]
        phone = message.get("from")
        msg_type = message.get("type")

        if msg_type != "text":
            send_message(phone, "⚠️ Please send a text message only.")
            return "OK", 200

        text = message["text"]["body"].strip()
        logger.info(f"Received from {phone}: {text}")
        handle_message(phone, text)

    except Exception as e:
        logger.exception(f"Webhook error: {e}")

    return "OK", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "whatsapp-admissions-bot"}), 200


# --------------------------------
# Run
# --------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
