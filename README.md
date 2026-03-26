# TurboCV

TurboCV is a Telegram bot that compares a candidate's resume against a job description, returns an alignment score out of 10, suggests improvements, and generates downloadable improved resume drafts in multiple formats and templates.

## What The Bot Does

The bot supports a command-led flow:

1. User starts the bot with `/start`
2. Bot shows the available commands and accepted input formats
3. User sends `/jd` and provides the job description
4. User sends `/resume` and provides the resume
5. Bot processes both inputs
6. Bot returns:
   - score out of 10
   - alignment label
   - summary
   - matched keywords
   - missing or weak keywords
   - suggestions to improve
   - downloadable improved resume drafts

## Commands

- `/start` - shows the welcome message and current status
- `/help` - shows commands and supported formats
- `/jd` - tells the bot to wait for the job description
- `/resume` - tells the bot to wait for the resume
- `/cancel` - cancels the current intake step

## Supported Inputs

### Job Description

The JD can currently be provided as:

- pasted text message
- screenshot or image file such as `JPG`, `PNG`, `JPEG`, `WEBP`
- `PDF`
- `DOCX`
- `TXT`
- `MD`

Important note:

- JD screenshots depend on `GEMINI_API_KEY`
- if Gemini is not configured or fails, image-based JD extraction does not work
- text-based JD formats do not need Gemini

### Resume

The resume can currently be provided as:

- pasted text message
- `PDF`
- `DOCX`
- `TXT`
- `MD`
- Notion content exported as text, markdown, or PDF

Important note:

- legacy `.doc` files are not parsed by the current implementation
- direct Notion links are not supported; the content must be exported first

## High-Level Architecture

The project is intentionally small and centered around two main files:

- `main.py` handles Telegram bot commands, user interaction, and orchestration
- `utils.py` handles extraction, analysis, fallback logic, and resume file generation

Supporting folders:

- `templates/` contains the HTML resume templates
- `generated/` stores uploaded and generated files

## How The Bot Works

### 1. Bot Startup

When `python main.py` is run:

- environment variables are loaded from `.env`
- the Telegram bot is created using `python-telegram-bot`
- bot commands are registered with Telegram in `post_init`
- polling starts with `application.run_polling()`

### 2. Command-Led State Management

The bot uses `context.user_data` as in-memory per-user state.

Current keys used in that state include:

- `awaiting_jd`
- `awaiting_resume`
- `jd_text`
- `resume_text`
- `last_analysis`

This means:

- there is no database
- state is kept in memory per Telegram chat session
- restarting the bot clears runtime state

### 3. JD Intake

After `/jd`:

- the bot marks the user as `awaiting_jd = True`
- the next text or supported JD file is treated as the job description

If the JD is:

- text -> saved directly
- `PDF` -> text is extracted with `pdfplumber`
- `DOCX` -> text is extracted with `python-docx`
- `TXT` or `MD` -> file content is read directly
- image -> Gemini is used to extract readable JD text from the screenshot

Once the JD is stored:

- the waiting state is cleared
- the bot asks the user to send `/resume`

### 4. Resume Intake

After `/resume`:

- the bot checks whether a JD already exists
- if no JD exists, it tells the user to send `/jd` first
- if a JD exists, the bot marks the user as `awaiting_resume = True`

If the resume is:

- text -> used directly
- `PDF` -> parsed using `pdfplumber`
- `DOCX` -> parsed using `python-docx`
- `TXT` or `MD` -> read directly

Once the resume text is ready:

- the bot sends a processing message
- the analysis pipeline begins

## How Analysis Happens

The central analysis entry point is:

- `analyze_resume_against_jd(jd_text, resume_text, chat_id)`

This function performs three main tasks:

1. Analyze the resume against the JD
2. Build or normalize a draft improved resume
3. Generate downloadable output files

### AI + Fallback Strategy

Analysis is attempted in this order:

1. `Groq`
2. `Gemini`
3. local heuristic scoring

That means:

- if Groq works, Groq handles the analysis
- if Groq fails, Gemini is tried
- if both fail, the project still returns a local non-AI score and suggestions

Important distinction:

- this fallback applies to resume-vs-JD analysis
- JD screenshot extraction is Gemini-only in the current implementation

## AI Analysis Details

When an AI provider is available:

- the code sends both the JD and resume text to the model
- the model is asked to return strict JSON only
- the requested JSON includes:
  - `score`
  - `alignment_label`
  - `summary`
  - `matched_keywords`
  - `missing_keywords`
  - `suggestions`
  - `draft_resume`

### `draft_resume`

The generated draft resume is expected to include:

