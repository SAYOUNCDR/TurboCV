import os
import google.generativeai as genai
import pdfplumber
from docx import Document
import json

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        return None


def analyze_resume(resume_text, job_description):
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    You are an expert Resume Analyzer. Analyze the following resume against the provided Job Description.
    
    Job Description:
    {job_description}
    
    Resume:
    {resume_text}
    
    Evaluate based on:
    1. Keyword Matching (skills, tools)
    2. Experience Relevance
    3. Education & Certifications
    4. Action Verbs & Impact
    5. Clarity & Formatting
    
    Return the response in JSON format with the following structure:
    {{
        "score": <number out of 100>,
        "missing_keywords": [<list of strings>],
        "summary_feedback": "<string>",
        "improvement_tips": [<list of strings>]
    }}
    Ensure the output is valid JSON. Do not include markdown code blocks.
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            ),
        )
        print(f"Raw Gemini response: {response.text}")
        return json.loads(response.text)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {
            "score": 0,
            "missing_keywords": [],
            "summary_feedback": f"Error analyzing resume: {str(e)}",
            "improvement_tips": [],
        }
