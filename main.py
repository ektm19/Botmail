from flask import Flask
from threading import Thread
import telebot
import requests
import json
import os
import random
import string
import time # Tambahkan modul time untuk sleep

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
    """Menghasilkan string acak untuk username/password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def get_available_domain():
    """Mengambil domain pertama yang tersedia dari Mail.tm."""
    try:
        # Menambahkan timeout untuk keandalan
        response = requests.get(f"{MAILTM_API_BASE}/domains", timeout=10) 
        response.raise_for_status() 
        
        data = response.json()
        domains = data.get('hydra:member', [])
        
        if domains:
            return domains[0]['domain']
        
        print("Mail.tm API: Tidak ada domain yang ditemukan dalam respons.")
        return None
        
    except requests.exceptions.Timeout:
        print("Mail.tm API: Permintaan Timeout saat mengambil domain.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Mail.tm API: Error saat mengambil domain: {e}")
        return None

# --- Inisialisasi File Admin ---

# Pastikan semua folder dan file statistik ada
if not os.path.exists("admin"):
    os.makedirs("admin")

files_to_check = ["admin/total.txt", "admin/mail.txt"]
for total_file in files_to_check:
    if not os.path.exists(total_file):
        with open(total_file, 'w') as f:
            f.write("0")

# --- Telegram Handlers ---

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
    
    payload = {
        "address": email_address,
        "password": password
    }

    try:
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload, timeout=10)
        response.raise_for_status()
        
        account_data = response.json()
        
        user_mail_data = {
            "email": email_address,
            "id": account_data.get('id'),
            "password": password 
        }
        
        file_path = f"admin/mail{user_id}.json"
        with open(file_path, "w") as mail_file:
            mail_file.write(json.dumps(user_mail_data))

        # Perbarui statistik
        try:
            with open("admin/mail.txt", "r+") as mail_count_file:
                # Baca, hitung, dan tulis ulang
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
        bot.send_message(user_id, "<b>❌ Error: Data email tidak valid. Cobafrom flask import Flask </b>")
from threading import Thread
import telebot
import requests
import json
import os
import random
import string
import time # Tambahkan modul time untuk sleep

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
    """Menghasilkan string acak untuk username/password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def get_available_domain():
    """Mengambil domain pertama yang tersedia dari Mail.tm."""
    try:
        # Menambahkan timeout untuk keandalan
        response = requests.get(f"{MAILTM_API_BASE}/domains", timeout=10) 
        response.raise_for_status() 
        
        data = response.json()
        domains = data.get('hydra:member', [])
        
        if domains:
            return domains[0]['domain']
        
        print("Mail.tm API: Tidak ada domain yang ditemukan dalam respons.")
        return None
        
    except requests.exceptions.Timeout:
        print("Mail.tm API: Permintaan Timeout saat mengambil domain.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Mail.tm API: Error saat mengambil domain: {e}")
        return None

# --- Inisialisasi File Admin ---

# Pastikan semua folder dan file statistik ada
if not os.path.exists("admin"):
    os.makedirs("admin")

files_to_check = ["admin/total.txt", "admin/mail.txt"]
for total_file in files_to_check:
    if not os.path.exists(total_file):
        with open(total_file, 'w') as f:
            f.write("0")

# --- Telegram Handlers ---

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
    
    payload = {
        "address": email_address,
        "password": password
    }

    try:
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload, timeout=10)
        response.raise_for_status()
        
        account_data = response.json()
        
        user_mail_data = {
            "email": email_address,
            "id": account_data.get('id'),
            "password": password 
        }
        
        file_path = f"admin/mail{user_id}.json"
        with open(file_path, "w") as mail_file:
            mail_file.write(json.dumps(user_mail_data))

        # Perbarui statistik
        try:
            with open("admin/mail.txt", "r+") as mail_count_file:
                # Baca, hitung, dan tulis ulang
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
        bot.send_message(user_id, "<b>❌ Error: Data email tidak valid. Coba
