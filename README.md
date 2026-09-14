# AI-Based Quiz Generator from PDF / Notes
### BSc Computer Science College Project

A complete, beginner-friendly web application that automatically extracts text from study materials (PDF documents or raw lecture notes) and uses **Google Gemini AI** to generate interactive Multiple Choice (MCQ) and True/False questions. Built using **Python Flask**, **SQLite**, **PyPDF2**, and a responsive **Bootstrap 5** frontend.

---

## 📌 Features

1. **User Authentication & Isolation**
   - User registration & login with email and secure password hashing (`Werkzeug`).
   - Session-based user isolation (each user can only view, edit, and attempt their own quizzes).
   - Safe logout functionality.

2. **Dual Material Input Modes**
   - **Upload PDF**: Upload textbook chapters, lecture slides, or exam sheets. PyPDF2 automatically parses and extracts readable text.
   - **Paste Notes**: Directly type or paste revision notes, summary points, or code notes into a clean input area.

3. **Intelligent AI Quiz Generation**
   - Connects to **Google Gemini API** (`gemini-1.5-flash`) via the Flask backend.
   - Generates questions strictly based on the provided text.
   - Configurable settings:
     - Number of questions (3, 5, 10, 15)
     - Difficulty levels: **Easy**, **Medium**, **Hard**
     - Question types: **MCQ (4 options)**, **True/False**, or **Mixed**
   - **Offline / Sample Mode Fallback**: If no Gemini API key is configured or the quota is exceeded, the app automatically switches to an offline contextual question generator so your project evaluation or demo **never fails**.

4. **Live Quiz Preview & Customization**
   - Review generated questions, options, correct answers, and explanations.
   - Edit questions or options before saving.
   - One-click **Save to Library** or **Save & Attempt Immediately**.

5. **Interactive Quiz Player**
   - Step-by-step question stepper with a progress bar.
   - Question navigation palette to easily jump between questions.
   - Automatic score calculation with pass/merit badges.

6. **Comprehensive Score Breakdown & Explanations**
   - Visual result score circle (Percentage, Score, Performance rating).
   - Question-by-question review showing:
     - Your selected answer
     - Correct answer
     - Educational explanation from the source text

7. **Quiz Library & History**
   - Saves all created quizzes in SQLite database.
   - Tracks total attempts and best score for each quiz.
   - Retake or delete quizzes at any time.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons |
| **Backend** | Python 3, Flask Framework |
| **Database** | SQLite (Embedded database `quiz_database.db`) |
| **PDF Extraction** | PyPDF2 |
| **AI Integration** | Google Gemini API (`google-generativeai`) |
| **Security** | Werkzeug password hashing, Flask Sessions |

---

## 🗄️ Database Schema

The application uses SQLite (`quiz_database.db`) with relational integrity and cascading deletes:

1. **`users`**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `name`: TEXT NOT NULL
   - `email`: TEXT NOT NULL UNIQUE
   - `password`: TEXT NOT NULL (Hashed)
   - `created_at`: TIMESTAMP

2. **`quizzes`**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `user_id`: INTEGER (FOREIGN KEY -> users.id)
   - `title`: TEXT NOT NULL
   - `difficulty`: TEXT NOT NULL
   - `created_at`: TIMESTAMP

3. **`questions`**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `quiz_id`: INTEGER (FOREIGN KEY -> quizzes.id)
   - `question`: TEXT NOT NULL
   - `question_type`: TEXT NOT NULL (`MCQ` or `True/False`)
   - `options`: TEXT NOT NULL (JSON-encoded array of options)
   - `correct_answer`: TEXT NOT NULL
   - `explanation`: TEXT

4. **`quiz_attempts`**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `quiz_id`: INTEGER (FOREIGN KEY -> quizzes.id)
   - `user_id`: INTEGER (FOREIGN KEY -> users.id)
   - `score`: INTEGER NOT NULL
   - `total_questions`: INTEGER NOT NULL
   - `percentage`: REAL NOT NULL
   - `user_answers`: TEXT (JSON-encoded user choices)
   - `completed_at`: TIMESTAMP

---

## 📁 Project Directory Structure

```
AI_QUIZ_GENERATOR/
│
├── app.py                     # Main Flask application and API routes
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (Gemini Key, Secret Key)
├── .env.example               # Example configuration template
├── README.md                  # Comprehensive project documentation
├── .gitignore                 # Git ignore rules
│
├── templates/                 # Jinja2 HTML templates
│   ├── index.html             # Landing page
│   ├── login.html             # User login
│   ├── register.html          # User registration
│   ├── dashboard.html         # Student dashboard & statistics
│   ├── upload.html            # Upload PDF / Paste Notes & Quiz Preview
│   ├── quiz.html              # Interactive quiz attempt player
│   ├── result.html            # Detailed score breakdown & explanations
│   └── history.html           # Quiz library and past attempts
│
├── static/                    # Frontend assets
│   ├── style.css              # Custom styling & responsive theme
│   └── script.js              # Client-side logic, PDF parsing, Quiz Stepper
│
└── services/
    └── ai_service.py          # PyPDF2 extraction, Gemini AI & Fallback engine
```

