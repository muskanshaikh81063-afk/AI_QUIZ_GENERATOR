"""
AI Service Module for AI-Based Quiz Generator
Handles:
1. PDF Text Extraction using PyPDF2
2. AI Quiz Generation using Google Gemini API
3. Offline / Sample Quiz Generation when API key is missing or unavailable
"""

import os
import re
import json
import random
from typing import List, Dict, Any, Tuple
import PyPDF2


def extract_text_from_pdf(file_stream) -> str:
    """
    Extracts text from an uploaded PDF file stream or file path.
    Raises ValueError if PDF is empty or invalid.
    """
    try:
        reader = PyPDF2.PdfReader(file_stream)
        if len(reader.pages) == 0:
            raise ValueError("The uploaded PDF has no pages.")

        extracted_text = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(page_text.strip())

        full_text = "\n\n".join(extracted_text).strip()
        if not full_text or len(full_text) < 10:
            raise ValueError(
                "Could not extract readable text from the PDF. "
                "The PDF might be scanned/image-based or empty."
            )

        return full_text
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Error reading PDF file: {str(e)}")


def _clean_json_response(raw_text: str) -> str:
    """Removes markdown code fences if present in Gemini output."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    return raw_text.strip()


def generate_quiz_with_gemini(
    text: str,
    num_questions: int = 5,
    difficulty: str = "Medium",
    question_type: str = "MCQ",
    api_key: str = None
) -> List[Dict[str, Any]]:
    """
    Generates quiz questions using Google Gemini API.
    Returns a list of question dictionaries.
    """
    import google.generativeai as genai

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise ValueError("No Gemini API key provided.")

    genai.configure(api_key=api_key)

    # Use gemini-1.5-flash which is standard, fast, and reliable
    # We also have a fallback model list in case of deprecation
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    prompt = f"""
You are an expert academic educator and quiz master.
Create exactly {num_questions} high-quality quiz questions strictly based on the following study text.

Difficulty Level: {difficulty}
Question Type: {question_type} (Options: 'MCQ' for Multiple Choice Questions with 4 choices, 'True/False' for True/False questions, or 'Mixed' for a combination of MCQ and True/False).

Rules:
1. Questions MUST test understanding directly from the provided text.
2. For MCQ questions, provide exactly 4 distinct options.
3. For True/False questions, options MUST be ["True", "False"].
4. 'correct_answer' must be the exact text of one of the options.
5. Provide a clear, educational 'explanation' citing or summarizing the reasoning from the text.
6. Return ONLY valid JSON in an array format. Do NOT wrap in explanation or commentary.

Output JSON format schema:
[
  {{
    "question": "Question text here?",
    "question_type": "MCQ",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Explanation here."
  }},
  {{
    "question": "Statement text here.",
    "question_type": "True/False",
    "options": ["True", "False"],
    "correct_answer": "True",
    "explanation": "Explanation here."
  }}
]

