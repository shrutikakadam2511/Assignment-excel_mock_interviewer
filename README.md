# 📊 AI-Powered Excel Mock Interviewer

An AI-driven system to simulate **Excel technical interviews**.  
This tool evaluates candidate answers, provides feedback, and generates performance summaries — helping companies save time and standardize Excel skill assessments.

---

## 🚀 Features
- **Multi-turn interview flow**: Asks a series of Excel-related questions (Basics → Advanced → Scenario).
- **Answer evaluation**:
  - Rule-based evaluator (keywords + heuristics).
  - Optional LLM-powered evaluation (Gemini / OpenAI).
- **Stateful interview sessions**: Tracks candidate responses through the session.
- **Constructive feedback report**: Provides section-wise scores, strengths, weaknesses, and recommendations.
- **Frontend + Backend**:
  - Chat-like UI (React + Vite).
  - API (FastAPI) for evaluation and reporting.
- **Deployment ready**: Dockerized with `docker-compose`.

---

## 🏗️ Project Structure
excel-mock-interviewer/
├─ backend/
│ ├─ app/
│ │ ├─ main.py # FastAPI entry
│ │ ├─ evaluator.py # Evaluation logic
│ │ ├─ models.py # Pydantic schemas
│ │ ├─ questions.json # Question bank
│ ├─ requirements.txt
│ ├─ Dockerfile
├─ frontend/
│ ├─ web/
│ │ ├─ src/ # React components
│ │ ├─ package.json
│ ├─ Dockerfile
├─ docker-compose.yml
├─ README.md

👩‍💻 Author

Developed by Shrutika Kadam as part of an AI Engineering assignment project.
Live Demo: https://excel-mock-interviewe-wndl4hzsbnxccomunew5uo.streamlit.app/
