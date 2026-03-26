# Resume Analyzer Bot Implementation Plan

This document outlines the implementation plan, technology stack, and evaluation criteria for building a Resume Analyzer bot (MVP).

## 1. Scoring Criteria & Logic

The bot will evaluate the resume against the Job Description (JD) using an LLM based on the following criteria:

- **Keyword Matching (30%)**: Extraction of required skills, tools, and technologies from the JD and matching them against the resume content. Missing crucial keywords will lower this score.
- **Experience Relevance (25%)**: Comparing the required years of experience mapped in the JD with the calculated professional experience parsed from the resume.
- **Education & Certifications (15%)**: Checking if the job requires specific degrees or certifications and if they exist in the uploaded resume.
- **Action Verbs & Impact (15%)**: Evaluating if the resume uses strong action verbs and quantifies impact (e.g., "Increased sales by 20%").
- **Clarity & Formatted Readability (15%)**: Checking structural elements of the text indicating a well-organized flow (length, grammar, section presence).

The Language Model will be prompted to analyze these metrics and output a final score out of 10, along with detailed feedback.

## 2. Technology Stack Recommendations

For the MVP, we recommend the following stack for rapid development and reliability:

- **Bot Platform**: **Telegram** (via `python-telegram-bot`). Telegram is highly recommended for MVPs because its APIs handle file uploads (PDF/DOCX) and unstructured chat sessions exceptionally well natively. WhatsApp integration generally requires a specific Business API provider (like Twilio or Meta directly), making the initial setup slower.
- **Backend Language**: **Python** (excellent MVP language for AI/NLP, PDF parsing, and scalable bot scripting).
- **Core AI Engine**: **Google Gemini API (Free Tier)** or **Groq API (Llama 3 - Free Tier)**. Since there are no AI credits available, these APIs offer generous 100% free developer tiers that require no credit card, and they are excellent at structured JSON extraction.
- **Document Parsing**: 
  - `PyPDF2` or `pdfplumber` for PDF text extraction.
  - `python-docx` for parsing DOCX files.
- **Resume Templating & Generation Engine**: 
  - **HTML to PDF generation** using `Jinja2` (for templating) and `pdfkit` / `WeasyPrint` (for rendering the finalized PDFs). Alternatively, we can use a library like `ReportLab`.
- **Hosting/Deployment**: Render.com, Heroku, or AWS EC2 for running the Python worker continuously.
- **State Management**: **SQLite** (or in-memory states mapped to user Chat IDs) to manage conversational flows (e.g., waiting for JD input vs. waiting for the Resume file).

## 3. General Approach & Folder Structure

**Time Constraint:** The entire MVP implementation is constrained to a **2-hour time limit**. Therefore, the architecture and logic will be kept as straightforward as possible, focusing heavily on getting the core loop running quickly.

### Suggested Folder Structure
The project will use the following minimal directory structure suitable for a 2-hour MVP development cycle:

```text
TurboCV/
├── main.py             # Entry point: Telegram bot handlers and state logic
├── utils.py            # Helper functions: PDF/DOCX parsing and OpenAI API calls
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (API tokens)
├── templates/          # Directory holding HTML/CSS templates for resumes
│   └── format_1.html   # Basic clean resume template
└── downloads/          # Temporary directory for user uploads during session
```

### User Interaction Flow
1. User starts the bot (`/start`).
2. Bot requests the **Job Description (JD)** (Text).
3. User pastes JD; Bot acknowledges and requests the **Resume** (PDF/DOCX).
4. User uploads Resume.
5. Bot extracts text, queries the LLM for Score & Feedback, and returns textual results.
6. Bot maps LLM output to `format_1.html`, generates a new PDF, and sends it back.

## 4. Implementation Steps (2-Hour Timeline)

### Step 1: Core Setup & Document Parsing (40 mins)
- Initialize the project and the folder structure.
- Set up `main.py` with `python-telegram-bot` to handle the conversational state (JD -> Resume).
- Implement basic text extraction functions in `utils.py` using `pdfplumber` and `python-docx`.

### Step 2: AI Analysis & Feedback (40 mins)
- Integrate the free Gemini/Groq API in `utils.py`.
- Write the core prompt instructing the LLM to score the resume vs JD and return structured JSON (Score, Missing Keywords, Improved Snippets).
- Connect the bot to send the text-based review back to the user.

### Step 3: Resume Generation & Delivery (40 mins)
- Create one straightforward HTML template (`templates/format_1.html`).
- Use `Jinja2` to inject the LLM-improved data into the template.
- Use `pdfkit` or `WeasyPrint` to convert the HTML to a PDF and send it back to the user via the bot.

## User Review Required

- **Platform Choice**: Does Telegram sound good for the MVP, or do you strictly require a discord bot? (Telegram is suggested for faster development).
- **Templates**: Are there any specific styling elements you want in the generated resume templates, or should we design standard, clean tech templates?
- **AI Choice**: Both Google Gemini and Groq are free. Are you okay going with Gemini for the easiest free AI integration?
