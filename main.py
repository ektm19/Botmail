import telebot
import requests
import json
import os
import random
import string
import time

# --- 1. KONFIGURASI DAN INISIALISASI ---

# GANTI INI dengan Token Bot Anda yang Benar
BOT_TOKEN = '7343856291:AAHWR8oPdtmI_yc4u6OCOHugz_5rPVd7oAU'
bot = telebot.TeleBot(BOT_TOKEN)

MAILTM_API_BASE = "https://api.mail.tm"
# File penyimpanan data email (Ganti dengan path sesuai kebutuhan Anda)
# Kami akan menyimpan data email per user di sini untuk kesederhanaan
USER_DATA_FILE = "user_mail_data.json" 

# Memuat data email yang disimpan (jika ada)
if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'r') as f:
        USER_MAIL_DATA = json.load(f)
else:
    USER_MAIL_DATA = {}

def save_data():
    """Menyimpan data email pengguna ke file."""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(USER_MAIL_DATA, f, indent=4)

# --- 2. FUNGSI MAIL.TM CORE ---

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
        domains = response.json().get('hydra:member', [])
        if domains:
            return domains[0]['domain']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching domains: {e}")
        return None

# --- 3. TELEGRAM HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    fname = message.from_user.first_name
    
    mess = f"<b>Halo {fname}! Saya adalah bot email sementara sederhana (Mail.tm).</b>"
    
    keyboard_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    keyboard_markup.row("📧 Buat Email Baru")
    keyboard_markup.row("📨 Cek Inbox", "🚀 Email Saya")
    
    bot.send_message(user_id, mess, reply_markup=keyboard_markup, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📧 Buat Email Baru')
def generate_email(message):
    user_id = str(message.from_user.id)
    
    bot.send_message(user_id, "⚙️ Mencari domain dan membuat akun...")
    
    domain = get_available_domain()
    if not domain:
        bot.send_message(user_id, "<b>❌ Error: Tidak dapat mengambil domain Mail.tm.</b>", parse_mode='HTML')
        return

    username = get_random_string(10)
    password = get_random_string(12) # Password diperlukan untuk login cek inbox
    email_address = f"{username}@{domain}"
    
    payload = {"address": email_address, "password": password}

    try:
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload, timeout=10)
        response.raise_for_status()
        
        account_data = response.json()
        
        # Simpan data di memori (dan ke file)
        USER_MAIL_DATA[user_id] = {
            "email": email_address,
            "id": account_data.get('id'),
            "password": password
        }
        save_data() # Simpan data setelah update
            
        bot.send_message(user_id, f"<b>✅ Email Sementara Berhasil Dibuat!</b>\n\n📧 <b>Alamat: </b><code>{email_address}</code>\n\n*Alamat ini valid untuk 1 jam atau lebih.", parse_mode='HTML')
        
    except requests.exceptions.RequestException as e:
        error_msg = response.json().get('detail', 'Gagal membuat email.') if 'response' in locals() else 'Gagal koneksi ke API.'
        bot.send_message(user_id, f"<b>❌ Error: {error_msg}</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '🚀 Email Saya')
def get_user_email(message):
    user_id = str(message.from_user.id)
    
    if user_id in USER_MAIL_DATA:
        email = USER_MAIL_DATA[user_id].get('email')
        bot.send_message(user_id, f"<b>Email Anda Saat Ini:\n\n</b><code>{email}</code>", parse_mode='HTML')
    else:
        bot.send_message(user_id, "<b>❌️ Belum ada email yang dibuat.</b>", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == '📨 Cek Inbox')
def check_inbox(message):
    user_id = str(message.from_user.id)
    
    if user_id not in USER_MAIL_DATA:
        bot.send_message(user_id, "<b>⛔️ Silakan buat email terlebih dahulu.</b>", parse_mode='HTML')
        return

    data = USER_MAIL_DATA[user_id]
    email = data.get('email')
    password = data.get('password')
        
    bot.send_message(user_id, "🔎 Mencoba login dan memeriksa inbox...")
    
    login_payload = {"address": email, "password": password}
    
    try:
        # 1. Login untuk mendapatkan Token
        login_response = requests.post(f"{MAILTM_API_BASE}/token", json=login_payload, timeout=10)
        login_response.raise_for_status()
        token = login_response.json().get('token')
        
        if not token:
            bot.send_message(user_id, "<b>❌ Gagal mendapatkan token login (Mail.tm).</b>", parse_mode='HTML')
            return
        
        # 2. Ambil Email (Messages) menggunakan Token
        headers = {"Authorization": f"Bearer {token}"}
        messages_response = requests.get(f"{MAILTM_API_BASE}/messages", headers=headers, timeout=10)
        messages_response.raise_for_status()
        
        emails = messages_response.json().get('hydra:member', [])
        
        if not emails:
            bot.send_message(user_id, "❌️ Tidak ada email baru yang diterima.")
        else:
            bot.send_message(user_id, f"<b>✅ Ditemukan {len(emails)} pesan baru.</b>", parse_mode='HTML')
            
            for msg_data in emails:
                # 3. Ambil detail pesan
                detail_response = requests.get(f"{MAILTM_API_BASE}/messages/{msg_data['id']}", headers=headers, timeout=10)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                body_text = detail.get('text', 'Tidak ada konten teks.')
                
                msg = f"<b>Mail Received</b>\n\n"
                msg += f"<b>📩 Dari:</b> {detail.get('from', {}).get('address', 'N/A')}\n"
                msg += f"<b>📑 Subjek:</b> {detail.get('subject', 'N/A')}\n\n"
                
                preview = body_text.strip()
                # Batasi preview konten
                msg += f"<b>📝 Preview:</b>\n{preview[:300]}{'...' if len(preview) > 300 else ''}"

                bot.send_message(user_id, msg, parse_mode='HTML')
                
    except requests.exceptions.RequestException as e:
        print(f"Error checking Mail.tm inbox: {e}")
        bot.send_message(user_id, "<b>❌ Terjadi Kesalahan saat memeriksa inbox.</b>", parse_mode='HTML')


# --- 4. START POLLING BOT ---

if __name__ == '__main__':
    print("Bot Polling dimulai...")
    # Polling dijalankan dalam loop tak terbatas dengan error handling
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            # Jeda sebentar sebelum mencoba lagi setelah error (misalnya koneksi terputus)
            print(f"Bot Polling Error: {e}. Mencoba lagi dalam 15 detik.")
            time.sleep(15)
