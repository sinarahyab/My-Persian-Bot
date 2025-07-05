import os
import logging
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import whisper
import ffmpeg

# تنظیمات ربات
TOKEN = os.getenv("TELEGRAM_TOKEN")  # توکن را در تنظیمات رازها قرار دهید
MAX_SIZE = 2000 * 1024 * 1024  # 2 گیگابایت

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # دریافت فایل
        file = await update.message.effective_attachment.get_file()
        
        if file.file_size > MAX_SIZE:
            await update.message.reply_text("❌ حجم فایل بیش از ۲ گیگابایت است!")
            return
            
        await update.message.reply_text("⏳ فایل دریافت شد. پردازش آغاز شد...")
        
        # دانلود فایل موقت
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            await file.download_to_drive(tmp_file.name)
            input_path = tmp_file.name
        
        # تبدیل به صوت
        audio_path = f"{input_path}.wav"
        (
            ffmpeg.input(input_path)
            .output(audio_path, ar=16000, ac=1)
            .run(overwrite_output=True, quiet=True)
        )
        
        # تشخیص گفتار
        model = whisper.load_model("medium")
        result = model.transcribe(audio_path, language="fa", task="transcribe")
        transcript = result["text"]
        
        # ویرایش متن
        edited_text = f"📝 متن استخراج شده:\n\n{transcript}\n\n✅ پردازش کامل شد!"
        
        # ارسال نتیجه
        await update.message.reply_text(edited_text)
        
        # پاک‌سازی فایل‌های موقت
        os.unlink(input_path)
        os.unlink(audio_path)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"⚠️ خطا در پردازش: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # افزودن هندلر برای انواع فایل‌های رسانه‌ای
    media_filter = filters.VIDEO | filters.AUDIO | filters.Document.VIDEO | filters.Document.AUDIO
    app.add_handler(MessageHandler(media_filter, handle_media))
    
    app.run_polling()

if __name__ == "__main__":
    main()
