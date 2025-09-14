import streamlit as st
import json
from evaluator import HybridEvaluator, InterviewReportGenerator
from questions_storage import QuestionStorageAgent
from questions_agent import QuestionBankAgent, QuestionGeneratorAgent
import time

st.set_page_config(
    page_title="Excel Mock Interviewer",
    page_icon="📊"
)

def load_questions():
    """Load questions from JSON file or create default questions"""
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default questions if file doesn't exist
        return [
            {
                "id": 1,
                "question": "What Excel function would you use to sum values in range A1:A10?",
                "type": "formula",
                "keywords": ["SUM", "formula"],
                "difficulty": "basic"
            },
            {
                "id": 2,
                "question": "How would you remove duplicate values from a dataset in Excel?",
                "type": "concept", 
                "keywords": ["remove duplicates", "data", "filter"],
                "difficulty": "intermediate"
            },
            {
                "id": 3,
                "question": "Explain how VLOOKUP works and when you'd use it.",
                "type": "concept",
                "keywords": ["VLOOKUP", "lookup", "table", "match"],
                "difficulty": "intermediate"
            },
            {
                "id": 4,
                "question": "What's the difference between absolute and relative cell references?",
                "type": "concept",
                "keywords": ["absolute", "relative", "$"],
                "difficulty": "basic"
            },
            {
                "id": 5,
                "question": "How would you create a pivot table for data analysis?",
                "type": "concept",
                "keywords": ["pivot table", "data analysis"],
                "difficulty": "intermediate"
            },
            {
                "id": 6,
                "question": "How would you use SUMIF to calculate conditional totals?",
                "type": "formula",
                "keywords": ["SUMIF", "conditional"],
                "difficulty": "intermediate"
            }
        ]

# Initialize evaluator
@st.cache_resource
def get_evaluator():
    return HybridEvaluator(api_key=st.secrets.get("GEMINI_API_KEY"))

