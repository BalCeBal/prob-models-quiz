import streamlit as st
import pandas as pd
import time
import os

# --- Configurations ---
TIMEOUT_SECONDS = 300
EXAM_FOLDER = "exams"  # We will look for subfolders here

# --- Session Timeout ---
now = time.time()
if "last_active" in st.session_state:
    if now - st.session_state.last_active > TIMEOUT_SECONDS:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.session_state.last_active = now

# --- Styling ---
st.set_page_config(page_title="Probabilistic Models Prep", page_icon="🎲", layout="wide")
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { width: 100%; text-align: left; padding: 12px; border-radius: 8px; }
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

# --- Helper: Get Available Exams ---
def get_available_exams():
    if not os.path.exists(EXAM_FOLDER):
        os.makedirs(EXAM_FOLDER) # Create it if it doesn't exist
        return []
    # List subdirectories
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
            # Construct full path to image
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

# --- Sidebar & Selection ---
with st.sidebar:
    st.title("📚 Exam Selector")
    
    available_exams = get_available_exams()
    
    if not available_exams:
        st.warning(f"No exam folders found in '{EXAM_FOLDER}/'. Please create them.")
        st.stop()
        
    # Exam Dropdown
    # We use session state to track the *current* selection so we can detect changes
    if "selected_exam" not in st.session_state:
        st.session_state.selected_exam = available_exams[0]
        
    new_exam = st.selectbox("Choose Exam:", available_exams, index=available_exams.index(st.session_state.selected_exam))
    
    # If exam changed, reset everything
    if new_exam != st.session_state.selected_exam:
        st.session_state.selected_exam = new_exam
        for k in ["index", "score", "quiz_finished", "answer_submitted"]: 
            if k in st.session_state: del st.session_state[k]
        st.rerun()

    st.divider()

# --- Main App Logic ---
questions = load_exam_data(st.session_state.selected_exam)

if not questions:
    st.error(f"No questions found in {st.session_state.selected_exam}/questions.csv")
    st.stop()

# --- Initialize Session ---
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.total = len(questions)
    st.session_state.quiz_finished = False
    st.session_state.answer_submitted = False

# --- Navigation (Sidebar Part 2) ---
with st.sidebar:
    st.write(f"**Current:** {st.session_state.selected_exam}")
    
    q_numbers = list(range(1, len(questions) + 1))
    selected_q = st.selectbox("Jump to Question:", q_numbers, index=st.session_state.index)
    
    if selected_q - 1 != st.session_state.index:
        st.session_state.index = selected_q - 1
        st.session_state.answer_submitted = False
        st.rerun()

    st.write(f"**Score:** {st.session_state.score} / {st.session_state.total}")
    if st.button("🔄 Reset This Quiz"):
        for k in ["index", "score", "quiz_finished", "answer_submitted"]: del st.session_state[k]
        st.rerun()

# --- Quiz View ---
if st.session_state.quiz_finished:
    st.balloons()
    st.title(f"🎉 {st.session_state.selected_exam} Completed!")
    st.metric("Final Score", f"{st.session_state.score} / {st.session_state.total}")
    if st.button("Start Over"):
        for k in ["index", "score", "quiz_finished", "answer_submitted"]: del st.session_state[k]
        st.rerun()
    st.stop()

# --- Question Display ---
current_q = questions[st.session_state.index]
st.progress((st.session_state.index + 1) / st.session_state.total)
st.caption(f"Question {st.session_state.index + 1} of {st.session_state.total}")

col_q, col_opt = st.columns([3, 2])

with col_q:
    img_path = current_q['context_image']
    if img_path and os.path.exists(img_path):
        st.image(img_path, caption="Context")
            
    st.markdown(f"### {current_q['question']}")

with col_opt:
    if not st.session_state.answer_submitted:
        with st.form(key=f"q_{st.session_state.index}"):
            sel = st.radio("Answer:", current_q['options'], index=None)
            if st.form_submit_button("Submit"):
                if sel:
                    if str(sel).strip() == str(current_q['correct_answer']).strip():
                        st.session_state.score += 1
                        st.session_state.last_correct = True
                    else:
                        st.session_state.last_correct = False
                    st.session_state.answer_submitted = True
                    st.rerun()
    else:
        if st.session_state.last_correct: st.success("✅ Correct!")
        else: st.error(f"❌ Incorrect. Answer: {current_q['correct_answer']}")
        
        st.info(f"**Explanation:** {current_q['explanation']}")
        
        if st.button("Next ➡", type="primary"):
            st.session_state.answer_submitted = False
            if st.session_state.index + 1 < st.session_state.total:
                st.session_state.index += 1
            else:
                st.session_state.quiz_finished = True
            st.rerun()