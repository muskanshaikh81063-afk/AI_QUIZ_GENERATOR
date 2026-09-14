/**
 * AI-Based Quiz Generator - Interactive Client-Side Logic
 */

// Global state for generated quiz preview
let currentGeneratedQuiz = {
    title: "",
    difficulty: "Medium",
    questions: []
};

// -------------------------------------------------------------------
// Helper: Show / Hide Loading Overlay
// -------------------------------------------------------------------
function showLoading(message = "Analyzing text and generating quiz...") {
    const overlay = document.getElementById("loadingOverlay");
    const msgElem = document.getElementById("loadingMessage");
    if (msgElem) msgElem.textContent = message;
    if (overlay) overlay.style.display = "flex";
}

function hideLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) overlay.style.display = "none";
}

// -------------------------------------------------------------------
// PDF Upload & Extraction Handler
// -------------------------------------------------------------------
function handlePdfUpload(fileInput) {
    const file = fileInput.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        alert("Please select a valid PDF file.");
        fileInput.value = "";
        return;
    }

    const formData = new FormData();
    formData.append("pdf_file", file);

    showLoading("Reading and extracting text from PDF using PyPDF2...");

    fetch("/api/extract-pdf", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const previewArea = document.getElementById("extractedTextPreview");
            const studyTextInput = document.getElementById("studyMaterialText");
            const previewCard = document.getElementById("textPreviewCard");
            const textStats = document.getElementById("extractedStats");

            if (previewArea) previewArea.textContent = data.text;
            if (studyTextInput) studyTextInput.value = data.text;
            if (previewCard) previewCard.style.display = "block";
            if (textStats) {
                textStats.textContent = `Extracted from ${data.filename}: ${data.word_count} words (${data.char_count} characters)`;
            }

            // Default quiz title from filename
            const titleInput = document.getElementById("quizTitle");
            if (titleInput && !titleInput.value) {
                titleInput.value = data.filename.replace(/\.pdf$/i, "") + " Quiz";
            }
        } else {
            alert("PDF Extraction Error: " + (data.error || "Failed to extract text."));
        }
    })
    .catch(err => {
        hideLoading();
        alert("Network error while extracting PDF: " + err.message);
    });
}

// -------------------------------------------------------------------
// Generate & Start Quiz Directly (Hides questions & answers until attempt)
// -------------------------------------------------------------------
function generateAndStartQuiz() {
    const studyText = document.getElementById("studyMaterialText")?.value.trim();
    const title = document.getElementById("quizTitle")?.value.trim() || "Study Quiz";
    const difficulty = document.getElementById("quizDifficulty")?.value || "Medium";
    const questionType = document.getElementById("questionType")?.value || "MCQ";
    const numQuestions = parseInt(document.getElementById("numQuestions")?.value || "5", 10);

    if (!studyText || studyText.length < 20) {
        alert("Please upload a PDF or paste notes with at least 20 characters before generating a quiz.");
        return;
    }

    showLoading("Generating quiz with AI... Preparing your test...");

    fetch("/generate-quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            text: studyText,
            title: title,
            difficulty: difficulty,
            question_type: questionType,
            num_questions: numQuestions
        })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            hideLoading();
            alert("Quiz Generation Error: " + (data.error || "Unable to generate quiz."));
            return;
        }

        // Save directly to database and launch quiz immediately
        return fetch("/quiz/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: data.title,
                difficulty: data.difficulty,
                questions: data.questions
            })
        });
    })
    .then(res => res ? res.json() : null)
    .then(saveData => {
        if (saveData) {
            hideLoading();
            if (saveData.success && saveData.quiz_id) {
                // Redirect directly to Attempt Quiz!
                window.location.href = `/quiz/${saveData.quiz_id}`;
            } else {
                alert("Error saving quiz: " + (saveData.error || "Could not start quiz."));
            }
        }
    })
    .catch(err => {
        hideLoading();
        alert("Error: " + err.message);
    });
}

// -------------------------------------------------------------------
// Toggle Detailed Answers on Result Page
// -------------------------------------------------------------------
function toggleResultAnswers() {
    const container = document.getElementById("detailedAnswersContainer");
    const btnText = document.getElementById("toggleAnswersBtnText");
    const btnIcon = document.getElementById("toggleAnswersBtnIcon");

    if (!container) return;

    if (container.style.display === "none") {
        container.style.display = "block";
        if (btnText) btnText.textContent = "Hide Detailed Answers";
        if (btnIcon) btnIcon.className = "bi bi-eye-slash me-1";
    } else {
        container.style.display = "none";
        if (btnText) btnText.textContent = "Show Detailed Answers";
        if (btnIcon) btnIcon.className = "bi bi-eye me-1";
    }
}

