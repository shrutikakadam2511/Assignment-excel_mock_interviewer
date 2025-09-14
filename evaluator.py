import json
from typing import Dict, List, Any
import os
import re
import streamlit as st
import google.generativeai as genai

class AIAnswerReviewer:
    def __init__(self, api_key: str = None):
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def review_answer(self, question: Dict, response: str) -> Dict[str, Any]:
        """Main function to review and evaluate answers using AI"""
        
        # Create evaluation prompt
        prompt = self._create_evaluation_prompt(question, response)
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            ai_response = response.text
            return self._parse_ai_evaluation(ai_response)

        except Exception as e:
            # Fallback to rule-based evaluation
            return self._fallback_evaluation(question, response, str(e))
    
    def _get_system_prompt(self) -> str:
        """System prompt that defines the AI's role as Excel interviewer"""
        return """
        You are an expert Excel interviewer evaluating candidate responses. 
        
        Your job is to:
        1. Assess technical accuracy of Excel knowledge
        2. Evaluate depth of understanding
        3. Check for practical application skills
        4. Provide constructive feedback
        
        Rate answers on a scale of 0-100 and provide specific feedback.
        
        Format your response as JSON:
        {
            "score": 85,
            "technical_accuracy": 90,
            "depth": 80,
            "practical_application": 85,
            "strengths": ["List specific strengths"],
            "improvements": ["List areas for improvement"],
            "overall_feedback": "Brief overall assessment"
        }
        """
    
    def _create_evaluation_prompt(self, question: Dict, response: str) -> str:
        """Create specific evaluation prompt for the question and answer"""
    
        question_text = question.get('question', '')
        question_type = question.get('type', 'general')  
        difficulty = question.get('difficulty', 'medium')
        expected_keywords = question.get('keywords', [])
    
        # Include system prompt in the main prompt for Gemini
        prompt = f"""
    You are an expert Excel interviewer evaluating candidate responses.
    
    Your job is to:
    1. Assess technical accuracy of Excel knowledge
    2. Evaluate depth of understanding  
    3. Check for practical application skills
    4. Provide constructive feedback
    
    Rate answers on a scale of 0-100 and provide specific feedback.
    
    EXCEL INTERVIEW QUESTION:
    Type: {question_type}
    Difficulty: {difficulty}
    Question: "{question_text}"
    
    CANDIDATE'S RESPONSE:
    "{response}"
    
    EVALUATION CRITERIA:
    - Technical accuracy of Excel functions/formulas mentioned
    - Depth of understanding shown
    - Practical application and problem-solving approach
    - Communication clarity
    
    {f"Expected concepts to cover: {', '.join(expected_keywords)}" if expected_keywords else ""}
    
    Please evaluate this response and provide detailed feedback in this EXACT JSON format:
    {{
        "score": 85,
        "technical_accuracy": 90,
        "depth": 80,
        "practical_application": 85,
        "strengths": ["List specific strengths"],
        "improvements": ["List areas for improvement"],
        "overall_feedback": "Brief overall assessment"
    }}
    
    Return ONLY the JSON, no other text.
    """
    
        return prompt

    
    def _parse_ai_evaluation(self, ai_response: str) -> Dict[str, Any]:
        """Parse the AI's evaluation response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            
            if json_match:
                evaluation_data = json.loads(json_match.group())
                
                # Ensure all required fields exist
                return {
                    'score': evaluation_data.get('score', 50),
                    'technical_accuracy': evaluation_data.get('technical_accuracy', 50),
                    'depth': evaluation_data.get('depth', 50),
                    'practical_application': evaluation_data.get('practical_application', 50),
                    'strengths': evaluation_data.get('strengths', []),
                    'improvements': evaluation_data.get('improvements', []),
                    'overall_feedback': evaluation_data.get('overall_feedback', 'Response evaluated'),
                    'evaluation_source': 'AI'
                }
            else:
                # If no JSON found, parse text response
                return self._parse_text_response(ai_response)
                
        except json.JSONDecodeError:
            return self._parse_text_response(ai_response)
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse non-JSON AI response"""
        lines = response.split('\n')
        
        # Extract score if mentioned
        score = 70  # default
        for line in lines:
            if 'score' in line.lower() or '/100' in line:
                numbers = re.findall(r'\d+', line)
                if numbers:
                    score = min(int(numbers[0]), 100)
                    break
        
        return {
            'score': score,
            'technical_accuracy': score,
            'depth': score - 10,
            'practical_application': score - 5,
            'strengths': ['AI provided detailed feedback'],
            'improvements': ['See detailed feedback below'],
            'overall_feedback': response[:200] + "..." if len(response) > 200 else response,
            'evaluation_source': 'AI_Text'
        }
    
    def _fallback_evaluation(self, question: Dict, response: str, error: str) -> Dict[str, Any]:
        """Fallback evaluation when AI fails"""
        # Enhanced rule-based evaluation as backup
        score = 40  # base score
    
        words = len(response.split())
        if words > 30:
            score += 25
        elif words > 15:
            score += 15
        elif words > 5:
            score += 10
    
        excel_functions = ['SUM', 'AVERAGE', 'VLOOKUP', 'IF', 'COUNT', 'PIVOT', 'INDEX', 'MATCH']
        found_functions = [func for func in excel_functions if func.lower() in response.lower()]
        if found_functions:
            score += 20
    
        if '=' in response or '()' in response:
            score += 15
    
        return {
        'score': min(score, 100),
        'technical_accuracy': min(score, 100),
        'depth': max(score - 10, 0),
        'practical_application': max(score - 5, 0),
        'strengths': ['Response provided'] + ([f'Mentioned: {", ".join(found_functions[:2])}'] if found_functions else []),
        'improvements': ['Could provide more detail', 'Add specific Excel function examples'],
        'overall_feedback': f'Enhanced fallback evaluation (Gemini API error: {error[:50]}...)',
        'evaluation_source': 'Enhanced_Fallback'
    }