Study Material / Notes:
\"\"\"
{text[:12000]}
\"\"\"
"""

    last_error = None
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                )
            )
            cleaned = _clean_json_response(response.text)
            quiz_data = json.loads(cleaned)

            if isinstance(quiz_data, dict) and "questions" in quiz_data:
                quiz_data = quiz_data["questions"]

            if not isinstance(quiz_data, list) or len(quiz_data) == 0:
                raise ValueError("Model output did not match expected list format.")

            validated_questions = []
            for item in quiz_data[:num_questions]:
                q_text = item.get("question", "").strip()
                q_type = item.get("question_type", "MCQ")
                options = item.get("options", [])
                ans = item.get("correct_answer", "")
                exp = item.get("explanation", "Based on provided study material.")

                if not q_text or not options:
                    continue

                if ans not in options:
                    # Fix possible mismatch
                    options.append(ans)

                validated_questions.append({
                    "question": q_text,
                    "question_type": q_type,
                    "options": options,
                    "correct_answer": ans,
                    "explanation": exp
                })

            if len(validated_questions) > 0:
                return validated_questions

        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Gemini API generation failed: {str(last_error)}")


def generate_fallback_quiz(
    text: str,
    num_questions: int = 5,
    difficulty: str = "Medium",
    question_type: str = "MCQ"
) -> List[Dict[str, Any]]:
    """
    Intelligent offline / sample quiz generator that creates questions
    directly from sentences and key concepts in the user's provided notes or PDF.
    Guarantees the application remains 100% functional even without an API key.
    """
    # Clean and split into sentences
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    raw_sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    
    # Filter sentences with reasonable length (between 30 and 200 chars)
    sentences = [
        s.strip() for s in raw_sentences 
        if 25 <= len(s.strip()) <= 200 and not s.strip().startswith("#")
    ]

    questions: List[Dict[str, Any]] = []

    # If text has too few sentences, add standard contextual concepts
    if len(sentences) < 3:
        sentences.extend([
            "Computer Science is the study of computation, information, and automation.",
            "Algorithms provide step-by-step procedures for solving computational problems.",
            "Relational databases store structured data in tables with rows and columns.",
            "Operating systems manage computer hardware and software resources.",
            "Python is a high-level interpreted programming language renowned for readability."
        ])

    random.seed(len(text) + num_questions)

    # Determine types
    types_list = []
    for i in range(num_questions):
        if question_type == "MCQ":
            types_list.append("MCQ")
        elif question_type == "True/False":
            types_list.append("True/False")
        else:
            types_list.append("MCQ" if i % 2 == 0 else "True/False")

    used_sentences = set()

    for i, q_type in enumerate(types_list):
        # Pick an unused sentence if possible
        available = [s for s in sentences if s not in used_sentences]
        sentence = random.choice(available if available else sentences)
        used_sentences.add(sentence)

        words = [w.strip('.,;:"()[]{}') for w in sentence.split() if len(w.strip('.,;:"()[]{}')) > 3]

        if q_type == "True/False":
            # Decide if statement will be True or False
            is_true = (i % 2 == 0)
            if is_true:
                q_text = f"Based on the text: \"{sentence}\""
                ans = "True"
                exp = f"True: The study material directly confirms: \"{sentence}\""
            else:
                # Invert or negate
                if words:
                    replaced_word = random.choice(words)
                    fake_sentence = sentence.replace(replaced_word, "never " + replaced_word, 1)
                else:
                    fake_sentence = "Not " + sentence
                q_text = f"Based on the text: \"{fake_sentence}\""
                ans = "False"
                exp = f"False: The original text specifies: \"{sentence}\""

            questions.append({
                "question": q_text,
                "question_type": "True/False",
                "options": ["True", "False"],
                "correct_answer": ans,
                "explanation": exp
            })
        else:
            # MCQ Question
            if words:
                keyword = random.choice(words)
                # Create fill in the blank or definition question
                blank_sentence = re.sub(r'\b' + re.escape(keyword) + r'\b', '_______', sentence, count=1)
                q_text = f"Fill in the blank based on your notes:\n\"{blank_sentence}\""
                ans = keyword

                # Distractors from other words or general concepts
                other_words = [w for s in sentences for w in s.split() if len(w) > 3 and w.lower() != keyword.lower()]
                distractor_pool = list(set(other_words))
                if len(distractor_pool) < 3:
                    distractor_pool.extend(["Framework", "Protocol", "Architecture", "Optimization", "Interface"])
                
                distractors = random.sample(distractor_pool, min(3, len(distractor_pool)))
                options = [ans] + distractors
                random.shuffle(options)

                exp = f"According to the notes: \"{sentence}\""
            else:
                q_text = f"Which statement best represents the provided notes?"
                ans = sentence
                options = [
                    sentence,
                    "This concept is completely unrelated to the provided document.",
                    "The text invalidates this premise.",
                    "None of the provided concepts mention this statement."
                ]
                random.shuffle(options)
                exp = f"Confirmed directly by: \"{sentence}\""

            questions.append({
                "question": q_text,
                "question_type": "MCQ",
                "options": options,
                "correct_answer": ans,
                "explanation": exp
            })

    return questions


def generate_quiz(
    text: str,
    num_questions: int = 5,
    difficulty: str = "Medium",
    question_type: str = "MCQ",
    api_key: str = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Primary interface for quiz generation.
    Attempts Gemini API first; if no key or failure occurs, falls back to
    sample mode gracefully.
    Returns: (questions_list, mode_description)
    """
    key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if key and key != "your_gemini_api_key_here":
        try:
            questions = generate_quiz_with_gemini(
                text=text,
                num_questions=num_questions,
                difficulty=difficulty,
                question_type=question_type,
                api_key=key
            )
            return questions, "Generated with Google Gemini AI"
        except Exception as e:
            # Fallback when Gemini API encounters errors (e.g. quota, network)
            print(f"[AI Service Warning] Gemini API error: {e}. Switching to sample mode.")
            questions = generate_fallback_quiz(
                text=text,
                num_questions=num_questions,
                difficulty=difficulty,
                question_type=question_type
            )
            return questions, f"Sample Mode (Gemini Notice: {str(e)[:60]}...)"
    else:
        # No API Key provided
        questions = generate_fallback_quiz(
            text=text,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_type
        )
        return questions, "Sample Quiz Mode (Add GEMINI_API_KEY in .env for live AI)"
