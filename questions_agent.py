import json
import random
from typing import List, Dict, Any
from datetime import datetime

class QuestionBankAgent:
    def __init__(self):
        self.question_categories = {
            "basic_formulas": ["SUM", "AVERAGE", "COUNT", "MAX", "MIN"],
            "lookup_functions": ["VLOOKUP", "HLOOKUP", "INDEX", "MATCH"],
            "data_analysis": ["PIVOT", "FILTER", "SORT", "SUBTOTAL"],
            "advanced_formulas": ["IF", "SUMIF", "COUNTIF", "NESTED"],
            "data_manipulation": ["CONCATENATE", "TEXT", "DATE", "TIME"],
            "scenario_based": ["DASHBOARD", "REPORTING", "ANALYSIS"]
        }
        
        self.role_focus = {
            "finance": ["basic_formulas", "lookup_functions", "scenario_based"],
            "operations": ["data_analysis", "data_manipulation", "scenario_based"],
            "data_analytics": ["advanced_formulas", "data_analysis", "lookup_functions"]
        }
        
        self.initialize_base_questions()
    
    def initialize_base_questions(self):
        """Create foundational question templates"""
        self.base_questions = [
            {
                "template": "What function would you use to {action} in Excel?",
                "variations": {
                    "action": ["sum values in a range", "find the average", "count non-empty cells"]
                },
                "category": "basic_formulas",
                "difficulty": "basic"
            },
            {
                "template": "How would you {task} in a large dataset?",
                "variations": {
                    "task": ["remove duplicates", "find unique values", "filter specific criteria"]
                },
                "category": "data_analysis",
                "difficulty": "intermediate"
            },
            {
                "template": "Explain the difference between {concept1} and {concept2}.",
                "variations": {
                    "concept1": ["VLOOKUP", "absolute references", "SUMIF"],
                    "concept2": ["INDEX-MATCH", "relative references", "SUMIFS"]
                },
                "category": "advanced_formulas",
                "difficulty": "advanced"
            }
        ]
class QuestionGeneratorAgent:
    def __init__(self, question_bank: QuestionBankAgent):
        self.question_bank = question_bank
        self.used_questions = set()
        self.difficulty_progression = ["basic", "intermediate", "advanced"]
    
    def generate_interview_questions(self, role: str, count: int = 6) -> List[Dict]:
        """Generate personalized questions for specific role"""
        questions = []
        categories = self.question_bank.role_focus.get(role, ["basic_formulas"])
        
        # Ensure difficulty progression
        difficulty_distribution = {
            "basic": count // 3 + 1,
            "intermediate": count // 3 + 1, 
            "advanced": count // 3
        }
        
        for difficulty, num_questions in difficulty_distribution.items():
            for _ in range(num_questions):
                question = self._generate_single_question(categories, difficulty)
                if question and question['id'] not in self.used_questions:
                    questions.append(question)
                    self.used_questions.add(question['id'])
        
        return questions[:count]
    
    def _generate_single_question(self, categories: List[str], difficulty: str) -> Dict:
        """Generate a single question based on parameters"""
        # Mix of templates and pre-defined questions
        if random.choice([True, False]):
            return self._use_template_question(categories, difficulty)
        else:
            return self._get_curated_question(categories, difficulty)
    
    def _use_template_question(self, categories: List[str], difficulty: str) -> Dict:
        """Generate question from template"""
        suitable_templates = [
            t for t in self.question_bank.base_questions 
            if t['category'] in categories and t['difficulty'] == difficulty
        ]
        
        if not suitable_templates:
            return None
        
        template = random.choice(suitable_templates)
        question_text = self._fill_template(template)
        
        return {
            "id": hash(question_text) % 10000,
            "question": question_text,
            "type": "formula" if "function" in question_text.lower() else "concept",
            "category": template['category'],
            "difficulty": difficulty,
            "keywords": self._extract_keywords(question_text),
            "generated": True,
            "timestamp": datetime.now().isoformat()
        }
class QuestionStorageAgent:
    def __init__(self, storage_file: str = "dynamic_questions.json"):
        self.storage_file = storage_file
        self.load_questions()
    
    def store_question(self, question: Dict, performance_data: Dict = None):
        """Store question with performance metadata"""
        question_entry = {
            **question,
            "usage_count": 0,
            "avg_score": 0.0,
            "success_rate": 0.0,
            "effectiveness_score": 0.5,
            "created_date": datetime.now().isoformat(),
            "performance_history": []
        }
        
        if performance_data:
            question_entry.update(performance_data)
        
        self.questions.append(question_entry)
        self.save_questions()
    
    def update_question_performance(self, question_id: int, score: int, outcome: str = None):
        """Update question performance based on candidate results"""
        for question in self.questions:
            if question['id'] == question_id:
                # Update usage statistics
                question['usage_count'] += 1
                old_avg = question['avg_score']
                count = question['usage_count']
                question['avg_score'] = ((old_avg * (count - 1)) + score) / count
                
                # Track performance history
                question['performance_history'].append({
                    'score': score,
                    'timestamp': datetime.now().isoformat(),
                    'outcome': outcome
                })
                
                # Calculate effectiveness
                question['effectiveness_score'] = self._calculate_effectiveness(question)
                break
        
        self.save_questions()
    
    def get_best_questions(self, category: str = None, difficulty: str = None, count: int = 5) -> List[Dict]:
        """Retrieve most effective questions based on criteria"""
        filtered_questions = self.questions
        
        if category:
            filtered_questions = [q for q in filtered_questions if q.get('category') == category]
        if difficulty:
            filtered_questions = [q for q in filtered_questions if q.get('difficulty') == difficulty]
        
        # Sort by effectiveness score
        sorted_questions = sorted(filtered_questions, key=lambda x: x.get('effectiveness_score', 0), reverse=True)
        return sorted_questions[:count]
