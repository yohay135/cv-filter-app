import streamlit as st
import os
import shutil
import tempfile
from PyPDF2 import PdfReader
import docx
from datetime import datetime
from pathlib import Path
from fuzzywuzzy import fuzz

st.set_page_config(page_title="סינון קורות חיים", layout="wide")
st.markdown("<h1 style='text-align: right;'>📄 סינון קבצי קורות חיים לפי דרישות</h1>", unsafe_allow_html=True)

# קלטים מהמשתמש
requirements_input = st.text_input("הכנס דרישות (מופרדות בפסיק):", "python, sql, excel")
requirements = [r.strip().lower() for r in requirements_input.split(",") if r.strip()]
threshold = st.slider("סף ההתאמות מינימלי:", min_value=1, max_value=len(requirements), value=2)
uploaded_files = st.file_uploader("העלה קבצי PDF או DOCX", type=["pdf", "docx"], accept_multiple_files=True)

# פונקציות עזר
def read_pdf(file):
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.lower()

def read_docx(file):
    doc = docx.Document(file)
    return " ".join(para.text for para in doc.paragraphs).lower()

def get_rating_label(score, max_score, threshold):
    if score == max_score:
        return "התאמה מעולה 💎", "#4CAF50"
    elif score >= threshold:
        return "התאמה חלקית ✅", "#FF9800"
    else:
        return "לא מתאים ❌", "#F44336"

results = []
cv_files = []
max_score = len(requirements)

if st.button("🔍 סנן קורות חיים"):
    if not uploaded_files:
        st.warning("לא הועלו קבצים.")
    else:
        for file in uploaded_files:
            filename = file.name
            suffix = filename.split(".")[-1].lower()

            if suffix == "pdf":
                text = read_pdf(file)
            elif suffix == "docx":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    tmp.write(file.read())
                    tmp_path = tmp.name
                text = read_docx(tmp_path)
                os.remove(tmp_path)
            else:
                continue

            matches = [req for req in requirements if fuzz.partial_ratio(req, text) > 80]
            score = len(matches)
            rating, color = get_rating_label(score, max_score, threshold)

            cv_files.append({
                "name": filename,
                "score": score,
                "match_terms": matches,
                "buffer": file.getbuffer()
            })

            percentage = int((score / max_score) * 100)
            st.markdown(f"""
            <div style="background-color: #fff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; direction: rtl">
                <div style="display: flex; align-items: center;">
                    <div style="width: 70px; height: 70px; border-radius: 50%; background-color: {color}; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold; margin-left: 15px;">
                        {percentage}%
                    </div>
                    <div>
                        <div style="font-size: 18px;"><strong>{filename}</strong></div>
                        <div style="color: {color}; font-weight: bold;">{rating}</div>
                        <div>התאמות שנמצאו: {', '.join(matches) if matches else 'אין'}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # שמירה בסשן
        st.session_state["filtered"] = cv_files
        st.session_state["threshold"] = threshold
        st.session_state["max_score"] = max_score

# הורדה לשולחן העבודה רק לאחר סינון
if "filtered" in st.session_state:
    st.markdown("---")
    st.subheader("📁 הורדת קבצים מסוננים")
    choice = st.radio("מה ברצונך לשמור?", ["קבצים שעברו את הסף", "קבצים מושלמים בלבד"])

    if st.button("📥 הורד לשולחן העבודה"):
        threshold = st.session_state["threshold"]
        max_score = st.session_state["max_score"]
        filtered = st.session_state["filtered"]

        desktop = Path.home() / "Desktop"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = desktop / "קורות חיים" / f"סינון_{timestamp}"
        os.makedirs(base_dir, exist_ok=True)

        saved = 0
        if choice == "קבצים מושלמים בלבד":
            perfect_dir = base_dir / "מושלמים"
            os.makedirs(perfect_dir, exist_ok=True)
            for cv in filtered:
                if cv["score"] == max_score:
                    with open(perfect_dir / cv["name"], "wb") as f:
                        f.write(cv["buffer"])
                        saved += 1
        else:
            above_dir = base_dir / "עברו סף"
            os.makedirs(above_dir, exist_ok=True)
            for cv in filtered:
                if cv["score"] >= threshold:
                    with open(above_dir / cv["name"], "wb") as f:
                        f.write(cv["buffer"])
                        saved += 1

        if saved > 0:
            st.success("✅ הקבצים נשמרו בהצלחה על שולחן העבודה!")
        else:
            st.warning("⚠️ לא נמצאו קבצים תואמים לשמירה.")
