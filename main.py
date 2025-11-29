from flask import Flask
from threading import Thread
import telebot
import requests
import json
import os
import random
import string
import time # Dipertahankan untuk sleep

# --- Konfigurasi ---
app = Flask(__name__)
# Ganti dengan token bot Anda yang BENAR
bot = telebot.TeleBot('8141275674:AAEq1WodTyoi_D54hF5dsOs_xFps40zc8xc')
admin = "1188483395"

# --- Konfigurasi Mail.tm ---
MAILTM_API_BASE = "https://api.mail.tm"

# --- Fungsi Helper ---

def file_exists(file_path):
    return os.path.exists(file_path)

def get_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def get_available_domain():
    """Mengambil domain pertama yang tersedia dari Mail.tm."""
    try:
        response = requests.get(f"{MAILTM_API_BASE}/domains", timeout=10) 
        response.raise_for_status() 
        data = response.json()
        domains = data.get('hydra:member', [])
        if domains:
            return domains[0]['domain']
        print("Mail.tm API: Tidak ada domain yang ditemukan dalam respons.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Mail.tm API: Error saat mengambil domain: {e}")
        return None

# --- Inisialisasi File Admin (Dijalankan Saat Start) ---

if not os.path.exists("admin"):
    os.makedirs("admin")

# Menginisialisasi file statistik
for total_file in ["admin/total.txt", "admin/mail.txt"]:
    if not os.path.exists(total_file):
        with open(total_file, 'w') as f:
            f.write("0")

# --- Telegram Handlers (Tetap Sama) ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    fname = message.from_user.first_name
    
    users_directory = "admin/users/"
    if not os.path.exists(users_directory):
        os.makedirs(users_directory)

    user_file_path = f"{users_directory}{user_id}.json"
    
    if not file_exists(user_file_path):
        try:
            with open(user_file_path, "w") as f:
                f.write(json.dumps({})) 
            bot.send_message(admin, f"<b>🚀 New User Joined The Bot\n\nUser Id : {user_id}\n\nFirst Name: {fname}</b>", parse_mode='HTML')
        except Exception as e:
            print(f"Error creating user file or sending admin message: {e}")

    mess = f"<b>😀 Hey {fname} Welcome To the @{bot.get_me().username}\n\nBot Deploy By : @ektm19</b>"
    keyboard_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    keyboard_markup.row("🚀 My Email")
    keyboard_markup.row("📧 Generate New Email", "📨 Inbox")
    keyboard_markup.row("📊  Status")
    bot.send_message(user_id, mess, reply_markup=keyboard_markup, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📧 Generate New Email')
def generate_email(message):
    user_id = message.from_user.id
    
    bot.send_message(user_id, "⚙️ Mencari domain yang tersedia...")
    domain = get_available_domain()
    
    if not domain:
        bot.send_message(user_id, "<b>❌ Error: Tidak dapat mengambil domain Mail.tm yang tersedia. Coba lagi nanti.</b>", parse_mode='HTML')
        return

    username = get_random_string(10)
    password = get_random_string(12)
    email_address = f"{username}@{domain}"
    
    payload = {"address": email_address, "password": password}

    try:
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload, timeout=10)
        response.raise_for_status()
        account_data = response.json()
        
        user_mail_data = {"email": email_address, "id": account_data.get('id'), "password": password }
        
        file_path = f"admin/mail{user_id}.json"
        with open(file_path, "w") as mail_file:
            mail_file.write(json.dumps(user_mail_data))

        try:
            with open("admin/mail.txt", "r+") as mail_count_file:
                h = int(mail_count_file.read().strip() or 0) + 1
                mail_count_file.seek(0)
                mail_count_file.truncate()
                mail_count_file.write(str(h))
        except Exception as e:
            print(f"Error updating mail count file: {e}")
            
        bot.send_message(user_id, f"<b>✅ Email Sementara Berhasil Dibuat!\n\n📧 Alamat: </b><code>{email_address}</code>\n\n<b>Gunakan menu '📨 Inbox' untuk memeriksa pesan.</b>", parse_mode='HTML')
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating Mail.tm account: {e}")
        try:
            error_msg = response.json().get('detail', f"Status {response.status_code}")
        except:
            error_msg = 'Gagal terhubung ke API Mail.tm.'
            
        bot.send_message(user_id, f"<b>❌ Error occurred while generating email:\n{error_msg}</b>", parse_mode='HTML')

# --- Handlers Lainnya (My Email, Inbox, Status, Broadcast, tetap sama dengan perbaikan Mail.tm sebelumnya) ---

@bot.message_handler(func=lambda message: message.text == '🚀 My Email')
def get_user_email(message):
    user_id = message.from_user.id
    file_path = f"admin/mail{user_id}.json"
    
    if file_exists(file_path):
        try:
            data = json.load(open(file_path))
            email = data.get('email')
            bot.send_message(user_id, f"<b>Your Email Is\n\n</b><code>{email}</code>", parse_mode='HTML')
        except Exception:
             bot.send_message(user_id, "<b>❌️ Data email rusak. Coba buat email baru.</b>", parse_mode='HTML')
    else:
        bot.send_message(user_id, "<b>❌️ No Email created. Please use '📧 Generate New Email' first.</b>", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == '📨 Inbox')