# Enhanced Evaluator that combines AI and rule-based approaches
class HybridEvaluator:
    def __init__(self, api_key: str = None):
        self.ai_reviewer = AIAnswerReviewer(api_key)
        
    def evaluate_comprehensive(self, question: Dict, response: str) -> Dict[str, Any]:
        """Comprehensive evaluation using AI + rule-based backup"""
        
        # Get AI evaluation
        ai_eval = self.ai_reviewer.review_answer(question, response)
        
        # Add additional metrics
        word_count = len(response.split())
        char_count = len(response.strip())
        
        # Enhance with additional analysis
        enhanced_eval = {
            **ai_eval,
            'response_length': {
                'words': word_count,
                'characters': char_count,
                'quality': 'detailed' if word_count > 20 else 'brief' if word_count > 5 else 'minimal'
            },
            'timestamp': self._get_timestamp(),
            'question_id': question.get('id', 'unknown')
        }
        
        return enhanced_eval
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

class InterviewReportGenerator:
    def __init__(self):
        self.hiring_thresholds = {
            'finance': {'minimum_score': 75, 'critical_skills': ['lookup_functions', 'advanced_formulas']},
            'operations': {'minimum_score': 70, 'critical_skills': ['data_manipulation', 'basic_formulas']},
            'data_analytics': {'minimum_score': 80, 'critical_skills': ['data_analysis', 'advanced_formulas']}
        }
    
    def generate_final_report(self, evaluations: List[Dict], role: str = 'general') -> Dict[str, Any]:
        """Generate strict, concise hiring-focused report"""
        
        if not evaluations:
            return {"error": "No evaluations to report"}
        
        # Calculate scores
        avg_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
        technical_avg = sum(eval_data.get('technical_accuracy', 0) for eval_data in evaluations) / len(evaluations)
        depth_avg = sum(eval_data.get('depth', 0) for eval_data in evaluations) / len(evaluations)
        practical_avg = sum(eval_data.get('practical_application', 0) for eval_data in evaluations) / len(evaluations)
        
        # Strict hiring decision
        hiring_decision = self._make_hiring_decision(avg_score, role, evaluations)
        
        # Concise skills assessment
        skills_assessment = self._assess_critical_skills(evaluations)
        
        # Executive summary
        executive_summary = self._generate_executive_summary(avg_score, hiring_decision, skills_assessment)
        
        return {
            'overall_score': round(avg_score, 1),
            'hiring_decision': hiring_decision,
            'executive_summary': executive_summary,
            'detailed_scores': {
                'technical_accuracy': round(technical_avg, 1),
                'depth_of_understanding': round(depth_avg, 1),
                'practical_application': round(practical_avg, 1)
            },
            'skills_breakdown': skills_assessment,
            'critical_gaps': self._identify_critical_gaps(evaluations, role),
            'recommendation_rationale': self._get_recommendation_rationale(avg_score, hiring_decision),
            'next_steps': self._get_next_steps(hiring_decision, avg_score)
        }
    
    def _make_hiring_decision(self, avg_score: float, role: str, evaluations: List[Dict]) -> Dict[str, Any]:
        """Make strict binary hiring decision"""
        
        threshold = self.hiring_thresholds.get(role, {}).get('minimum_score', 70)
        
        # Strict criteria
        if avg_score >= 85:
            decision = "STRONG HIRE"
            confidence = "High"
        elif avg_score >= threshold:
            decision = "CONDITIONAL HIRE"
            confidence = "Medium"
        elif avg_score >= 50:
            decision = "NO HIRE - TRAINING REQUIRED"
            confidence = "High"
        else:
            decision = "REJECT"
            confidence = "High"
        
        # Check for critical failures
        critical_failures = sum(1 for eval_data in evaluations if eval_data['score'] < 30)
        if critical_failures > len(evaluations) // 2:
            decision = "REJECT"
            confidence = "High"
        
        return {
            'decision': decision,
            'confidence': confidence,
            'meets_threshold': avg_score >= threshold
        }
    
    def _assess_critical_skills(self, evaluations: List[Dict]) -> Dict[str, str]:
        """Assess performance in critical Excel skill areas"""
        
        # Categorize by performance level
        skills = {
            'formula_knowledge': 'WEAK',
            'data_manipulation': 'WEAK',
            'analytical_thinking': 'WEAK',
            'attention_to_detail': 'WEAK'
        }
        
        total_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
        
        # Simple classification based on overall performance
        if total_score >= 80:
            for skill in skills:
                skills[skill] = 'STRONG'
        elif total_score >= 60:
            for skill in skills:
                skills[skill] = 'ADEQUATE'
        # else remains WEAK
        
        return skills
    
    def _identify_critical_gaps(self, evaluations: List[Dict], role: str) -> List[str]:
        """Identify critical skill gaps that block hiring"""
        
        gaps = []
        avg_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
        
        if avg_score < 30:
            gaps.append("CRITICAL: Lacks basic Excel formula knowledge")
        
        if avg_score < 50:
            gaps.append("MAJOR: Cannot perform essential Excel functions")
        
        # Check for specific failures
        low_scores = [eval_data for eval_data in evaluations if eval_data['score'] < 40]
        if len(low_scores) > 2:
            gaps.append("PATTERN: Consistent poor performance across multiple areas")
        
        # Role-specific gaps
        if role == 'finance' and avg_score < 70:
            gaps.append("FINANCE CRITICAL: Insufficient Excel skills for financial analysis")
        elif role == 'data_analytics' and avg_score < 75:
            gaps.append("ANALYTICS CRITICAL: Cannot handle data analysis requirements")
        
        return gaps[:3]  # Limit to top 3 critical gaps
    
    def _generate_executive_summary(self, avg_score: float, hiring_decision: Dict, skills: Dict) -> str:
        """Generate concise executive summary for hiring managers"""
        
        decision = hiring_decision['decision']
        
        if decision == "STRONG HIRE":
            return f"**RECOMMEND FOR HIRE**: Candidate demonstrates strong Excel proficiency (Score: {avg_score:.0f}/100). Ready for immediate deployment in Excel-dependent role."
        
        elif decision == "CONDITIONAL HIRE":
            return f"**CONDITIONAL HIRE**: Candidate has adequate Excel foundation (Score: {avg_score:.0f}/100) but requires targeted training in specific areas before role assignment."
        
        elif decision == "NO HIRE - TRAINING REQUIRED":
            return f"**NOT RECOMMENDED**: Candidate lacks essential Excel skills (Score: {avg_score:.0f}/100). Would require extensive training program before being job-ready."
        
        else:  # REJECT
            return f"**REJECT**: Candidate demonstrates insufficient Excel knowledge (Score: {avg_score:.0f}/100). Not suitable for Excel-dependent position even with training."
    
    def _get_recommendation_rationale(self, avg_score: float, hiring_decision: Dict) -> str:
        """Provide brief rationale for the hiring decision"""
        
        decision = hiring_decision['decision']
        
        if decision == "STRONG HIRE":
            return "Consistently high performance across all Excel skill areas. Candidate can contribute immediately."
        
        elif decision == "CONDITIONAL HIRE":
            return "Solid foundation with specific gaps that can be addressed through focused training within 2-4 weeks."
        
        elif decision == "NO HIRE - TRAINING REQUIRED":
            return "Fundamental Excel knowledge gaps require extensive training (6-8 weeks) which may not be cost-effective."
        
        else:
            return "Critical deficiencies in basic Excel operations. Training unlikely to bring candidate to required proficiency level."
    
    def _get_next_steps(self, hiring_decision: Dict, avg_score: float) -> List[str]:
        """Provide actionable next steps for hiring manager"""
        
        decision = hiring_decision['decision']
        
        if decision == "STRONG HIRE":
            return [
                "Proceed with job offer",
                "Assign to Excel-intensive projects immediately",
                "Consider for mentoring other team members"
            ]
        
        elif decision == "CONDITIONAL HIRE":
            return [
                "Offer position with 30-day Excel training requirement",
                "Assign Excel mentor for first month",
                "Re-evaluate after training completion"
            ]
        
        elif decision == "NO HIRE - TRAINING REQUIRED":
            return [
                "Do not proceed with hiring",
                "Consider for future openings after Excel certification",
                "Recommend Excel fundamentals course to candidate"
            ]
        
        else:
            return [
                "Reject application immediately",
                "Do not consider for Excel-dependent roles",
                "Focus recruitment efforts on other candidates"
            ]
