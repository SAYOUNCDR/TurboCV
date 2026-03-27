# TurboCV

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-python--telegram--bot-2ea44f)](https://python-telegram-bot.org/)
[![Status](https://img.shields.io/badge/Status-Active-informational)](#)

TurboCV is a Telegram bot that evaluates how well a resume aligns with a job description, returns a score out of 10, and generates improved resume drafts in multiple downloadable formats.

## Overview

The bot runs a command-driven workflow:

1. User submits a job description.
2. User submits a resume.
3. TurboCV analyzes alignment using AI with fallback logic.
4. TurboCV returns a score, gap analysis, improvement suggestions, and generated resume files.

## Core Features

- Resume-to-JD alignment scoring (`1.0` to `10.0`)
- Matched and missing keyword analysis
- Practical, role-specific improvement suggestions
- Improved resume draft generation
- Multi-format output (`TXT`, `MD`, `DOCX`, template-based `HTML`)
- AI provider fallback to local heuristic scoring

## Commands

- `/start` - Show welcome message and current status.
- `/help` - Show command and format guidance.
- `/jd` - Begin job description intake.
- `/resume` - Begin resume intake.
- `/cancel` - Cancel current intake step.

## Supported Input Formats

### Job Description

- Text message
- Images: `JPG`, `JPEG`, `PNG`, `WEBP` (Gemini required)
- `PDF`
- `DOCX`
- `TXT`
- `MD`

### Resume

- Text message
- `PDF`
- `DOCX`
- `TXT`
- `MD`
- Notion exports (text, markdown, or PDF)

Notes:
- Legacy `.doc` files are not supported.
- Direct Notion links are not supported.

## Analysis Pipeline

Primary analysis entry point:

- `analyze_resume_against_jd(jd_text, resume_text, chat_id)`

Provider order:

1. Groq
2. Gemini
3. Local heuristic fallback

If AI providers fail, TurboCV still returns a usable score and recommendations via local scoring logic.

### AI Output Contract

When AI analysis succeeds, the response is expected in strict JSON with these fields:

- `score`
- `alignment_label`
- `summary`
- `matched_keywords`
- `missing_keywords`
- `suggestions`
- `draft_resume`

## Generated Outputs

For each run, TurboCV can generate:

- `improved_resume.txt`
- `improved_resume.md`
- `improved_resume.docx`
- `resume_classic.html`
- `resume_modern.html`
- `resume_compact.html`

If `wkhtmltopdf` is installed and available in `PATH`, HTML outputs can also be converted to PDF.

## Project Structure

```text
main.py                 # Telegram command handlers and orchestration
utils.py                # Parsing, analysis, fallback, and file generation
templates/              # Jinja2 HTML resume templates
generated/downloads/    # Uploaded user files
generated/results/      # Generated output artifacts
```

## Configuration

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

Environment variables:

- `TELEGRAM_BOT_TOKEN`: Required to run the bot.
- `GEMINI_API_KEY`: Required for JD image extraction and used as analysis fallback provider.
- `GROQ_API_KEY`: Primary AI analysis provider.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

The bot starts polling once initialization is complete.

## Current Limitations

- JD image extraction depends on Gemini.
- `.doc` input is not supported.
- Local fallback analysis is heuristic-based.
- Generated artifacts are not auto-cleaned.
- Runtime user state is in-memory only.
- `google-generativeai` is deprecated and should be migrated.

## Recommended Next Improvements

- Add retention and cleanup for generated files.
- Add structured logging for provider failures.
- Add automated tests for parsing, fallback logic, and template rendering.
- Improve handling for very large JD/resume inputs.
- Migrate Gemini integration to the latest SDK.
- Tighten validation to reduce over-assertive draft content.

## License

No license file is currently included in this repository.
