from flask import Flask
from threading import Thread
import telebot
import requests
import json
import os
import random
import string

# --- Konfigurasi ---
# ... (konfigurasi bot dan admin lainnya) ...
bot = telebot.TeleBot('8141275674:AAEq1WodTyoi_D54hF5dsOs_xFps40zc8xc')
admin = "1188483395"

# --- Konfigurasi Mail.tm ---
MAILTM_API_BASE = "https://api.mail.tm"

# --- Fungsi Helper ---

# ... (file_exists dan get_random_string tetap sama) ...

def get_random_string(length):
    """Menghasilkan string acak untuk username/password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def get_available_domain():
    """Mengambil domain pertama yang tersedia dari Mail.tm."""
    # Menambahkan timeout dan error handling yang lebih baik
    try:
        response = requests.get(f"{MAILTM_API_BASE}/domains", timeout=10) 
        response.raise_for_status() # Akan melempar HTTPError untuk status 4xx/5xx
        
        data = response.json()
        domains = data.get('hydra:member', [])
        
        if domains:
            # Mengambil domain pertama
            return domains[0]['domain']
        
        print("Mail.tm API: Tidak ada domain yang ditemukan dalam respons.")
        return None
        
    except requests.exceptions.Timeout:
        print("Mail.tm API: Permintaan Timeout saat mengambil domain.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Mail.tm API: Error saat mengambil domain: {e}")
        return None

# ... (fungsi inisialisasi file admin dan handle_start tetap sama) ...

@bot.message_handler(func=lambda message: message.text == '📧 Generate New Email')
def generate_email(message):
    user_id = message.from_user.id
    
    # 1. Ambil domain
    bot.send_message(user_id, "⚙️ Mencari domain yang tersedia...")
    domain = get_available_domain()
    
    if not domain:
        bot.send_message(user_id, "<b>❌ Error: Tidak dapat mengambil domain Mail.tm yang tersedia. Coba lagi nanti.</b>", parse_mode='HTML')
        return

    # 2. Buat data akun
    username = get_random_string(10)
    password = get_random_string(12)
    email_address = f"{username}@{domain}"
    
    payload = {
        "address": email_address,
        "password": password
    }

    # 3. Kirim permintaan pembuatan akun ke Mail.tm
    try:
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload, timeout=10)
        response.raise_for_status()
        
        account_data = response.json()
        
        # Simpan data penting (email, ID, dan password)
        user_mail_data = {
            "email": email_address,
            "id": account_data.get('id'),
            "password": password
        }
        
        # 4. Simpan ke file user
        file_path = f"admin/mail{user_id}.json"
        with open(file_path, "w") as mail_file:
            mail_file.write(json.dumps(user_mail_data))

        # 5. Perbarui statistik
        # Menggunakan pengecekan file yang lebih aman
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
        # Ambil detail error jika tersedia
        try:
            error_msg = response.json().get('detail', f"Status {response.status_code}")
        except:
            error_msg = 'Gagal terhubung ke API Mail.tm.'
            
        bot.send_message(user_id, f"<b>❌ Error occurred while generating email:\n{error_msg}</b>", parse_mode='HTML')

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
    except Exception as e:
        bot.send_message(user_id, "<b>❌ Error: Data email tidak valid. Coba buat email baru.</b>", parse_mode='HTML')
        return
        
    if not email or not password:
        bot.send_message(user_id, "<b>❌ Error: Data login email tidak lengkap. Coba buat email baru.</b>", parse_mode='HTML')
        return
    
    bot.send_message(user_id, "🔎 Mencoba login dan memeriksa inbox...")
    
    # 1. Lakukan Login untuk mendapatkan Token
    login_payload = {
        "address": email,
        "password": password
    }
    
    try:
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
            bot.send_message(user_id, "❌️ No Mail Received")
        else:
            bot.send_message(user_id, f"<b>✅ Ditemukan {len(emails)} pesan baru.</b>", parse_mode='HTML')
            
            for msg_data in emails:
                # 3. Ambil detail pesan
                detail_response = requests.get(f"{MAILTM_API_BASE}/messages/{msg_data['id']}", headers=headers, timeout=10)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                body_text = detail.get('text', 'Tidak ada konten teks.')
                
                msg = f"<b>Mail Received</b>\n\n"
                msg += f"<b>📩 From:</b> {detail.get('from', {}).get('address', 'N/A')}\n"
                msg += f"<b>📑 Subject:</b> {detail.get('subject', 'N/A')}\n\n"
                # Batasi teks
                preview = body_text.strip()
                msg += f"<b>📝 Content Preview:</b>\n{preview[:500]}{'...' if len(preview) > 500 else ''}"

                bot.send_message(user_id, msg, parse_mode='HTML')
                
    except requests.exceptions.RequestException as e:
        print(f"Error checking Mail.tm inbox: {e}")
        bot.send_message(user_id, "<b>❌ Terjadi Kesalahan saat mencoba mengambil inbox. Cek koneksi Anda.</b>", parse_mode='HTML')

# ... (bagian lain dari kode seperti My Email, Status, Broadcast, dan Flask Server tetap sama) ...
