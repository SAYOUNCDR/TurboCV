import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from utils import (
    SUPPORTED_JD_FORMATS,
    SUPPORTED_RESUME_FORMATS,
    analyze_resume_against_jd,
    answer_general_query,
    extract_jd_text,
    extract_resume_text,
    generated_output_dir,
    infer_extension,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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


def set_waiting_state(
    context: ContextTypes.DEFAULT_TYPE,
    jd: bool = False,
    resume: bool = False,
) -> None:
    context.user_data["awaiting_jd"] = jd
    context.user_data["awaiting_resume"] = resume


def looks_like_general_query(message_text: str) -> bool:
    lowered = message_text.strip().lower()
    if not lowered:
        return False

    question_starters = (
        "what",
        "which",
        "who",
        "where",
        "when",
        "why",
        "how",
        "can",
        "could",
        "should",
        "would",
        "do",
        "does",
        "is",
        "are",
        "am",
        "will",
        "suggest",
        "recommend",
        "tell me",
        "help me",
    )
    if lowered.endswith("?"):
        return True
    if any(lowered.startswith(starter) for starter in question_starters):
        return len(lowered) <= 400
    return False


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show welcome message"),
            BotCommand("help", "Show commands and supported formats"),
            BotCommand("jd", "Attach or paste the job description"),
            BotCommand("resume", "Attach or paste the resume"),
            BotCommand("cancel", "Cancel the current intake step"),
        ]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_waiting_state(context)
    message = (
        "TurboCV is ready.\n\n"
        f"{command_overview()}\n\n"
        f"{format_overview()}\n\n"
        "Start by sending /jd to attach the job description."
    )
    await update.message.reply_text(f"{message}\n\n{user_status(context)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"{command_overview()}\n\n{format_overview()}\n\n{user_status(context)}"
    )


