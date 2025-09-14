import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from questions_agent import QuestionBankAgent, QuestionGeneratorAgent
from questions_storage import QuestionStorageAgent
from evaluator import HybridEvaluator

class InterviewOrchestrator:
    def __init__(self, api_key: str = None):
        """Initialize the interview orchestrator with all agents"""
        self.question_bank = QuestionBankAgent()
        self.question_generator = QuestionGeneratorAgent(self.question_bank)
        self.storage_agent = QuestionStorageAgent()
        self.evaluator = HybridEvaluator(api_key)
        
        # Interview state management
        self.current_interview = None
        self.interview_history = []
        
    def start_interview(self, 
                       role: str, 
                       candidate_info: Dict = None, 
                       question_count: int = 6) -> Dict[str, Any]:
        """Start a new interview session"""
        
        # Generate interview ID
        interview_id = self._generate_interview_id()
        
        # Get questions for the role
        questions = self._select_interview_questions(role, question_count)
        
        # Initialize interview session
        self.current_interview = {
            'interview_id': interview_id,
            'role': role,
            'candidate_info': candidate_info or {},
            'questions': questions,
            'responses': [],
            'evaluations': [],
            'start_time': datetime.now().isoformat(),
            'current_question_index': 0,
            'status': 'in_progress'
        }
        
        # Store new generated questions if any
        for question in questions:
            if question.get('generated', False):
                self.storage_agent.store_question(question)
        
        return {
            'interview_id': interview_id,
            'total_questions': len(questions),
            'first_question': questions[0] if questions else None,
            'status': 'started'
        }
    
    def _select_interview_questions(self, role: str, count: int) -> List[Dict]:
        """Intelligently select questions for the interview"""
        
        # Try to get best questions from storage first
        stored_questions = self.storage_agent.get_best_questions(role, count)
        
        # If we don't have enough effective questions, generate new ones
        if len(stored_questions) < count:
            needed_count = count - len(stored_questions)
            generated_questions = self.question_generator.generate_interview_questions(
                role, needed_count
            )
            
            # Combine stored and generated questions
            all_questions = stored_questions + generated_questions
        else:
            all_questions = stored_questions[:count]
        
        # Ensure variety in question types and difficulties
        balanced_questions = self._balance_question_selection(all_questions, count)
        
        return balanced_questions
    
    def _balance_question_selection(self, questions: List[Dict], target_count: int) -> List[Dict]:
        """Ensure balanced selection across types and difficulties"""
        
        if len(questions) <= target_count:
            return questions
        
        # Group questions by difficulty
        difficulty_groups = {
            'basic': [q for q in questions if q.get('difficulty') == 'basic'],
            'intermediate': [q for q in questions if q.get('difficulty') == 'intermediate'],
            'advanced': [q for q in questions if q.get('difficulty') == 'advanced']
        }
        
        # Aim for balanced distribution
        target_distribution = {
            'basic': target_count // 3 + (1 if target_count % 3 > 0 else 0),
            'intermediate': target_count // 3 + (1 if target_count % 3 > 1 else 0),
            'advanced': target_count // 3
        }
        
        selected_questions = []
        
        # Select from each difficulty level
        for difficulty, target_num in target_distribution.items():
            available = difficulty_groups.get(difficulty, [])
            # Sort by effectiveness and take the best ones
            available.sort(key=lambda x: x.get('effectiveness_score', 0), reverse=True)
            selected_questions.extend(available[:target_num])
        
        # If we still need more questions, fill with remaining best questions
        if len(selected_questions) < target_count:
            remaining = [q for q in questions if q not in selected_questions]
            remaining.sort(key=lambda x: x.get('effectiveness_score', 0), reverse=True)
            selected_questions.extend(remaining[:target_count - len(selected_questions)])
        
        return selected_questions[:target_count]
    
    def get_current_question(self) -> Optional[Dict]:
        """Get the current question for the active interview"""
        if not self.current_interview:
            return None
        
        questions = self.current_interview['questions']
        current_index = self.current_interview['current_question_index']
        
        if current_index < len(questions):
            return questions[current_index]
        
        return None
    
    def submit_answer(self, response: str) -> Dict[str, Any]:
        """Process candidate's answer and move to next question"""
        if not self.current_interview:
            return {'error': 'No active interview session'}
        
        current_question = self.get_current_question()
        if not current_question:
            return {'error': 'No current question available'}
        
        # Evaluate the response
        evaluation = self.evaluator.evaluate_comprehensive(current_question, response)
        
        # Store response and evaluation
        self.current_interview['responses'].append({
            'question_id': current_question['id'],
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
        self.current_interview['evaluations'].append(evaluation)
        
        # Update question performance in storage
        self.storage_agent.update_question_performance(
            current_question['id'],
            evaluation['score']
        )
        
        # Move to next question
        self.current_interview['current_question_index'] += 1
        
        # Check if interview is complete
        total_questions = len(self.current_interview['questions'])
        current_index = self.current_interview['current_question_index']
        
        if current_index >= total_questions:
            # Interview completed
            return self._complete_interview()
        else:
            # Return next question
            next_question = self.get_current_question()
            return {
                'status': 'continue',
                'evaluation': evaluation,
                'next_question': next_question,
                'progress': {
                    'current': current_index + 1,
                    'total': total_questions,
                    'percentage': ((current_index + 1) / total_questions) * 100
                }
            }
    
    def _complete_interview(self) -> Dict[str, Any]:
        """Complete the interview and generate final report"""
        if not self.current_interview:
            return {'error': 'No active interview to complete'}
        
        # Mark interview as completed
        self.current_interview['status'] = 'completed'
        self.current_interview['end_time'] = datetime.now().isoformat()
        
        # Generate comprehensive report
        final_report = self._generate_final_report()
        
        # Store interview in history
        self.interview_history.append(self.current_interview.copy())
        
        # Clear current interview
        interview_data = self.current_interview
        self.current_interview = None
        
        return {
            'status': 'completed',
            'interview_id': interview_data['interview_id'],
            'final_report': final_report,
            'total_time': self._calculate_interview_duration(interview_data)
        }
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive interview report"""
        evaluations = self.current_interview['evaluations']
        
        if not evaluations:
            return {'error': 'No evaluations available'}
        
        # Calculate overall metrics
        total_score = sum(eval_data['score'] for eval_data in evaluations)
        avg_score = total_score / len(evaluations)
        
        # Detailed score breakdown
        technical_scores = [eval_data.get('technical_accuracy', eval_data['score']) for eval_data in evaluations]
        depth_scores = [eval_data.get('depth', eval_data['score'] - 10) for eval_data in evaluations]
        practical_scores = [eval_data.get('practical_application', eval_data['score'] - 5) for eval_data in evaluations]
        
        technical_avg = sum(technical_scores) / len(technical_scores)
        depth_avg = sum(depth_scores) / len(depth_scores)
        practical_avg = sum(practical_scores) / len(practical_scores)
        
        # Collect strengths and improvements
        all_strengths = []
        all_improvements = []
        
        for eval_data in evaluations:
            all_strengths.extend(eval_data.get('strengths', []))
            all_improvements.extend(eval_data.get('improvements', []))
        
        # Remove duplicates and get top items
        unique_strengths = list(dict.fromkeys(all_strengths))[:5]
        unique_improvements = list(dict.fromkeys(all_improvements))[:5]
        
        # Performance classification
        performance_data = self._classify_performance(avg_score)
        
        # Question-wise analysis
        question_analysis = []
        for i, (question, evaluation) in enumerate(zip(self.current_interview['questions'], evaluations)):
            question_analysis.append({
                'question_number': i + 1,
                'question_text': question['question'][:60] + '...',
                'score': evaluation['score'],
                'difficulty': question.get('difficulty', 'unknown'),
                'category': question.get('category', 'unknown')
            })
        
        return {
            'overall_score': round(avg_score, 1),
            'performance_level': performance_data['level'],
            'recommendation': performance_data['recommendation'],
            'detailed_scores': {
                'technical_accuracy': round(technical_avg, 1),
                'depth_of_understanding': round(depth_avg, 1),
                'practical_application': round(practical_avg, 1)
            },
            'question_count': len(evaluations),
            'strengths_summary': unique_strengths,
            'improvement_areas': unique_improvements,
            'question_wise_performance': question_analysis,
            'score_distribution': {
                'highest_score': max(eval_data['score'] for eval_data in evaluations),
                'lowest_score': min(eval_data['score'] for eval_data in evaluations),
                'consistency': self._calculate_consistency(evaluations)
            },
            'role_specific_insights': self._generate_role_insights()
        }
    
    def _classify_performance(self, avg_score: float) -> Dict[str, str]:
        """Classify performance level and provide recommendation"""
        if avg_score >= 90:
            return {
                'level': 'Exceptional',
                'recommendation': 'Strong hire - candidate demonstrates exceptional Excel proficiency'
            }
        elif avg_score >= 80:
            return {
                'level': 'Excellent', 
                'recommendation': 'Recommend for hire - strong Excel skills with minor areas for improvement'
            }
        elif avg_score >= 70:
            return {
                'level': 'Good',
                'recommendation': 'Consider for hire - solid Excel foundation, may benefit from targeted training'
            }
        elif avg_score >= 60:
            return {
                'level': 'Average',
                'recommendation': 'Conditional hire - requires Excel training before role assignment'
            }
        elif avg_score >= 50:
            return {
                'level': 'Below Average',
                'recommendation': 'Not recommended - significant Excel skill gaps need addressing'
            }
        else:
            return {
                'level': 'Poor',
                'recommendation': 'Not suitable for Excel-dependent role - extensive training required'
            }
    
    def _calculate_consistency(self, evaluations: List[Dict]) -> str:
        """Calculate performance consistency across questions"""
        scores = [eval_data['score'] for eval_data in evaluations]
        if len(scores) < 2:
            return 'insufficient_data'
        
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        
        if std_dev <= 10:
            return 'very_consistent'
        elif std_dev <= 20:
            return 'consistent'
        elif std_dev <= 30:
            return 'somewhat_variable'
        else:
            return 'highly_variable'
    
    def _generate_role_insights(self) -> Dict[str, Any]:
        """Generate role-specific insights based on performance"""
        if not self.current_interview:
            return {}
        
        role = self.current_interview['role']
        evaluations = self.current_interview['evaluations']
        questions = self.current_interview['questions']
        
        # Analyze performance by category
        category_performance = {}
        for question, evaluation in zip(questions, evaluations):
            category = question.get('category', 'unknown')
            if category not in category_performance:
                category_performance[category] = []
            category_performance[category].append(evaluation['score'])
        
        # Calculate average performance per category
        category_averages = {
            cat: sum(scores) / len(scores) 
            for cat, scores in category_performance.items()
        }
        
        # Role-specific recommendations
        role_recommendations = self._get_role_specific_recommendations(role, category_averages)
        
        return {
            'role': role,
            'category_performance': category_averages,
            'role_specific_recommendations': role_recommendations,
            'strongest_area': max(category_averages, key=category_averages.get) if category_averages else None,
            'weakest_area': min(category_averages, key=category_averages.get) if category_averages else None
        }
    
    def _get_role_specific_recommendations(self, role: str, category_performance: Dict[str, float]) -> List[str]:
        """Generate role-specific recommendations"""
        recommendations = []
        
        if role == 'finance':
            if category_performance.get('lookup_functions', 0) < 70:
                recommendations.append("Focus on VLOOKUP and INDEX-MATCH for financial data lookups")
            if category_performance.get('advanced_formulas', 0) < 70:
                recommendations.append("Strengthen knowledge of SUMIF/COUNTIF for financial analysis")
            if category_performance.get('data_analysis', 0) < 70:
                recommendations.append("Practice pivot tables for financial reporting")
                
        elif role == 'operations':
            if category_performance.get('data_manipulation', 0) < 70:
                recommendations.append("Improve data cleaning and manipulation skills")
            if category_performance.get('data_analysis', 0) < 70:
                recommendations.append("Focus on data analysis techniques for operational insights")
            if category_performance.get('basic_formulas', 0) < 70:
                recommendations.append("Strengthen foundation in basic Excel formulas")
                
        elif role == 'data_analytics':
            if category_performance.get('advanced_formulas', 0) < 70:
                recommendations.append("Master advanced Excel formulas for data analysis")
            if category_performance.get('data_analysis', 0) < 70:
                recommendations.append("Enhance pivot table and data analysis skills")
            if category_performance.get('lookup_functions', 0) < 70:
                recommendations.append("Improve lookup functions for data integration")
        
        return recommendations
    
    def _calculate_interview_duration(self, interview_data: Dict) -> Dict[str, Any]:
        """Calculate total interview duration"""
        if 'start_time' not in interview_data or 'end_time' not in interview_data:
            return {'error': 'Missing timestamp data'}
        
        try:
            start_time = datetime.fromisoformat(interview_data['start_time'])
            end_time = datetime.fromisoformat(interview_data['end_time'])
            duration = end_time - start_time
            
            return {
                'total_seconds': duration.total_seconds(),
                'total_minutes': round(duration.total_seconds() / 60, 1),
                'formatted': str(duration).split('.')[0]  # Remove microseconds
            }
        except Exception as e:
            return {'error': f'Error calculating duration: {str(e)}'}
    
    def _generate_interview_id(self) -> str:
        """Generate unique interview ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        return f"interview_{timestamp}_{random_suffix}"
    
    def get_interview_status(self) -> Dict[str, Any]:
        """Get current interview status"""
        if not self.current_interview:
            return {'status': 'no_active_interview'}
        
        return {
            'status': self.current_interview['status'],
            'interview_id': self.current_interview['interview_id'],
            'role': self.current_interview['role'],
            'progress': {
                'current_question': self.current_interview['current_question_index'] + 1,
                'total_questions': len(self.current_interview['questions']),
                'percentage': ((self.current_interview['current_question_index']) / len(self.current_interview['questions'])) * 100
            },
            'elapsed_time': self._get_elapsed_time()
        }
    
    def _get_elapsed_time(self) -> Dict[str, Any]:
        """Calculate elapsed time for current interview"""
        if not self.current_interview or 'start_time' not in self.current_interview:
            return {'error': 'No active interview or missing start time'}
        
        try:
            start_time = datetime.fromisoformat(self.current_interview['start_time'])
            current_time = datetime.now()
            elapsed = current_time - start_time
            
            return {
                'seconds': elapsed.total_seconds(),
                'minutes': round(elapsed.total_seconds() / 60, 1),
                'formatted': str(elapsed).split('.')[0]
            }
        except Exception as e:
            return {'error': f'Error calculating elapsed time: {str(e)}'}
    
    def pause_interview(self) -> Dict[str, Any]:
        """Pause the current interview"""
        if not self.current_interview:
            return {'error': 'No active interview to pause'}
        
        self.current_interview['status'] = 'paused'
        self.current_interview['pause_time'] = datetime.now().isoformat()
        
        return {'status': 'paused', 'message': 'Interview paused successfully'}
    
    def resume_interview(self) -> Dict[str, Any]:
        """Resume a paused interview"""
        if not self.current_interview:
            return {'error': 'No interview to resume'}
        
        if self.current_interview['status'] != 'paused':
            return {'error': 'Interview is not in paused state'}
        
        self.current_interview['status'] = 'in_progress'
        self.current_interview['resume_time'] = datetime.now().isoformat()
        
        current_question = self.get_current_question()
        return {
            'status': 'resumed',
            'current_question': current_question,
            'message': 'Interview resumed successfully'
        }
    
    def get_interview_history(self, limit: int = 10) -> List[Dict]:
        """Get recent interview history"""
        return self.interview_history[-limit:] if self.interview_history else []
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get overall system analytics"""
        storage_analytics = self.storage_agent.get_analytics()
        
        return {
            'question_bank_stats': storage_analytics,
            'total_interviews_conducted': len(self.interview_history),
            'active_interview': self.current_interview is not None,
            'system_status': 'operational'
        }
