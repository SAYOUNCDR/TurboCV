import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import utils
import json

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
DOWNLOAD_CALLBACK = "download_improved_resume"


def command_overview() -> str:
    return (
        "Available commands:\n"
        "/start - Show welcome message and current status\n"
        "/help - Show commands and supported formats\n"
        "/jd - Attach or paste the job description first\n"
        "/resume - Attach or paste the resume after JD\n"
        "/cancel - Reset the current intake step"
    )


def format_overview() -> str:
    return (
        "Accepted formats:\n"
        f"JD: {SUPPORTED_JD_FORMATS}\n"
        f"Resume: {SUPPORTED_RESUME_FORMATS}"
    )


def user_status(context: ContextTypes.DEFAULT_TYPE) -> str:
    jd_ready = "attached" if context.user_data.get("jd_text") else "missing"
    resume_ready = "attached" if context.user_data.get("resume_text") else "missing"
    return f"Current status:\nJD: {jd_ready}\nResume: {resume_ready}"


# Constants for conversation states
JD_STATE, RESUME_STATE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the Job Description."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    await update.message.reply_text(
        f"{command_overview()}\n\n{format_overview()}\n\n{user_status(context)}"
    )


async def handle_jd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the JD and asks for the Resume."""
    jd_text = update.message.text
    context.user_data["jd_text"] = jd_text

    await update.message.reply_text(
        "JD is already attached.\n"
        "Send /resume when you are ready to upload or paste the resume.\n"
        "You can also ask me general career questions here."
    )


async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Downloads the resume, extracts text, analyzes it, and sends feedback."""
    user = update.message.from_user
    document = update.message.document

    # Check if document exists
    if not document:
        await update.message.reply_text(
            "Please make sure you upload a valid file (PDF/DOCX) using the attachment button."
        )
        return RESUME_STATE

    file_name = document.file_name
    # Check file extension
    if not (file_name.lower().endswith(".pdf") or file_name.lower().endswith(".docx")):
        await update.message.reply_text(
            "I only support .pdf and .docx file formats right now. Try uploading a valid document."
        )
        return RESUME_STATE

    await update.message.reply_text("Uploading your resume... ⏳")

    # Create downloads directory if it doesn't exist
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Download the file to 'downloads' directory
    file = await context.bot.get_file(document.file_id)
    file_path = os.path.join("downloads", f"{user.id}_{file_name}")
    await file.download_to_drive(file_path)

    await update.message.reply_text(
        "Analyzing your resume... please wait (this calls the AI model). 🤖"
    )

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
        if not jd_text:
            await update.message.reply_text(
                "Job Description missing. Please start over with /start."
            )
            return ConversationHandler.END

        analysis = utils.analyze_resume(resume_text, jd_text)

        # Check if analysis failed inside utils (it returns a dict with error message)
        if (
            "summary_feedback" in analysis
            and "Error analyzing" in analysis["summary_feedback"]
        ):
            # If specific error is returned
            error_msg = analysis["summary_feedback"]
            logger.error(f"Analysis Error: {error_msg}")
            await update.message.reply_text(
                f"An error occurred during AI analysis:\n{error_msg}"
            )
            return ConversationHandler.END

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
    context.user_data.clear()
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

    # Check if a custom log level for httpx is needed to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