async def jd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_waiting_state(context, jd=True, resume=False)
    await update.message.reply_text(
        "Send the job description now.\n\n"
        "You can attach it as pasted text or as a screenshot/image file.\n"
        f"{format_overview()}"
    )


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("jd_text"):
        await update.message.reply_text(
            "You have not attached the JD yet.\n"
            "Please send /jd first, then attach the job description."
        )
        return

    set_waiting_state(context, jd=False, resume=True)
    await update.message.reply_text(
        "Send the resume now.\n\n"
        "You can paste resume text or upload a document.\n"
        f"{format_overview()}"
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_waiting_state(context)
    await update.message.reply_text(
        "Current intake step canceled.\n"
        "Use /jd to attach a job description or /resume to continue with the saved JD."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = (update.message.text or "").strip()
    if not message_text:
        return

    if context.user_data.get("awaiting_jd"):
        context.user_data["jd_text"] = message_text
        context.user_data["resume_text"] = None
        set_waiting_state(context)
        await update.message.reply_text(
            "JD saved successfully.\n"
            "Now send /resume and upload or paste the resume."
        )
        return

    if context.user_data.get("awaiting_resume"):
        await process_resume_text(update, context, message_text, "pasted text")
        return

    if context.user_data.get("resume_text") or context.user_data.get("last_analysis"):
        reply = await asyncio.to_thread(
            answer_general_query,
            message_text,
            context.user_data.get("jd_text"),
            context.user_data.get("resume_text"),
            context.user_data.get("last_analysis"),
        )
        await update.message.reply_text(reply)
        return

    if looks_like_general_query(message_text):
        reply = await asyncio.to_thread(
            answer_general_query,
            message_text,
            context.user_data.get("jd_text"),
            context.user_data.get("resume_text"),
            context.user_data.get("last_analysis"),
        )
        await update.message.reply_text(reply)
        return

    if not context.user_data.get("jd_text"):
        await update.message.reply_text(
            "I need the JD first.\n"
            "Please use /jd before sending the resume.\n"
            "You can also ask me general career questions in normal chat."
        )
        return

    await update.message.reply_text(
        "JD is already attached.\n"
        "Send /resume when you are ready to upload or paste the resume.\n"
        "You can also ask me general career questions here."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_jd"):
        if not context.user_data.get("jd_text"):
            await update.message.reply_text(
                "You have not attached the JD yet.\n"
                "Please send /jd first."
            )
        else:
            await update.message.reply_text(
                "Photo uploads are only supported for JD screenshots.\n"
                "Use /resume to attach the resume as text or document."
            )
        return

    downloads_dir = generated_output_dir("downloads", update.effective_chat.id)
    file_path = downloads_dir / "jd_screenshot.jpg"
    telegram_file = await context.bot.get_file(update.message.photo[-1].file_id)
    await telegram_file.download_to_drive(str(file_path))

    await update.message.reply_text("Please wait while we read the JD screenshot...")

    try:
        jd_text = await asyncio.to_thread(extract_jd_text, file_path)
    except Exception as exc:
        logger.exception("Failed to extract JD from photo")
        await update.message.reply_text(
            "I could not read that JD screenshot.\n"
            "Please try again with clearer text, or paste the JD as text.\n"
            f"Details: {exc}"
        )
        return

    context.user_data["jd_text"] = jd_text
    context.user_data["resume_text"] = None
    set_waiting_state(context)
    await update.message.reply_text(
        "JD screenshot processed successfully.\n"
        "Now send /resume and upload or paste the resume."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    file_name = document.file_name or "attachment"
    file_extension = infer_extension(file_name, document.mime_type)

    if context.user_data.get("awaiting_jd"):
        await process_jd_document(update, context, file_name, file_extension)
        return

    if not context.user_data.get("jd_text"):
        await update.message.reply_text(
            "You have not attached the JD yet.\n"
            "Please send /jd first, then upload the job description."
        )
        return

    if not context.user_data.get("awaiting_resume"):
        await update.message.reply_text(
            "JD is already attached.\n"
            "Send /resume first, then upload the resume."
        )
        return

    await process_resume_document(update, context, file_name, file_extension)


async def process_jd_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_name: str,
    file_extension: str,
) -> None:
    downloads_dir = generated_output_dir("downloads", update.effective_chat.id)
    target_path = downloads_dir / f"jd_upload{file_extension}"
    telegram_file = await context.bot.get_file(update.message.document.file_id)
    await telegram_file.download_to_drive(str(target_path))

    await update.message.reply_text("Please wait while we read the job description...")

    try:
        jd_text = await asyncio.to_thread(extract_jd_text, target_path)
    except Exception as exc:
        logger.exception("Failed to extract JD from document")
        await update.message.reply_text(
            "I could not process that JD attachment.\n"
            "Please send the JD as text or as an image screenshot.\n"
            f"Details: {exc}"
        )
        return

    context.user_data["jd_text"] = jd_text
    context.user_data["resume_text"] = None
    set_waiting_state(context)
    await update.message.reply_text(
        f"JD saved from {file_name}.\n"
        "Now send /resume and upload or paste the resume."
    )


async def process_resume_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_name: str,
    file_extension: str,
) -> None:
    downloads_dir = generated_output_dir("downloads", update.effective_chat.id)
    target_path = downloads_dir / f"resume_upload{file_extension}"
    telegram_file = await context.bot.get_file(update.message.document.file_id)
    await telegram_file.download_to_drive(str(target_path))

    try:
        resume_text = await asyncio.to_thread(extract_resume_text, target_path)
    except Exception as exc:
        logger.exception("Failed to extract resume from document")
        await update.message.reply_text(
            "I could not process that resume file.\n"
            "Please upload a readable resume in PDF, DOCX, TXT, MD, or paste it as text.\n"
            f"Details: {exc}"
        )
        return

    await process_resume_text(update, context, resume_text, file_name)


async def process_resume_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    resume_text: str,
    source_label: str,
) -> None:
    jd_text = context.user_data.get("jd_text")
    if not jd_text:
        await update.message.reply_text(
            "You have not attached the JD yet.\n"
            "Please send /jd first."
        )
        return

    context.user_data["resume_text"] = resume_text
    set_waiting_state(context)

    await update.message.reply_text("Please wait while we are processing your JD and resume...")

    try:
        analysis = await asyncio.to_thread(
            analyze_resume_against_jd,
            jd_text,
            resume_text,
            update.effective_chat.id,
        )
    except Exception as exc:
        logger.exception("Resume analysis failed")
        await update.message.reply_text(
            "Something went wrong while analyzing the resume.\n"
            f"Details: {exc}"
        )
        return

    context.user_data["last_analysis"] = analysis

    matched = ", ".join(analysis["matched_keywords"][:8]) or "No strong keyword overlap detected yet"
    missing = ", ".join(analysis["missing_keywords"][:8]) or "No critical gaps detected"
    suggestions = "\n".join(f"- {item}" for item in analysis["suggestions"])

    result_message = (
        f"Processing complete for {source_label}.\n\n"
        f"Score: {analysis['score']} / 10\n"
        f"Alignment: {analysis['alignment_label']}\n"
        f"Summary: {analysis['summary']}\n\n"
        f"Matched keywords: {matched}\n"
        f"Missing or weak keywords: {missing}"
    )

    if analysis["score"] < 8 or analysis["suggestions"]:
        result_message += f"\n\nSuggestions to improve:\n{suggestions}"

    result_message += (
        "\n\nImproved resume drafts are attached below."
        "\nPlease review and replace any placeholders with your real achievements before using them."
    )
    await update.message.reply_text(result_message)

    for file_path in analysis["generated_files"]:
        with Path(file_path).open("rb") as handle:
            await update.message.reply_document(document=handle, filename=Path(file_path).name)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided. Please check your .env file.")
        print("CRITICAL: Add TELEGRAM_BOT_TOKEN to your .env file.")
        return

    application = Application.builder().token(token).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("jd", jd_command))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is polling and ready for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
