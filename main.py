import requests
import random
import string
import json
from flask import Flask, request, jsonify 
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup

# --- KONFIGURASI DAN INICIALISASI ---

# Ganti dengan Token Bot Anda
BOT_TOKEN = "5391771268:AAEhgFIWqPRD16fQ2fkmgI8FBH2dYwLaFe4" 
MAIL_TM_API = "https://api.mail.tm"
user_sessions = {}
ADMIN_IDS = [1188483395] 
# 🗑️ REQUIRED_CHANNEL DIHAPUS

# Inisialisasi Aplikasi Flask dan Telegram Bot
app = Flask(__name__)
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# --- FUNGSI UTILITAS DASAR ---

def random_str(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def send_message(chat_id, text, reply_markup=None):
    """Fungsi pembantu untuk mengirim pesan via HTTP request ke Telegram API."""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        # Flask harus mengirim markup dalam bentuk JSON string
        payload['reply_markup'] = json.dumps(reply_markup)
        
    requests.post(TELEGRAM_API_URL + 'sendMessage', data=payload)

# 🗑️ FUNGSI check_membership DIHAPUS

# --- LOGIKA BOT (Fungsi yang Dimodifikasi) ---

def handle_start(update: Update, user_id, chat_id):
    # 🧱 Membuat Reply Keyboard dengan EMOJI
    keyboard = [
        [
            {"text": "📧 /new"}, 
            {"text": "📥 /inbox"}
        ],
        [
            {"text": "🗑️ /delete"}, 
            {"text": "ℹ️ /info"}
        ]
    ]
    reply_markup = {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

    msg = (
        "👋 *Welcome to TempMail Bot!*\n\n"
        "You can use the following commands or the keyboard below:\n\n"
        "📧 `/new` – Create a new temporary email\n"
        "📥 `/inbox` – View inbox messages\n"
        "🗑️ `/delete` – Delete your current temp email\n"
        "ℹ️ `/info` – Show your current email session\n"
    )
    
    send_message(chat_id, msg, reply_markup)


def handle_new_email(update: Update, user_id, chat_id):
    # 🗑️ Pengecekan membership DIHAPUS

    username = random_str()
    password = random_str()

    # Get domain
    domains_resp = requests.get(f"{MAIL_TM_API}/domains")
    if domains_resp.status_code != 200:
        return send_message(chat_id, "❌ Failed to fetch mail domains.")
    domain = domains_resp.json()["hydra:member"][0]["domain"]
    email = f"{username}@{domain}"

    # Create account
    create_resp = requests.post(f"{MAIL_TM_API}/accounts", json={"address": email, "password": password})
    if create_resp.status_code not in [200, 201]:
        return send_message(chat_id, "❌ Failed to create email.")

    # Auth token
    token_resp = requests.post(f"{MAIL_TM_API}/token", json={"address": email, "password": password})
    if token_resp.status_code != 200:
        return send_message(chat_id, "❌ Failed to authenticate.")

    token = token_resp.json()["token"]
    user_sessions[user_id] = {
        "email": email,
        "password": password,
        "token": token
    }

    send_message(chat_id, f"✅ Your temp email:\n📧 `{email}`")


def handle_inbox(update: Update, user_id, chat_id):
    session = user_sessions.get(user_id)
    if not session:
        return send_message(chat_id, "ℹ️ Use /new to create a temporary email first.")

    headers = {"Authorization": f"Bearer {session['token']}"}
    r = requests.get(f"{MAIL_TM_API}/messages", headers=headers)
    data = r.json()
    if not data["hydra:member"]:
        return send_message(chat_id, "📭 Inbox is empty.")

    for m in data["hydra:member"][:3]:
        msg_id = m["id"]
        detail_resp = requests.get(f"{MAIL_TM_API}/messages/{msg_id}", headers=headers)
        if detail_resp.status_code != 200:
            continue

        msg_detail = detail_resp.json()
        sender = msg_detail["from"]["address"]
        subject = msg_detail["subject"] or "(no subject)"
        body = msg_detail.get("text", "(No content)")

        text = (
            f"*From:* `{sender}`\n"
            f"*Subject:* _{subject}_\n\n"
            f"*Message:*\n"
            f"\n{body.strip()[:1000]}\n"
        )
        send_message(chat_id, text)

def handle_delete_email(update: Update, user_id, chat_id):
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        send_message(chat_id, "🗑️ Your temp email has been deleted.")
    else:
        send_message(chat_id, "ℹ️ No temp email to delete.")

def handle_info(update: Update, user_id, chat_id):
    session = user_sessions.get(user_id)
    if session:
        email = session['email']
        send_message(chat_id, f"📧 Your current temp email:\n`{email}`")
    else:
        send_message(chat_id, "ℹ️ You don't have a temp email yet.")

# --- ROUTE UTAMA FLASK UNTUK WEBHOOK ---

@app.route('/', methods=['GET'])
def index():
    return 'TempMail Bot Webhook is running!', 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update_json = request.get_json()
        
        try:
            # Gunakan Update.de_json untuk mempermudah parsing data
            update = Update.de_json(update_json, None)
        except Exception:
            return jsonify({'status': 'ok'}), 200

        if update.message and update.message.text:
            text = update.message.text.strip().split()
            command = text[0].lower()
            user_id = update.message.from_user.id
            chat_id = update.message.chat_id

            # Dispatch berdasarkan perintah
            if command == '/start':
                handle_start(update, user_id, chat_id)
            elif command == '/new':
                handle_new_email(update, user_id, chat_id)
            elif command == '/inbox':
                handle_inbox(update, user_id, chat_id)
            elif command == '/delete':
                handle_delete_email(update, user_id, chat_id)
            elif command == '/info':
                handle_info(update, user_id, chat_id)
            
    return jsonify({'status': 'ok'}), 200

# --- PENGATURAN WEBHOOK DAN RUN FLASK ---

if __name__ == '__main__':
    # Pastikan Anda telah mengatur webhook ke URL publik HTTPS Anda
    app.run(debug=True)