def main():
    st.title("🤖 AI Excel Mock Interviewer")
    
    # Initialize session state first
    if 'evaluations' not in st.session_state:
        st.session_state.evaluations = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'interview_started' not in st.session_state:
        st.session_state.interview_started = False
    if 'selected_questions' not in st.session_state:
        st.session_state.selected_questions = None
    if 'question_manager' not in st.session_state:
        st.session_state.question_manager = None
    
    # Get evaluator
    evaluator = get_evaluator()
    
    # Role selection and question setup
    if not st.session_state.interview_started:
        st.write("### Welcome to the AI Excel Mock Interviewer!")
        st.write("This interview will assess your Excel skills across different areas.")
        
        # Get role from user
        role = st.selectbox("Select your target role:", ["finance", "operations", "data_analytics"])
        
        if st.button("Start Interview"):
            # Use the proper agent structure
            try:
                storage_agent = QuestionStorageAgent()
                
                # Get best questions for the role
                selected_questions = storage_agent.get_best_questions(role, count=6)
                
                # If not enough stored questions, use defaults
                if len(selected_questions) < 3:
                    selected_questions = load_questions()
                
                st.session_state.selected_questions = selected_questions
                st.session_state.question_manager = storage_agent
                
            except Exception as e:
                # Fallback to default questions
                st.session_state.selected_questions = load_questions()
                st.session_state.question_manager = None
            
            st.session_state.interview_started = True
            st.rerun()
    
    else:
        # Interview is in progress
        questions = st.session_state.selected_questions
        
        if st.session_state.current_question < len(questions):
            # Show progress
            progress = (st.session_state.current_question) / len(questions)
            st.progress(progress)
            
            # Show current question
            question = questions[st.session_state.current_question]
            st.write(f"**Question {st.session_state.current_question + 1} of {len(questions)}**")
            st.write(f"**{question['question']}**")
            
            # Text area for response
            response = st.text_area(
                "Your answer:", 
                key=f"q_{st.session_state.current_question}",
                height=150,
                placeholder="Please provide your detailed answer here..."
            )
            
            # Submit button
            if st.button("Submit Answer", type="primary"):
                if response.strip():
                    # Get AI evaluation
                    with st.spinner("AI is reviewing your answer..."):
                        evaluation = evaluator.evaluate_comprehensive(question, response)
                    
                    # Store evaluation
                    st.session_state.evaluations.append(evaluation)
                    
                    # Update question bank learning (if available)
                    if st.session_state.question_manager:
                        try:
                            st.session_state.question_manager.update_question_performance(
                                question['id'], 
                                evaluation['score']
                            )
                        except Exception as e:
                            # Silently continue if update fails
                            pass 

                    # Show success message
                    st.success("✅ Answer submitted successfully!")
                    
                    # Auto-advance to next question
                    st.session_state.current_question += 1
                    
                    # Small delay then move to next
                    time.sleep(0.5)
                    st.rerun()
                            
                else:
                    st.error("Please provide an answer before submitting.")
        
        else:
            # Interview complete - Generate final report
            # st.write("## 🎉 Interview Complete!")
            # st.balloons()
            
            # if st.session_state.evaluations:
            #     report_generator = InterviewReportGenerator()
            #     final_report = report_generator.generate_final_report(st.session_state.evaluations)
                
            #     st.write(f"### Overall Score: {final_report['overall_score']}/100")
            #     st.write(f"**Performance Level:** {final_report['performance_level']}")
            #     st.write(f"**Recommendation:** {final_report['recommendation']}")
                
            #     # Detailed breakdown
            #     col1, col2, col3 = st.columns(3)
            #     with col1:
            #         st.metric("Technical Accuracy", f"{final_report['detailed_scores']['technical_accuracy']}/100")
            #     with col2:
            #         st.metric("Depth of Understanding", f"{final_report['detailed_scores']['depth_of_understanding']}/100")
            #     with col3:
            #         st.metric("Practical Application", f"{final_report['detailed_scores']['practical_application']}/100")
                
            #     # Additional report details
            #     if final_report.get('strengths_summary'):
            #         st.write("### 💪 Key Strengths")
            #         for strength in final_report['strengths_summary']:
            #             st.write(f"• {strength}")
                
            #     if final_report.get('improvement_areas'):
            #         st.write("### 📈 Areas for Improvement")
            #         for improvement in final_report['improvement_areas']:
            #             st.write(f"• {improvement}")


            # Interview complete - Generate final report
            st.write("## 📊 Interview Assessment Complete")

            if st.session_state.evaluations:
                report_generator = InterviewReportGenerator()

                # Get role from session or default
                role = getattr(st.session_state, 'selected_role', 'general')
                final_report = report_generator.generate_final_report(st.session_state.evaluations, role)

                # Executive Decision Box
                decision = final_report['hiring_decision']['decision']

                if decision == "STRONG HIRE":
                    st.success(f"**{decision}** - Score: {final_report['overall_score']}/100")
                elif decision == "CONDITIONAL HIRE":
                    st.warning(f"**{decision}** - Score: {final_report['overall_score']}/100")
                else:
                    st.error(f"**{decision}** - Score: {final_report['overall_score']}/100")

                # Executive Summary
                st.write("### Executive Summary")
                st.write(final_report['executive_summary'])

                # Quick Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Technical Skills", f"{final_report['detailed_scores']['technical_accuracy']}/100")
                with col2:
                    st.metric("Depth of Knowledge", f"{final_report['detailed_scores']['depth_of_understanding']}/100")
                with col3:
                    st.metric("Practical Application", f"{final_report['detailed_scores']['practical_application']}/100")

                # Critical Issues (if any)
                if final_report.get('critical_gaps'):
                    st.write("### ⚠️ Critical Issues")
                    for gap in final_report['critical_gaps']:
                        st.write(f"• {gap}")

                # Hiring Decision Rationale
                st.write("### Decision Rationale")
                st.write(final_report['recommendation_rationale'])

                # Next Steps
                st.write("### Recommended Next Steps")
                for step in final_report['next_steps']:
                    st.write(f"✓ {step}")



                            # Restart option
                if st.button("Start New Interview"):
                    # Reset all session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            else:
                st.error("No evaluations found. Please restart the interview.")

if __name__ == "__main__":
    main()