def check_inbox(message):
    user_id = message.from_user.id
    file_path = f"admin/mail{user_id}.json"
    
    if not file_exists(file_path):
        bot.send_message(user_id, "<b>⛔️ Please Generate an email first</b>", parse_mode='HTML')
        return

    try:
        data = json.load(open(file_path))
        email = data.get('email')
        password = data.get('password')
    except Exception:
        bot.send_message(user_id, "<b>❌ Error: Data email tidak valid. Coba buat email baru.</b>", parse_mode='HTML')
        return
        
    if not email or not password:
        bot.send_message(user_id, "<b>❌ Error: Data login email tidak lengkap. Coba buat email baru.</b>", parse_mode='HTML')
        return
    
    bot.send_message(user_id, "🔎 Mencoba login dan memeriksa inbox...")
    
    login_payload = {"address": email, "password": password}
    
    try:
        login_response = requests.post(f"{MAILTM_API_BASE}/token", json=login_payload, timeout=10)
        login_response.raise_for_status()
        token = login_response.json().get('token')
        
        if not token:
            bot.send_message(user_id, "<b>❌ Gagal mendapatkan token login (Mail.tm).</b>", parse_mode='HTML')
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        messages_response = requests.get(f"{MAILTM_API_BASE}/messages", headers=headers, timeout=10)
        messages_response.raise_for_status()
        
        emails = messages_response.json().get('hydra:member', [])
        
        if not emails:
            bot.send_message(user_id, "❌️ No Mail Received")
        else:
            bot.send_message(user_id, f"<b>✅ Ditemukan {len(emails)} pesan baru.</b>", parse_mode='HTML')
            
            for msg_data in emails:
                detail_response = requests.get(f"{MAILTM_API_BASE}/messages/{msg_data['id']}", headers=headers, timeout=10)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                body_text = detail.get('text', 'Tidak ada konten teks.')
                
                msg = f"<b>Mail Received</b>\n\n"
                msg += f"<b>📩 From:</b> {detail.get('from', {}).get('address', 'N/A')}\n"
                msg += f"<b>📑 Subject:</b> {detail.get('subject', 'N/A')}\n\n"
                
                preview = body_text.strip()
                msg += f"<b>📝 Content Preview:</b>\n{preview[:500]}{'...' if len(preview) > 500 else ''}"

                bot.send_message(user_id, msg, parse_mode='HTML')
                
    except requests.exceptions.RequestException as e:
        print(f"Error checking Mail.tm inbox: {e}")
        bot.send_message(user_id, "<b>❌ Terjadi Kesalahan saat mencoba mengambil inbox. Cek koneksi Anda.</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📊  Status')
def bot_status(message):
    user_id = message.from_user.id
    
    try:
        tmail = int(open("admin/mail.txt").read())
    except Exception:
        tmail = 0
    
    users_directory = "admin/users/"
    try:
        usr = len([name for name in os.listdir(users_directory) if name.endswith('.json')])
    except FileNotFoundError:
        usr = 0

    img_url = "https://quickchart.io/chart?bkg=white&c={'type':'bar','data':{'labels':[''],'datasets':[{'label':'Total-Users','data':[" + str(usr) + "]},{'label':'Total-Mail Created','data':[" + str(tmail) + "]}]}}"
    caption = f"📊 Bot Live Stats 📊\n\n⚙ Total Email Generated : {tmail}\n✅️ Total Users : {usr}\n\n🔥 By: @ektm19"
    bot.send_photo(user_id, img_url, caption=caption)


@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if str(message.from_user.id) == admin:
        bot.send_message(message.chat.id, "Send the message you want to broadcast to all users. ✨")
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.send_message(message.chat.id, "You are not authorized to use this command. ⛔️")


def send_broadcast(message):
    broadcast_text = message.text
    users_directory = "admin/users/"
    try:
        user_ids = [file.split('.')[0] for file in os.listdir(users_directory) if file.endswith('.json')]
    except FileNotFoundError:
        user_ids = []

    for user_id in user_ids:
        try:
            if user_id.isdigit():
                 bot.send_message(user_id, broadcast_text)
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {e}")

    bot.send_message(admin, f"Broadcast sent to {len(user_ids)} users! 📣")

# --- Flask Server dan Bot Polling Stabilization ---

@app.route('/')
def index():
    return "Alive"

def start_bot_polling():
    """Menjalankan bot polling dengan mekanisme retry."""
    while True:
        try:
            print("Bot Polling dimulai...")
            bot.polling(none_stop=True, interval=0, timeout=20) 
        except Exception as e:
            # Error saat koneksi terputus, coba lagi setelah jeda
            print(f"Bot Polling Error, mencoba lagi dalam 15 detik: {e}")
            time.sleep(15) 

def run_flask_app():
    """Menjalankan aplikasi Flask."""
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080)) 

# Fungsi utama untuk menjalankan Flask dan Bot Polling secara bersamaan
if __name__ == '__main__':
    # 1. Jalankan Bot Polling di Thread terpisah
    bot_thread = Thread(target=start_bot_polling)
    # Penting: Daemon=True agar thread berhenti ketika main