// -------------------------------------------------------------------
// Generate Quiz Handler (Optional Customization Mode)
// -------------------------------------------------------------------
function triggerQuizGeneration() {
    const studyText = document.getElementById("studyMaterialText")?.value.trim();
    const title = document.getElementById("quizTitle")?.value.trim() || "Study Quiz";
    const difficulty = document.getElementById("quizDifficulty")?.value || "Medium";
    const questionType = document.getElementById("questionType")?.value || "MCQ";
    const numQuestions = parseInt(document.getElementById("numQuestions")?.value || "5", 10);

    if (!studyText || studyText.length < 20) {
        alert("Please upload a PDF or paste notes with at least 20 characters before generating a quiz.");
        return;
    }

    showLoading("Generating quiz with AI... (This takes a few seconds)");

    fetch("/generate-quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            text: studyText,
            title: title,
            difficulty: difficulty,
            question_type: questionType,
            num_questions: numQuestions
        })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            currentGeneratedQuiz = {
                title: data.title,
                difficulty: data.difficulty,
                questions: data.questions
            };
            renderQuizPreview(data);
        } else {
            alert("Quiz Generation Error: " + (data.error || "Unable to generate quiz."));
        }
    })
    .catch(err => {
        hideLoading();
        alert("Network error: " + err.message);
    });
}

