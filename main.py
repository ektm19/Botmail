import os
from flask import Flask, request, jsonify
from telegram import Bot, Update

# --- Konfigurasi ---
# GANTI INI: Token Bot Anda
BOT_TOKEN = "8271421272:AAHDcwdsveSmwKVXvqAH4VpdKSpXH37cG4" 
# GANTI INI: URL publik dari aplikasi Anda (diperlukan untuk Webhook)
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE", "https://api.telegram.org/bot8271421272:AAHDcwdsveSmwKVXvqAHn4VpdKSpXH37cG4")
# Path unik untuk endpoint Webhook
WEBHOOK_PATH = f"/{BOT_TOKEN}" 

app = Flask(__name__)
bot = Bot(BOT_TOKEN)

# --- Fungsi Handler Logika Bot ---

def handle_telegram_update(update):
    """Memproses pembaruan yang diterima dan mengirim balasan."""
    if update.message:
        text = update.message.text
        chat_id = update.message.chat_id
        
        # Logika Balasan
        if text and text.startswith('/start'):
            reply = "Halo! Saya adalah bot Webhook. Kirim pesan apa pun untuk balasan otomatis."
        elif text:
            reply = f"Anda mengirim: '{text}'. Terima kasih, Webhook berhasil!"
        else:
            reply = "Saya menerima pembaruan tanpa teks yang jelas."

        # Mengirim balasan kembali ke Telegram
        bot.send_message(chat_id=chat_id, text=reply)

# --- Endpoint Flask ---

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook_receiver():
    """Endpoint yang menerima data POST (Update) dari server Telegram."""
    if request.method == "POST":
        json_data = request.get_json(force=True)
        try:
            # Mengubah JSON menjadi objek Update Telegram
            update = Update.de_json(json_data, bot)
            handle_telegram_update(update)
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            # Menghindari crash dan memberikan respon 200 agar Telegram tidak terus mencoba
            print(f"Error processing update: {e}")
            return jsonify({"status": "error", "message": str(e)}), 200
    
    return "Method Not Allowed", 405

@app.route('/set_webhook')
def set_webhook():
    """Endpoint untuk mengatur Webhook di server Telegram (perlu diakses sekali)."""
    full_webhook_url = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}"
    s = bot.setWebhook(full_webhook_url)
    
    if s:
        return f"✅ Webhook Berhasil Diatur ke: **{full_webhook_url}**"
    else:
        return "❌ Webhook GAGAL diatur. Periksa URL publik Anda."

@app.route('/')
def index():
    return 'Bot Webhook sedang berjalan.'

if __name__ == '__main__':
    # Pastikan URL publik diatur! Gunakan Ngrok atau Heroku untuk menguji secara publik.
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