---

## 🚀 Quick Setup & Installation Guide

Follow these simple steps to run the project on your computer:

### Step 1: Open the Project in VS Code
1. Open **Visual Studio Code**.
2. Click **File > Open Folder...** and select the `AI_QUIZ_GENERATOR` folder.
3. Open the built-in terminal in VS Code using ``Ctrl + ` `` (or **Terminal > New Terminal**).

---

### Step 2: Create and Activate a Python Virtual Environment

In your VS Code terminal (PowerShell or Command Prompt), run:

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy warning, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` and then re-run the activate command)*

**Or On Windows (Command Prompt `cmd`):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

You will see `(venv)` appear at the beginning of your terminal prompt.

---

### Step 3: Install Required Dependencies

Run:
```powershell
pip install -r requirements.txt
```

This installs:
- `Flask`: The backend web framework
- `PyPDF2`: For extracting text from PDF files
- `google-generativeai`: Official SDK for Google Gemini
- `python-dotenv`: For loading API keys from `.env`
- `Werkzeug`: For secure password hashing

---

### Step 4: Configure Google Gemini API Key

1. Open the `.env` file in VS Code.
2. Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to generate a free Gemini API key.
3. Paste your key in `.env`:
   ```env
   SECRET_KEY=college_quiz_generator_secret_key_2026
   GEMINI_API_KEY=AIzaSy...your_real_gemini_api_key...
   ```
4. Save the file (`Ctrl + S`).

> **💡 Note for Demonstration / Viva:**
> If you don't have an API key or don't have internet access during your college presentation, you can leave `GEMINI_API_KEY=` blank. The application will automatically operate in **Sample Quiz Mode** and create valid quizzes from the text using its built-in fallback engine!

---

### Step 5: Start the Flask Application

Run:
```powershell
python app.py
```

You should see output similar to:
```
AI Quiz Generator server starting on http://127.0.0.1:5000 ...
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

### Step 6: Open the Website in Your Browser

1. Open Chrome, Edge, or Firefox.
2. Navigate to: **`http://127.0.0.1:5000`**
3. Click **Register Free** to create a test account (e.g. `student@college.edu`).
4. Upload a sample PDF or paste your study notes, generate a quiz, preview questions, and take the quiz!

---

## 🧪 Testing Checklist for Presentation

- [x] **Registration & Login**: Register a user, log in, verify session persistence.
- [x] **PDF Text Extraction**: Upload a PDF document and confirm extracted text appears in the preview box.
- [x] **Notes Input**: Paste revision notes and confirm character count updates.
- [x] **AI Generation**: Choose 5 questions, Medium difficulty, MCQ type and click Generate.
- [x] **Quiz Preview & Edit**: Modify a question text or change an option before saving.
- [x] **Quiz Attempt**: Answer questions using Next/Previous and Question Jump buttons.
- [x] **Auto Scoring**: Submit quiz and observe immediate score, percentage badge, and explanations.
- [x] **Quiz Library**: Verify that the quiz and best score appear under **Quiz History**.
- [x] **User Isolation**: Log out and register a new user; verify that user 2 cannot see user 1's quizzes.

---

## 👨‍🎓 Viva / Examination Q&A

**Q1. How does the application extract text from PDF files?**  
*Answer:* We use `PyPDF2.PdfReader`. The uploaded file stream is parsed page-by-page, extracting all ASCII/Unicode text layers and filtering out empty lines.

**Q2. How does the Gemini AI integration work?**  
*Answer:* The extracted notes and configuration parameters (difficulty, question count, question type) are formatted into a strict system prompt. The backend calls `google.generativeai.GenerativeModel('gemini-1.5-flash')`, requesting a JSON array of questions, options, correct answers, and explanations.

**Q3. How is user data and passwords secured?**  
*Answer:* Passwords are never stored in plain text. They are hashed using SHA-256 with salt via `werkzeug.security.generate_password_hash()`. When logging in, `check_password_hash()` compares the hash securely.

**Q4. What happens if there is no internet connection or no Gemini API key?**  
*Answer:* The application implements a graceful fallback mechanism (`generate_fallback_quiz` in `services/ai_service.py`). It analyzes the uploaded text, extracts sentences and key terms, and constructs working MCQs and True/False questions so the project remains 100% operational.

---

## 📜 License
This project is developed for educational purposes as a BSc Computer Science academic project.
