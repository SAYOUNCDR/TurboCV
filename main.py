import os
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
import utils
import json

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for conversation states
JD_STATE, RESUME_STATE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the Job Description."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    await update.message.reply_text(
        "Hi! I'm TurboCV, your AI Resume Analyzer.\n\n"
        "Let's get started. Please paste the Job Description (JD) you are applying for."
    )
    return JD_STATE


async def handle_jd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the JD and asks for the Resume."""
    jd_text = update.message.text
    context.user_data["jd_text"] = jd_text

    await update.message.reply_text(
        "Got it! Now, please upload your Resume (PDF or DOCX)."
    )
    return RESUME_STATE


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Downloads the resume, extracts text, analyzes it, and sends feedback."""
    user = update.message.from_user
    document = update.message.document

    # Create downloads directory if it doesn't exist
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    file_path = os.path.join("downloads", f"{user.id}_{document.file_name}")
    new_file = await document.get_file()
    await new_file.download_to_drive(file_path)

    await update.message.reply_text("Analyzing your resume... please wait.")

    try:
        # Extract text from resume
        resume_text = utils.extract_text(file_path)
        if not resume_text:
            await update.message.reply_text(
                "Could not extract text from the file. Please ensure it's a valid PDF or DOCX."
            )
            return ConversationHandler.END

        # Analyze using Gemini
        jd_text = context.user_data.get("jd_text")
        analysis = utils.analyze_resume(resume_text, jd_text)

        # Format the feedback
        # Ensure analysis is a dictionary even if parsing failed
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except:
                analysis = {"summary_feedback": "Error parsing AI response."}

        score = analysis.get("score", 0)
        summary = analysis.get("summary_feedback", "No summary available.")
        missing_keywords = analysis.get("missing_keywords", [])
        improvement_tips = analysis.get("improvement_tips", [])

        feedback = (
            f"*Resume Score:* {score}/100\n\n"
            f"*Summary:*\n{summary}\n\n"
            f"*Missing Keywords:*\n- " + "\n- ".join(missing_keywords) + "\n\n"
            f"*Improvement Tips:*\n- " + "\n- ".join(improvement_tips)
        )

        await update.message.reply_text(feedback, parse_mode="Markdown")

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error("Error during analysis: %s", e)
        await update.message.reply_text(
            f"Sorry, something went wrong while analyzing your resume.\nError details: {str(e)}"
        )
    finally:
        # Clean up the downloaded file
        if os.path.exists(file_path):
            os.remove(file_path)

    await update.message.reply_text("Send /start to analyze another resume.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled. Send /start to try again.")
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            JD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_jd)],
            RESUME_STATE: [MessageHandler(filters.Document.ALL, handle_resume)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
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
    context.user_data["jd"] = jd_text

    await update.message.reply_text(
        "✅ Got the Job Description!\n\n"
        "Now, please upload your **Resume** document in PDF or DOCX format."
    )
    return RESUME_STATE


async def receive_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the Resume, validates the format, saves it, and indicates next steps."""
    document = update.message.document
    if not document:
        await update.message.reply_text(
            "Please make sure you upload a valid file (PDF/DOCX) using the attachment button."
        )
        return RESUME_STATE

    file_name = document.file_name
    if not (file_name.endswith(".pdf") or file_name.endswith(".docx")):
        await update.message.reply_text(
            "I only support .pdf and .docx file formats right now. Try uploading a valid document."
        )
        return RESUME_STATE

    await update.message.reply_text("Uploading your resume... ⏳")

    # Ensure the downloads directory exists
    os.makedirs("downloads", exist_ok=True)

    # Download the file to 'downloads' directory
    file = await context.bot.get_file(document.file_id)
    file_path = f"downloads/{document.file_id}_{file_name}"
    await file.download_to_drive(file_path)

    try:
        await update.message.reply_text(
            f"File `{file_name}` saved successfully!\n\nBeginning analysis phase... (AI Processing steps coming soon!)"
        )

        # Placeholder for extraction and AI logic
        # jd_text = context.user_data.get('jd')
        # extracted_text = utils.extract_text(file_path)
        # analysis_result = utils.analyze_with_free_ai(extracted_text, jd_text)

    except Exception as e:
        logger.error(f"Error handling file: {e}")
        await update.message.reply_text(
            "An error occurred during processing. Please try again later."
        )

    finally:
        # For a production app, we would clean up the downloaded file here.
        # But for development, leaving it can be helpful for debugging.
        pass

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation state machine entirely."""
    await update.message.reply_text(
        "Process canceled. Use /start whenever you want to begin a new analysis."
    )
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Main function initializing and running the bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided. Please check your .env file.")
        print(
            "CRITICAL: You must provide a valid Telegram Bot token in your .env file!"
        )
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
