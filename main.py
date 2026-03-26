import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Reduce the noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# State definitions for the conversation
JD_STATE, RESUME_STATE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and prompts the user for the Job Description."""
    await update.message.reply_text(
        "👋 Welcome to the **Free Resume AI Analyzer**!\n\n"
        "To get started, please paste the **Job Description (JD)** that you want your resume evaluated against."
    )
    return JD_STATE

async def receive_jd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the Job Description text and asks for the Resume file."""
    jd_text = update.message.text
    context.user_data['jd'] = jd_text
    
    await update.message.reply_text(
        "✅ Got the Job Description!\n\n"
        "Now, please upload your **Resume** document in PDF or DOCX format."
    )
    return RESUME_STATE

async def receive_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the Resume, validates the format, saves it, and indicates next steps."""
    document = update.message.document
    if not document:
        await update.message.reply_text("Please make sure you upload a valid file (PDF/DOCX) using the attachment button.")
        return RESUME_STATE
    
    file_name = document.file_name
    if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
        await update.message.reply_text("I only support .pdf and .docx file formats right now. Try uploading a valid document.")
        return RESUME_STATE
        
    await update.message.reply_text("Uploading your resume... ⏳")
    
    # Ensure the downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Download the file to 'downloads' directory
    file = await context.bot.get_file(document.file_id)
    file_path = f"downloads/{document.file_id}_{file_name}"
    await file.download_to_drive(file_path)
    
    try:
        await update.message.reply_text(f"File `{file_name}` saved successfully!\n\nBeginning analysis phase... (AI Processing steps coming soon!)")
        
        # Placeholder for extraction and AI logic
        # jd_text = context.user_data.get('jd')
        # extracted_text = utils.extract_text(file_path)
        # analysis_result = utils.analyze_with_free_ai(extracted_text, jd_text)
        
    except Exception as e:
        logger.error(f"Error handling file: {e}")
        await update.message.reply_text("An error occurred during processing. Please try again later.")
        
    finally:
        # For a production app, we would clean up the downloaded file here.
        # But for development, leaving it can be helpful for debugging.
        pass
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation state machine entirely."""
    await update.message.reply_text("Process canceled. Use /start whenever you want to begin a new analysis.")
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    """Main function initializing and running the bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided. Please check your .env file.")
        print("CRITICAL: You must provide a valid Telegram Bot token in your .env file!")
        return
        
    # Build application
    application = Application.builder().token(token).build()

    # Create the conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            JD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_jd)],
            RESUME_STATE: [MessageHandler(filters.Document.ALL, receive_resume)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Register handlers
    application.add_handler(conv_handler)
    
    # Start polling
    logger.info("Bot is polling and ready for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
