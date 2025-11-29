import telebot
import time

# GANTI DENGAN TOKEN BOT ANDA
BOT_TOKEN = '8141275674:AAEq1WodTyoi_D54hF5dsOs_xFps40zc8xc'
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "✅ BOT TEST BERHASIL! Jika Anda melihat ini, koneksi Telegram Anda OK.")

print("Memulai koneksi Telegram Polling...")

while True:
    try:
        # Menjalankan polling. Jika ini berhasil, masalahnya ada di Flask/threading
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        # Jika terjadi error (biasanya koneksi), coba lagi
        print(f"Error Polling: {e}. Mencoba lagi dalam 15 detik...")
        time.sleep(15)
