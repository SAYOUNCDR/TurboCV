import os
from groq import Groq
import pdfplumber
from docx import Document
import json

# Configure Groq API
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


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
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            # Updated to a currently supported model
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )

        response_content = chat_completion.choices[0].message.content
        print(f"Raw Groq response: {response_content}")
        return json.loads(response_content)
    except Exception as e:
        print(f"Error calling Groq: {e}")
        return {
            "score": 0,
            "missing_keywords": [],
            "summary_feedback": f"Error analyzing resume: {str(e)}",
            "improvement_tips": [],
        }
