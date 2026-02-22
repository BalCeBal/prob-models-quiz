import streamlit as st
import pandas as pd
import os

# --- Styling ---
st.set_page_config(page_title="Probabilistic Models Prep", page_icon="🎲", layout="wide")
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { width: 100%; text-align: left; padding: 12px; border-radius: 8px; font-weight: bold; }
        .nav-btn>button { width: 100%; text-align: center; }
        .info-box { 
            background-color: #e8f4f8; 
            padding: 10px; 
            border-radius: 10px; 
            border-left: 5px solid #0077b6; 
            margin-bottom: 20px; 
            color: #000000;
        }
        .info-box h1, .info-box h2, .info-box h3, .info-box h4, .info-box h5 {
            color: #000000 !important;
        }
        img { max-width: 100%; border-radius: 5px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

EXAM_FOLDER = "exams"

# --- Helper: Get Available Exams ---
def get_available_exams():
    if not os.path.exists(EXAM_FOLDER):
        os.makedirs(EXAM_FOLDER)
        return []
    exams = [d for d in os.listdir(EXAM_FOLDER) if os.path.isdir(os.path.join(EXAM_FOLDER, d))]
    return sorted(exams)

# --- Load Data ---
@st.cache_data
def load_exam_data(exam_name):
    csv_path = os.path.join(EXAM_FOLDER, exam_name, "questions.csv")
    if not os.path.exists(csv_path):
        return []
    
    try:
        df = pd.read_csv(csv_path, sep=';').fillna({'context_image': ''})
        questions = []
        for _, row in df.iterrows():
            img_filename = str(row['context_image']).strip()
            full_img_path = ""
            if img_filename and img_filename.lower() != "nan":
                full_img_path = os.path.join(EXAM_FOLDER, exam_name, img_filename)

            questions.append({
                "id": row['id'],
                "question": row['question'],
                "options": str(row['options']).split('|'),
                "correct_answer": str(row['correct_answer']),
                "explanation": row['explanation'],
                "context_image": full_img_path
            })
        return questions
    except Exception as e:
        st.error(f"Error loading {exam_name}: {e}")
        return []

# --- 1. Sidebar Setup & Exam Selection ---
with st.sidebar:
    st.title("📚 Exam Selector")
    available_exams = get_available_exams()
    
    if not available_exams:
        st.warning(f"No exam folders found in '{EXAM_FOLDER}/'.")
        st.stop()
        
    if "selected_exam" not in st.session_state:
        st.session_state.selected_exam = available_exams[0]
        
    new_exam = st.selectbox("Choose Exam:", available_exams, index=available_exams.index(st.session_state.selected_exam))

    # Reset state if the exam changes
    if new_exam != st.session_state.selected_exam:
        st.session_state.selected_exam = new_exam
        for k in ["index", "user_answers", "submitted_questions", "quiz_submitted"]: 
            if k in st.session_state: del st.session_state[k]
        st.rerun()

    st.divider()

# Load specific exam questions
questions = load_exam_data(st.session_state.selected_exam)
if not questions:
    st.error(f"No questions found in {st.session_state.selected_exam}/questions.csv")
    st.stop()

# --- 2. Initialize Core Session Variables ---
if "index" not in st.session_state:
    st.session_state.index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}  # {question_index: selected_option}
if "submitted_questions" not in st.session_state:
    st.session_state.submitted_questions = set() # Track questions that have been checked
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

# --- 3. Sidebar Navigation & Actions ---
with st.sidebar:
    st.write(f"**Current:** {st.session_state.selected_exam}")
    
    total_q = len(questions)
    
    # Jump to question
    q_numbers = list(range(1, total_q + 1))
    selected_q = st.selectbox("Jump to Question:", q_numbers, index=st.session_state.index)
    if selected_q - 1 != st.session_state.index:
        st.session_state.index = selected_q - 1
        st.rerun()

    st.divider()

    # Submit or Score Display
    answered_q = len(st.session_state.submitted_questions)
    
    if not st.session_state.quiz_submitted:
        st.write(f"**Progress:** {answered_q} / {total_q} Answered")
        if st.button("✅ Finish & Review Quiz", type="primary"):
            st.session_state.quiz_submitted = True
            st.session_state.index = 0  # Jump back to Q1 for review
            st.rerun()
    else:
        # Calculate Final Score based on checked answers
        score = 0
        for idx, q in enumerate(questions):
            ans = str(st.session_state.user_answers.get(idx, "")).strip()
            corr = str(q['correct_answer']).strip()
            if ans == corr:
                score += 1
        st.title(f"🏆 Score: {score} / {total_q}")
        st.metric("Accuracy", f"{(score/total_q)*100:.1f}%")

    st.divider()
    
    if st.button("🔄 Reset This Quiz"):
        for k in ["index", "user_answers", "submitted_questions", "quiz_submitted"]: 
            if k in st.session_state: del st.session_state[k]
        st.rerun()

# --- 4. Main Content Area (Question Display) ---
q_idx = st.session_state.index
current_q = questions[q_idx]

st.progress((q_idx + 1) / total_q)
st.caption(f"Question {q_idx + 1} of {total_q}")

col_q, col_opt = st.columns([3, 2])

with col_q:
    img_path = current_q['context_image']
    if img_path and os.path.exists(img_path):
        st.image(img_path, caption="Context")
            
    st.markdown(f"### {current_q['question']}")

with col_opt:
    options = current_q['options']
    correct_ans = str(current_q['correct_answer']).strip()
    
    # Scenario A: Question has NOT been answered yet AND quiz is not finished
    if not st.session_state.quiz_submitted and q_idx not in st.session_state.submitted_questions:
        with st.form(key=f"form_{q_idx}"):
            # Check if there is a saved (but unchecked) answer
            saved_ans = st.session_state.user_answers.get(q_idx)
            radio_idx = options.index(saved_ans) if saved_ans in options else None
            
            sel = st.radio("Select your answer:", options, index=radio_idx)
            
            if st.form_submit_button("Check Answer", type="primary"):
                if sel:
                    st.session_state.user_answers[q_idx] = sel
                    st.session_state.submitted_questions.add(q_idx)
                    st.rerun()
                else:
                    st.warning("Please select an answer before checking.")
                    
    # Scenario B: Question HAS been answered OR the whole quiz is finished (Review Mode)
    else:
        saved_ans = str(st.session_state.user_answers.get(q_idx, "No Answer Provided")).strip()
        
        st.write("#### Result:")
        if saved_ans == correct_ans:
            st.success(f"**Your Answer:** {saved_ans} (✅ Correct!)")
        else:
            st.error(f"**Your Answer:** {saved_ans}")
            st.success(f"**Correct Answer:** {correct_ans}")
            
        st.info(f"**Explanation:** {current_q['explanation']}")

    # --- 5. Navigation Buttons (Now inside col_opt) ---
    st.markdown("<br>", unsafe_allow_html=True) # Adds a little bit of spacing
    col_prev, col_next = st.columns(2)

    with col_prev:
        if q_idx > 0:
            if st.button("⬅ Previous", use_container_width=True):
                st.session_state.index -= 1
                st.rerun()

    with col_next:
        if q_idx < total_q - 1:
            # Highlight the "Next" button if the current question has been answered
            btn_type = "primary" if q_idx in st.session_state.submitted_questions else "secondary"
            if st.button("Next ➡", use_container_width=True, type=btn_type):
                st.session_state.index += 1
                st.rerun()