- `name`
- `headline`
- `contact`
- `summary`
- `skills`
- `experience`
- `projects`
- `education`
- `certifications`
- `notes`

The prompt explicitly asks the AI:

- not to invent facts
- to keep suggestions practical
- to use placeholders only when information is missing

Even with that instruction, generated resume drafts should still be reviewed manually before use.

## Local Heuristic Analysis

If both Groq and Gemini fail, the bot still produces an analysis locally.

### How local scoring works

The current heuristic uses:

- keyword overlap between JD and resume
- presence of resume sections such as summary, skills, experience, projects, education
- presence of strong action verbs
- presence of metrics like `%`, `+`, or currency values

### Rough score formula

The local score is based on:

- keyword match ratio
- section coverage
- action verb presence
- measurable impact presence

The result is then clamped into a `1.0` to `10.0` range.

### Alignment labels

- `Strong fit` for higher scores
- `Moderate fit` for mid-range scores
- `Needs improvement` for lower scores

### Suggestions

The local suggestion generator typically recommends:

- adding verified missing JD keywords
- improving the skills section
- adding measurable impact
- rewriting bullets with stronger action verbs
- tailoring the summary more closely to the role

## How Improved Resume Drafts Are Built

After analysis, the project creates a normalized resume draft.

If AI already returned a `draft_resume`:

- that version is used

If not:

- the project creates one from the resume text using simple extraction heuristics

The fallback draft builder:

- takes the first meaningful line as the name
- tries to detect a contact line
- guesses a role hint from the JD
- extracts bullet-like achievements from the resume
- builds a tailored summary
- mixes matched keywords with "validate and add if true" style skills for missing ones
- extracts education, projects, and certifications when possible

## Generated Outputs

For each processed resume, the bot generates:

- `improved_resume.txt`
- `improved_resume.md`
- `improved_resume.docx`
- `resume_classic.html`
- `resume_modern.html`
- `resume_compact.html`

If `wkhtmltopdf` is installed and available in the system path, the HTML resumes can also be converted into PDF files.

### Templates

The HTML templates are stored in:

- `templates/resume_classic.html`
- `templates/resume_modern.html`
- `templates/resume_compact.html`

These are rendered with `Jinja2`.

## File And Folder Behavior

### Uploaded files

Uploaded JD and resume files are stored under:

- `generated/downloads/<chat_id>/`

### Generated results

Generated outputs are stored under:

- `generated/results/<chat_id>/<timestamp>/`

Current behavior:

- files are kept on disk
- there is no cleanup mechanism yet
- this is helpful for debugging, but storage will grow over time

## Project Flow Summary

Here is the actual end-to-end working flow:

1. User runs `/start`
2. Bot shows commands and formats
3. User runs `/jd`
4. User sends JD as text, document, or screenshot
5. Bot extracts JD text
6. User runs `/resume`
7. User sends resume as text or file
8. Bot extracts resume text
9. Bot runs AI analysis with fallback
10. Bot builds an improved resume draft
11. Bot generates output files
12. Bot replies with score, feedback, and downloadable files

## Environment Variables

Create a `.env` file with:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

### What each key does

- `TELEGRAM_BOT_TOKEN` is required to run the bot
- `GEMINI_API_KEY` is used for JD screenshot extraction and can also be used as analysis fallback
- `GROQ_API_KEY` is used as the primary AI analysis provider

## Installation

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run The Bot

```powershell
python main.py
```

If everything is configured correctly, the terminal will show that the bot is polling and ready for messages.

## Dependencies

Main libraries currently used:

- `python-telegram-bot`
- `python-dotenv`
- `google-generativeai`
- `groq`
- `pdfplumber`
- `python-docx`
- `Jinja2`
- `pdfkit`

## Current Limitations

This README describes the project as it works now, including current limitations:

- JD screenshot extraction depends on Gemini
- `.doc` files are not supported
- direct Notion links are not supported
- local analysis is heuristic, not deeply semantic
- generated resume drafts may still need manual cleanup
- uploaded/generated files are not automatically deleted
- runtime user state is in memory only
- `google-generativeai` is deprecated and should be migrated later

## Suggested Next Improvements

Good next improvements for the project would be:

- add cleanup for uploaded and generated files
- log AI provider failures instead of silently swallowing them
- add tests for parsing, analysis fallback, and template generation
- support more document formats
- add chunking/truncation for very large resumes and JDs
- migrate Gemini integration to the newer SDK
- improve validation so generated resume drafts never overstate candidate experience

## Notes

This README is written to match the current implementation rather than an ideal future version. If the code changes, this file should be updated along with it so the project remains easy to understand for new contributors and reviewers.
