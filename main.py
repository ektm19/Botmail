from flask import Flask
from threading import Thread
import telebot
import requests
import json
import os
import random
import string

app = Flask(__name__)
# Ganti dengan token bot Anda yang BENAR
bot = telebot.TeleBot('8271421272:AAHDcwdsveSmwKVXvqAHn4VpdKSpXH37cG4')
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
        response = requests.get(f"{MAILTM_API_BASE}/domains")
        response.raise_for_status()
        domains = response.json().get('hydra:member', [])
        if domains:
            return domains[0]['domain']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching domains: {e}")
        return None

# --- Inisialisasi File Admin ---
# Pastikan direktori dan file statistik ada saat bot dijalankan
if not os.path.exists("admin"):
    os.makedirs("admin")

# File total user (diasumsikan tidak ada penambahan di fungsi start)
total_file = "admin/total.txt"
if not os.path.exists(total_file):
    with open(total_file, 'w') as f:
        f.write("0")

# File total email yang dibuat
mail_count_file = "admin/mail.txt"
if not os.path.exists(mail_count_file):
    with open(mail_count_file, 'w') as f:
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
    
    # Check dan buat file user
    if not file_exists(user_file_path):
        # NOTA: Anda perlu menyesuaikan logika penambahan total user (admin/total.txt) di sini
        # jika Anda ingin menghitung user baru
        try:
            with open(user_file_path, "w") as f:
                f.write(json.dumps({})) # Membuat file kosong atau menyimpan data dasar
            
            # Tambahkan logika untuk memperbarui admin/total.txt di sini jika diperlukan
            # usr_count = int(open(total_file).read()) + 1
            # with open(total_file, "w") as f:
            #     f.write(str(usr_count))
                
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
    
    # 1. Ambil domain
    domain = get_available_domain()
    if not domain:
        bot.send_message(user_id, "<b>Error: Tidak dapat mengambil domain Mail.tm yang tersedia.</b>", parse_mode='HTML')
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
        response = requests.post(f"{MAILTM_API_BASE}/accounts", json=payload)
        response.raise_for_status()
        
        account_data = response.json()
        
        # Simpan data penting (email, ID, dan password)
        user_mail_data = {
            "email": email_address,
            "id": account_data.get('id'),
            "password": password  # Perlu untuk login dan cek inbox
        }
        
        # 4. Simpan ke file user
        file_path = f"admin/mail{user_id}.json"
        with open(file_path, "w") as mail_file:
            mail_file.write(json.dumps(user_mail_data))

        # 5. Perbarui statistik
        h = int(open("admin/mail.txt").read()) + 1
        with open("admin/mail.txt", "w") as mail_count_file:
            mail_count_file.write(str(h))
            
        bot.send_message(user_id, f"<b>✅ Email Sementara Berhasil Dibuat!\n\n📧 Alamat: </b><code>{email_address}</code>\n\n<b>Gunakan menu '📨 Inbox' untuk memeriksa pesan.</b>", parse_mode='HTML')
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating Mail.tm account: {e}")
        error_msg = response.json().get('detail', 'Terjadi kesalahan saat membuat email.') if 'response' in locals() else 'Gagal terhubung ke API Mail.tm.'
        bot.send_message(user_id, f"<b>❌ Error occurred while generating email:\n{error_msg}</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '🚀 My Email')
def get_user_email(message):
    user_id = message.from_user.id
    file_path = f"admin/mail{user_id}.json"
    
    if file_exists(file_path):
        data = json.load(open(file_path))
        email = data.get('email')
        bot.send_message(user_id, f"<b>Your Email Is\n\n</b><code>{email}</code>", parse_mode='HTML')
    else:
        bot.send_message(user_id, "<b>❌️ No Email created. Please use '📧 Generate New Email' first.</b>", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == '📨 Inbox')
def check_inbox(message):
    user_id = message.from_user.id
    file_path = f"admin/mail{user_id}.json"
    
    if not file_exists(file_path):
        bot.send_message(user_id, "<b>⛔️ Please Generate an email first</b>", parse_mode='HTML')
        return

    data = json.load(open(file_path))
    email = data.get('email')
    password = data.get('password')
    
    # 1. Lakukan Login untuk mendapatkan Token
    login_payload = {
        "address": email,
        "password": password
    }
    
    try:
        login_response = requests.post(f"{MAILTM_API_BASE}/token", json=login_payload)
        login_response.raise_for_status()
        token = login_response.json().get('token')
        
        if not token:
            bot.send_message(user_id, "<b>❌ Gagal mendapatkan token login untuk cek inbox.</b>", parse_mode='HTML')
            return
        
        # 2. Ambil Email (Messages) menggunakan Token
        headers = {"Authorization": f"Bearer {token}"}
        # Gunakan endpoint messages untuk akun yang sedang login
        messages_response = requests.get(f"{MAILTM_API_BASE}/messages", headers=headers)
        messages_response.raise_for_status()
        
        emails = messages_response.json().get('hydra:member', [])
        
        if not emails:
            bot.send_message(user_id, "❌️ No Mail Received")
        else:
            bot.send_message(user_id, f"<b>✅ Ditemukan {len(emails)} pesan baru.</b>", parse_mode='HTML')
            
            for msg_data in emails:
                # Perlu mengambil detail pesan (body) menggunakan ID pesan
                detail_response = requests.get(f"{MAILTM_API_BASE}/messages/{msg_data['id']}", headers=headers)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                # Gunakan body_text (plain text) atau body (HTML)
                body_text = detail.get('text', 'Tidak ada konten teks.')
                
                msg = f"<b>Mail Received</b>\n\n"
                msg += f"<b>📩 From:</b> {detail.get('from', {}).get('address', 'N/A')}\n"
                msg += f"<b>📑 Subject:</b> {detail.get('subject', 'N/A')}\n\n"
                # Batasi teks agar tidak terlalu panjang
                msg += f"<b>📝 Content Preview:</b>\n{body_text[:500]}{'...' if len(body_text) > 500 else ''}"

                bot.send_message(user_id, msg, parse_mode='HTML')
                
    except requests.exceptions.RequestException as e:
        print(f"Error checking Mail.tm inbox: {e}")
        bot.send_message(user_id, "<b>❌ Terjadi Kesalahan saat mencoba mengambil inbox.</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📊  Status')
def bot_status(message):
    user_id = message.from_user.id
    
    try:
        tmail = int(open("admin/mail.txt").read())
    except FileNotFoundError:
        tmail = 0
    
    # Hitung total user dari folder admin/users
    users_directory = "admin/users/"
    try:
        usr = len([name for name in os.listdir(users_directory) if os.path.isfile(os.path.join(users_directory, name))])
    except FileNotFoundError:
        usr = 0


    img_url = "https://quickchart.io/chart?bkg=white&c={'type':'bar','data':{'labels':[''],'datasets':[{'label':'Total-Users','data':[" + str(usr) + "]},{'label':'Total-Mail Created','data':[" + str(tmail) + "]}]}}"

    caption = f"📊 Bot Live Stats 📊\n\n⚙ Total Email Generated : {tmail}\n✅️ Total Users : {usr}\n\n🔥 By: @ektm19"
    bot.send_photo(user_id, img_url, caption=caption)


@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    # Logika broadcast
    if str(message.from_user.id) == admin:
        bot.send_message(message.chat.id, "Send the message you want to broadcast to all users. ✨")
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.send_message(message.chat.id, "You are not authorized to use this command. ⛔️")


def send_broadcast(message):
    # Logika pengiriman broadcast
    broadcast_text = message.text
    users_directory = "admin/users/"
    try:
        user_ids = [file.split('.')[0] for file in os.listdir(users_directory) if file.endswith('.json')]
    except FileNotFoundError:
        user_ids = []

    for user_id in user_ids:
        try:
            # Periksa apakah ID valid sebelum mengirim
            if user_id.isdigit():
                 bot.send_message(user_id, broadcast_text)
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {e}")

    bot.send_message(admin, f"Broadcast sent to {len(user_ids)} users! 📣")


# --- Flask Server dan Keep Alive ---

@app.route('/')
def index():
    return "Alive"

def run():
    # Menjalankan Flask
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080)) # Gunakan variabel lingkungan PORT jika tersedia

def keep_alive():
    t = Thread(target=run)
    t.start()


if __name__ == '__main__':
    keep_alive()
    # Memulai bot polling
    print("Bot is starting polling...")
    bot.polling(none_stop=True)
