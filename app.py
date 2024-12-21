import random
from flask import Flask, render_template, request, session, redirect, url_for
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load flashcards from JSON
with open("flashcards.json", "r", encoding="utf-8") as f:
    flashcards = json.load(f)

@app.route("/")
def index():
    lessons = list(flashcards.keys())  # e.g., "Lesson 1", "Lesson 2", etc.
    parts = ["Part 1", "Part 2"]       # Assuming these parts exist in each lesson
    return render_template("index.html", lessons=lessons, parts=parts)

@app.route("/quiz", methods=["POST"])
def quiz():
    # Retrieve selected lessons and parts
    selected_parts = request.form.getlist("parts")  # e.g., ["Lesson 1:Part 1", "Lesson 2:Part 2"]
    num_to_mastered = int(request.form.get("num_to_mastered", 3))
    pinyin_hint = "pinyin" in request.form

    # Extract flashcards from the selected lessons and parts
    selected_flashcards = []
    for lesson_part in selected_parts:
        lesson, part = lesson_part.split(":")
        selected_flashcards.extend(flashcards.get(lesson, {}).get(part, []))

    # Shuffle the flashcards and store them in the session
    random.shuffle(selected_flashcards)
    session["questions"] = selected_flashcards
    session["progress"] = {card["vocab"]: 0 for card in selected_flashcards}
    session["num_to_mastered"] = num_to_mastered
    session["pinyin_hint"] = pinyin_hint
    session["question_history"] = []

    return redirect(url_for("next_question"))

@app.route("/next_question")
def next_question():
    # Get questions and progress
    cards = session["questions"]
    progress = session["progress"]
    num_to_mastered = session["num_to_mastered"]

    # Filter remaining questions
    remaining_questions = [
        card for card in cards if progress[card["vocab"]] < num_to_mastered
    ]

    if not remaining_questions:
        return redirect(url_for("results"))

    # Shuffle and pick a new vocab
    question_history = session.get("question_history", [])
    available_questions = [
        card for card in remaining_questions if card["vocab"] not in question_history
    ]

    if not available_questions:
        available_questions = remaining_questions
        session["question_history"] = []

    current_question = random.choice(available_questions)
    session["question_history"].append(current_question["vocab"])

    # Prepare options for the question
    options = [current_question["definition"]]
    other_definitions = [
        card["definition"] for card in cards if card["vocab"] != current_question["vocab"]
    ]
    options.extend(random.sample(other_definitions, min(3, len(other_definitions))))
    random.shuffle(options)
    current_question["options"] = options

    # Remove pinyin if pinyin_hint is False
    pinyin_hint = session.get("pinyin_hint", False)
    if not pinyin_hint and "pinyin" in current_question:
        current_question.pop("pinyin")

    # Calculate progress
    total_vocab = len(cards)
    mastered_vocab = sum(1 for v, p in progress.items() if p >= num_to_mastered)
    progress_percent = (mastered_vocab / total_vocab) * 100 if total_vocab > 0 else 0

    return render_template(
        "quiz.html",
        current_question=current_question,
        feedback=None,
        progress_percent=progress_percent,  # Pass progress to template
    )

@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    # Process the submitted answer
    vocab = request.form["vocab"]
    user_answer = request.form["answer"]
    correct_answer = request.form["correct_answer"]

    # Determine if the answer is correct
    is_correct = user_answer == correct_answer

    # Update progress only if the answer is correct
    if is_correct:
        progress = session["progress"]
        progress[vocab] += 1
        session["progress"] = progress  # Reassign the updated dictionary to session
    else:
        progress = session["progress"]
        progress[vocab] = 0
        session["progress"] = progress

    # Pass feedback and the next question to the template
    feedback = {
        "is_correct": is_correct,
        "user_answer": user_answer,
        "correct_answer": correct_answer
    }
    return render_template("quiz.html", current_question=None, feedback=feedback)

@app.route("/results")
def results():
    # Calculate results
    correct = sum(
        1 for vocab, progress in session["progress"].items()
        if progress >= session["num_to_mastered"]
    )
    total = len(session["questions"])
    results = [
        {
            "vocab": card["vocab"],
            "user_answer": session["progress"][card["vocab"]],
            "correct_answer": card["definition"],
        }
        for card in session["questions"]
    ]

    return render_template("result.html", correct=correct, total=total, results=results)

if __name__ == "__main__":
    app.run(debug=True)