// -------------------------------------------------------------------
// Render Quiz Preview & Edit Interface
// -------------------------------------------------------------------
function renderQuizPreview(data) {
    const previewSection = document.getElementById("quizPreviewSection");
    const container = document.getElementById("previewQuestionsList");
    const modeBadge = document.getElementById("generationModeBadge");
    const previewTitle = document.getElementById("previewTitle");

    if (!previewSection || !container) return;

    previewSection.style.display = "block";
    previewSection.scrollIntoView({ behavior: "smooth" });

    if (modeBadge) modeBadge.textContent = data.mode || "Generated Successfully";
    if (previewTitle) previewTitle.textContent = data.title;

    container.innerHTML = "";

    data.questions.forEach((q, idx) => {
        const card = document.createElement("div");
        card.className = "card mb-3 p-3 border-start border-primary border-4";
        card.id = `preview-q-${idx}`;

        let optionsHtml = "";
        q.options.forEach((opt, optIdx) => {
            const isCorrect = (opt === q.correct_answer);
            optionsHtml += `
                <div class="input-group mb-2">
                    <span class="input-group-text">
                        <input type="radio" name="preview_correct_${idx}" value="${optIdx}" 
                               ${isCorrect ? "checked" : ""} 
                               onchange="updateCorrectAnswer(${idx}, ${optIdx})" 
                               title="Mark as correct answer">
                    </span>
                    <input type="text" class="form-control" value="${escapeHtml(opt)}" 
                           oninput="updateOptionText(${idx}, ${optIdx}, this.value)">
                </div>
            `;
        });

        card.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-secondary">Question ${idx + 1} (${q.question_type})</span>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="deletePreviewQuestion(${idx})" title="Remove question">
                    <i class="bi bi-trash"></i> Delete
                </button>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold">Question:</label>
                <textarea class="form-control" rows="2" oninput="updateQuestionText(${idx}, this.value)">${escapeHtml(q.question)}</textarea>
            </div>
            <div class="mb-2">
                <label class="form-label fw-bold small text-muted">Options (Select radio for correct answer):</label>
                ${optionsHtml}
            </div>
            <div class="mb-1">
                <label class="form-label fw-bold small text-muted">Explanation:</label>
                <input type="text" class="form-control form-control-sm" value="${escapeHtml(q.explanation || '')}" 
                       oninput="updateExplanationText(${idx}, this.value)">
            </div>
        `;
        container.appendChild(card);
    });
}

function updateQuestionText(qIdx, val) {
    if (currentGeneratedQuiz.questions[qIdx]) {
        currentGeneratedQuiz.questions[qIdx].question = val;
    }
}

function updateOptionText(qIdx, optIdx, val) {
    if (currentGeneratedQuiz.questions[qIdx]) {
        const oldVal = currentGeneratedQuiz.questions[qIdx].options[optIdx];
        currentGeneratedQuiz.questions[qIdx].options[optIdx] = val;
        // If this was the correct answer, keep it updated
        if (currentGeneratedQuiz.questions[qIdx].correct_answer === oldVal) {
            currentGeneratedQuiz.questions[qIdx].correct_answer = val;
        }
    }
}

function updateCorrectAnswer(qIdx, optIdx) {
    if (currentGeneratedQuiz.questions[qIdx]) {
        const chosen = currentGeneratedQuiz.questions[qIdx].options[optIdx];
        currentGeneratedQuiz.questions[qIdx].correct_answer = chosen;
    }
}

function updateExplanationText(qIdx, val) {
    if (currentGeneratedQuiz.questions[qIdx]) {
        currentGeneratedQuiz.questions[qIdx].explanation = val;
    }
}

function deletePreviewQuestion(qIdx) {
    if (currentGeneratedQuiz.questions.length <= 1) {
        alert("A quiz must have at least one question.");
        return;
    }
    currentGeneratedQuiz.questions.splice(qIdx, 1);
    renderQuizPreview(currentGeneratedQuiz);
}

// -------------------------------------------------------------------
// Save Quiz to Database
// -------------------------------------------------------------------
function saveGeneratedQuiz(autoStart = false) {
    if (!currentGeneratedQuiz.questions || currentGeneratedQuiz.questions.length === 0) {
        alert("There are no questions to save.");
        return;
    }

    const titleInput = document.getElementById("quizTitle");
    if (titleInput && titleInput.value.trim()) {
        currentGeneratedQuiz.title = titleInput.value.trim();
    }

    showLoading("Saving quiz to database...");

    fetch("/quiz/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentGeneratedQuiz)
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            if (autoStart && data.quiz_id) {
                window.location.href = `/quiz/${data.quiz_id}`;
            } else {
                alert("Quiz saved successfully!");
                window.location.href = "/history";
            }
        } else {
            alert("Error saving quiz: " + (data.error || "Unknown error."));
        }
    })
    .catch(err => {
        hideLoading();
        alert("Network error while saving quiz: " + err.message);
    });
}

// -------------------------------------------------------------------
// Interactive Quiz Player Stepper (quiz.html)
// -------------------------------------------------------------------
let currentStep = 0;
let totalQuizSteps = 0;

function initQuizPlayer(total) {
    totalQuizSteps = total;
    showQuestionStep(0);
}

function showQuestionStep(index) {
    if (index < 0 || index >= totalQuizSteps) return;

    // Hide all question cards
    for (let i = 0; i < totalQuizSteps; i++) {
        const card = document.getElementById(`q-step-${i}`);
        if (card) card.style.display = (i === index) ? "block" : "none";

        // Update question navigation bubble
        const navBtn = document.getElementById(`nav-btn-${i}`);
        if (navBtn) {
            if (i === index) {
                navBtn.classList.add("border", "border-3", "border-primary");
            } else {
                navBtn.classList.remove("border-3", "border-primary");
            }
        }
    }

    currentStep = index;

    // Update Progress text & bar
    const progressText = document.getElementById("quizProgressText");
    const progressBar = document.getElementById("quizProgressBar");
    if (progressText) progressText.textContent = `Question ${index + 1} of ${totalQuizSteps}`;
    if (progressBar) {
        const pct = Math.round(((index + 1) / totalQuizSteps) * 100);
        progressBar.style.width = `${pct}%`;
    }

    // Prev / Next button state
    const prevBtn = document.getElementById("quizPrevBtn");
    const nextBtn = document.getElementById("quizNextBtn");
    const submitBtn = document.getElementById("quizSubmitBtn");

    if (prevBtn) prevBtn.disabled = (index === 0);
    if (nextBtn) nextBtn.style.display = (index === totalQuizSteps - 1) ? "none" : "inline-block";
    if (submitBtn) submitBtn.style.display = (index === totalQuizSteps - 1) ? "inline-block" : "none";
}

function nextQuestion() {
    if (currentStep < totalQuizSteps - 1) {
        showQuestionStep(currentStep + 1);
    }
}

function prevQuestion() {
    if (currentStep > 0) {
        showQuestionStep(currentStep - 1);
    }
}

function markAnswerSelected(stepIndex, questionId, selectedValue) {
    const navBtn = document.getElementById(`nav-btn-${stepIndex}`);
    if (navBtn) {
        navBtn.classList.remove("btn-outline-secondary");
        navBtn.classList.add("btn-success");
    }
}

function submitQuizAnswers(quizId) {
    // Exact user confirmation required
    if (!confirm("Are you sure you want to submit the quiz?")) {
        return;
    }

    const answers = {};
    for (let i = 0; i < totalQuizSteps; i++) {
        const selected = document.querySelector(`input[name="answer_q_${i}"]:checked`);
        const qIdElem = document.getElementById(`qid_${i}`);
        if (qIdElem) {
            const qId = qIdElem.value;
            answers[qId] = selected ? selected.value : "";
        }
    }

    showLoading("Submitting your answers and calculating score...");

    fetch(`/quiz/${quizId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(answers)
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success && data.redirect_url) {
            window.location.href = data.redirect_url;
        } else {
            alert("Error submitting quiz: " + (data.error || "Could not calculate score."));
        }
    })
    .catch(err => {
        hideLoading();
        alert("Network error: " + err.message);
    });
}

// -------------------------------------------------------------------
// Utility: Escape HTML
// -------------------------------------------------------------------
function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
