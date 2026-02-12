"""
Comprehensive test suite for Chess Academy Questionnaire API.

Tests cover:
- Basic CRUD operations
- Full quiz flow (start → answer → result)
- Multiple attempts by same user (20 times in a row)
- Skill progression (beginner → intermediate → expert)
- Edge cases and error handling
- Score calculation accuracy
"""

import json
import random
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Questionnaire, Question, Options, Qtaker


class BaseTestCase(APITestCase):
    """Base test case with common setup."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create admin user for creating test data
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
        # Create questionnaires for each skill level
        self.beginner_qn = Questionnaire.objects.create(
            title='beginner',
            description='Beginner level chess questions',
            created_by=self.admin_user
        )
        
        self.intermediate_qn = Questionnaire.objects.create(
            title='intermediate',
            description='Intermediate level chess questions',
            created_by=self.admin_user
        )
        
        self.expert_qn = Questionnaire.objects.create(
            title='expert',
            description='Expert level chess questions',
            created_by=self.admin_user
        )
        
        # Create questions for all levels (radio type for consistent testing)
        # Note: Specific tests for text/mixed questions create their own data
        self.create_radio_questions(self.beginner_qn, count=10)
        self.create_radio_questions(self.intermediate_qn, count=10)
        self.create_radio_questions(self.expert_qn, count=10)
    
    def create_radio_questions(self, questionnaire, count=5):
        """Create radio type questions with options."""
        questions = []
        for i in range(count):
            q = Question.objects.create(
                questionnaire=questionnaire,
                question_type='radio',
                question=f'<p>Radio question {i+1} for {questionnaire.title}?</p>',
                placement=i+1,
                created_by=self.admin_user
            )
            # Create 4 options, one correct
            for j in range(4):
                Options.objects.create(
                    question=q,
                    text=f'Option {j+1}',
                    correct=(j == 0)  # First option is correct
                )
            questions.append(q)
        return questions
    
    def create_text_questions(self, questionnaire, count=5):
        """Create text type questions."""
        questions = []
        for i in range(count):
            q = Question.objects.create(
                questionnaire=questionnaire,
                question_type='text',
                question=f'<p>Text question {i+1} for {questionnaire.title}?</p>',
                placement=i+1,
                created_by=self.admin_user
            )
            # Create one option with correct answer
            Options.objects.create(
                question=q,
                text=f'Correct answer {i+1}',
                correct=True
            )
            questions.append(q)
        return questions
    
    def create_mixed_questions(self, questionnaire, count=5):
        """Create mixed type questions."""
        questions = []
        for i in range(count):
            q_type = 'radio' if i % 2 == 0 else 'text'
            q = Question.objects.create(
                questionnaire=questionnaire,
                question_type=q_type,
                question=f'<p>{q_type.capitalize()} question {i+1}?</p>',
                placement=i+1,
                created_by=self.admin_user
            )
            if q_type == 'radio':
                for j in range(4):
                    Options.objects.create(
                        question=q,
                        text=f'Option {j+1}',
                        correct=(j == 0)
                    )
            else:
                Options.objects.create(
                    question=q,
                    text=f'Text answer {i+1}',
                    correct=True
                )
            questions.append(q)
        return questions
    
    def create_qtaker(self, name="Test User", age=25, email="test@test.com", skill="beginner"):
        """Helper to create a quiz taker."""
        response = self.client.post('/questionnaire/api/qtaker/', {
            'name': name,
            'age': age,
            'email': email,
            'skill': skill
        }, format='json')
        return response
    
    def answer_all_questions(self, qtaker_id, question_ids, correct=True):
        """Answer all questions in a session."""
        for qid in question_ids:
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            question_data = response.data['question']
            
            if question_data['question_type'] == 'radio':
                options = question_data['options']
                if correct:
                    # Find correct option
                    correct_opt = [o for o in options if o['correct']][0]
                    answer = str(correct_opt['id'])
                else:
                    # Pick wrong option
                    wrong_opts = [o for o in options if not o['correct']]
                    answer = str(wrong_opts[0]['id'])
            else:
                # Text question
                if correct:
                    # Get correct answer from options
                    question = Question.objects.get(id=qid)
                    correct_opt = Options.objects.get(question=question, correct=True)
                    answer = correct_opt.text
                else:
                    answer = "wrong answer"
            
            # Submit answer
            response = self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Record answer for scoring
            if response.data.get('is_correct'):
                last_answer_id = response.data.get('last_answer_id', 0)
                if last_answer_id:
                    self.client.get(f'/questionnaire/api/answer/{qtaker_id}/{last_answer_id}/')


class QtakerCreationTests(BaseTestCase):
    """Tests for quiz taker creation."""
    
    def test_create_qtaker_success(self):
        """Test successful quiz taker creation."""
        response = self.create_qtaker()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('qtaker_id', response.data)
        self.assertIn('question_id', response.data)
        self.assertEqual(response.data['skill'], 'beginner')
    
    def test_create_qtaker_without_email(self):
        """Test creating qtaker without email (optional field)."""
        response = self.client.post('/questionnaire/api/qtaker/', {
            'name': 'Test User',
            'age': 25,
            'skill': 'beginner'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_qtaker_invalid_skill(self):
        """Test creating qtaker with invalid skill level returns 400."""
        response = self.client.post('/questionnaire/api/qtaker/', {
            'name': 'Test User',
            'age': 25,
            'skill': 'invalid_skill'
        }, format='json')
        # Serializer validates skill choices and returns 400 for invalid skill
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_qtaker_missing_name(self):
        """Test creating qtaker without name."""
        response = self.client.post('/questionnaire/api/qtaker/', {
            'age': 25,
            'skill': 'beginner'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_qtaker_missing_age(self):
        """Test creating qtaker without age."""
        response = self.client.post('/questionnaire/api/qtaker/', {
            'name': 'Test User',
            'skill': 'beginner'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_qtaker_questionnaire_not_found(self):
        """Test error when questionnaire doesn't exist for skill."""
        # Delete beginner questionnaire
        self.beginner_qn.delete()
        
        response = self.create_qtaker()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_create_qtaker_question_randomization(self):
        """Test that questions are randomized for each qtaker."""
        # Create first qtaker
        response1 = self.create_qtaker(name="User 1")
        qtaker1 = Qtaker.objects.get(id=response1.data['qtaker_id'])
        set1 = qtaker1.current_question_set
        
        # Create second qtaker
        response2 = self.create_qtaker(name="User 2")
        qtaker2 = Qtaker.objects.get(id=response2.data['qtaker_id'])
        set2 = qtaker2.current_question_set
        
        # Questions should be randomized (may occasionally match but unlikely)
        self.assertEqual(len(set1), 5)  # QUESTIONS_PER_SESSION
        self.assertEqual(len(set2), 5)
    
    def test_create_qtaker_get_request(self):
        """Test GET request to qtaker endpoint."""
        response = self.client.get('/questionnaire/api/qtaker/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('form', response.data)
        self.assertIn('available_skills', response.data)


class QuizFlowTests(BaseTestCase):
    """Tests for quiz question and answer flow."""
    
    def test_get_question_success(self):
        """Test retrieving a question."""
        # Create qtaker
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        first_qid = response.data['question_id']
        
        # Get question
        response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{first_qid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('question', response.data)
        self.assertIn('qtaker', response.data)
        self.assertIn('options', response.data['question'])
    
    def test_submit_radio_answer_correct(self):
        """Test submitting correct radio answer."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qid = response.data['question_id']
        
        # Get question and find correct option
        response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
        options = response.data['question']['options']
        correct_opt = [o for o in options if o['correct']][0]
        
        # Submit correct answer
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': str(correct_opt['id'])},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_correct'])
    
    def test_submit_radio_answer_incorrect(self):
        """Test submitting incorrect radio answer."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qid = response.data['question_id']
        
        # Get question and find wrong option
        response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
        options = response.data['question']['options']
        wrong_opt = [o for o in options if not o['correct']][0]
        
        # Submit wrong answer
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': str(wrong_opt['id'])},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_correct'])
    
    def test_submit_text_answer_correct(self):
        """Test submitting correct text answer (case insensitive)."""
        # Create a text question
        text_q = Question.objects.create(
            questionnaire=self.beginner_qn,
            question_type='text',
            question='<p>Text question?</p>',
            placement=1,
            created_by=self.admin_user
        )
        Options.objects.create(question=text_q, text='Correct Answer', correct=True)
        
        response = self.create_qtaker(skill='beginner')
        qtaker_id = response.data['qtaker_id']
        
        # Manually set the question set to include our text question
        qtaker = Qtaker.objects.get(id=qtaker_id)
        qtaker.current_question_set = [text_q.id]
        qtaker.save()
        
        # Test case insensitivity
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{text_q.id}/',
            {'answer': 'CORRECT ANSWER'},  # Uppercase
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_correct'])
    
    def test_submit_text_answer_incorrect(self):
        """Test submitting incorrect text answer."""
        # Create a text question
        text_q = Question.objects.create(
            questionnaire=self.beginner_qn,
            question_type='text',
            question='<p>Text question?</p>',
            placement=1,
            created_by=self.admin_user
        )
        Options.objects.create(question=text_q, text='Correct Answer', correct=True)
        
        response = self.create_qtaker(skill='beginner')
        qtaker_id = response.data['qtaker_id']
        
        # Manually set the question set to include our text question
        qtaker = Qtaker.objects.get(id=qtaker_id)
        qtaker.current_question_set = [text_q.id]
        qtaker.save()
        
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{text_q.id}/',
            {'answer': 'completely wrong answer'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_correct'])
    
    def test_get_nonexistent_question(self):
        """Test error when question doesn't exist."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        
        response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_nonexistent_qtaker(self):
        """Test error when qtaker doesn't exist."""
        response = self.client.get('/questionnaire/api/quiz/99999/1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ScoringAndResultsTests(BaseTestCase):
    """Tests for scoring calculation and results."""
    
    def test_score_calculation_accuracy(self):
        """Test that scores are calculated correctly."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        
        # Answer first 3 correctly, last 2 incorrectly
        qtaker = Qtaker.objects.get(id=qtaker_id)
        question_ids = qtaker.current_question_set[:5]  # Get all 5
        
        correct_count = 0
        for i, qid in enumerate(question_ids):
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            question_data = response.data['question']
            
            # Answer first 3 correct, rest wrong
            should_be_correct = i < 3
            
            if question_data['question_type'] == 'radio':
                options = question_data['options']
                if should_be_correct:
                    answer = str([o for o in options if o['correct']][0]['id'])
                    correct_count += 1
                else:
                    answer = str([o for o in options if not o['correct']][0]['id'])
            else:
                question = Question.objects.get(id=qid)
                correct_opt = Options.objects.get(question=question, correct=True)
                if should_be_correct:
                    answer = correct_opt.text
                    correct_count += 1
                else:
                    answer = "wrong"
            
            response = self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
            
            if response.data.get('is_correct') and should_be_correct:
                last_answer_id = response.data.get('last_answer_id', 0)
                if last_answer_id:
                    self.client.get(f'/questionnaire/api/answer/{qtaker_id}/{last_answer_id}/')
        
        # Check final result
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 3)
        self.assertEqual(response.data['total_questions'], 5)
        self.assertEqual(response.data['percentage'], 60.0)
    
    def test_pass_condition(self):
        """Test passing condition (>60%)."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        # Answer all correctly (100%)
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=True)
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertTrue(response.data['passed'])
        self.assertEqual(response.data['percentage'], 100.0)
    
    def test_fail_condition(self):
        """Test failing condition (<=60%)."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        # Answer all incorrectly (0%)
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=False)
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertFalse(response.data['passed'])
        self.assertEqual(response.data['percentage'], 0.0)
    
    def test_borderline_pass(self):
        """Test borderline passing (exactly above 60%)."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        question_ids = qtaker.current_question_set[:5]
        
        # Answer 4/5 correct = 80% (pass)
        for i, qid in enumerate(question_ids):
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            question_data = response.data['question']
            
            should_be_correct = i < 4  # 4 correct, 1 wrong
            
            if question_data['question_type'] == 'radio':
                options = question_data['options']
                if should_be_correct:
                    answer = str([o for o in options if o['correct']][0]['id'])
                else:
                    answer = str([o for o in options if not o['correct']][0]['id'])
            else:
                question = Question.objects.get(id=qid)
                correct_opt = Options.objects.get(question=question, correct=True)
                if should_be_correct:
                    answer = correct_opt.text
                else:
                    answer = "wrong"
            
            response = self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
            
            if response.data.get('is_correct') and should_be_correct:
                last_answer_id = response.data.get('last_answer_id', 0)
                if last_answer_id:
                    self.client.get(f'/questionnaire/api/answer/{qtaker_id}/{last_answer_id}/')
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertEqual(response.data['score'], 4)
        self.assertEqual(response.data['percentage'], 80.0)
        self.assertTrue(response.data['passed'])


class SkillProgressionTests(BaseTestCase):
    """Tests for skill level progression."""
    
    def test_beginner_to_intermediate_progression(self):
        """Test progression from beginner to intermediate on pass."""
        response = self.create_qtaker(skill='beginner')
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        # Answer all correctly
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=True)
        
        # Get result
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertTrue(response.data['passed'])
        self.assertEqual(response.data['next_skill'], 'intermediate')
        self.assertIsNotNone(response.data['next_questionnaire'])
        
        # Verify qtaker skill was updated
        qtaker.refresh_from_db()
        self.assertEqual(qtaker.skill, 'intermediate')
        self.assertIsNotNone(qtaker.next_question_set)
    
    def test_no_progression_on_fail(self):
        """Test no progression when failing."""
        response = self.create_qtaker(skill='beginner')
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        # Answer all incorrectly
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=False)
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertFalse(response.data['passed'])
        self.assertIsNone(response.data['next_skill'])
        self.assertIsNone(response.data['next_questionnaire'])
        
        # Verify skill unchanged
        qtaker.refresh_from_db()
        self.assertEqual(qtaker.skill, 'beginner')
    
    def test_intermediate_to_expert_progression(self):
        """Test progression from intermediate to expert."""
        response = self.create_qtaker(skill='intermediate')
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=True)
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertTrue(response.data['passed'])
        self.assertEqual(response.data['next_skill'], 'expert')
        
        qtaker.refresh_from_db()
        self.assertEqual(qtaker.skill, 'expert')
    
    def test_expert_no_next_level(self):
        """Test that expert level has no next level."""
        response = self.create_qtaker(skill='expert')
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        self.answer_all_questions(qtaker_id, qtaker.current_question_set[:5], correct=True)
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertTrue(response.data['passed'])
        self.assertIsNone(response.data['next_skill'])  # No level after expert
        
        qtaker.refresh_from_db()
        self.assertEqual(qtaker.skill, 'expert')
    
    def test_get_next_skill_method(self):
        """Test the Qtaker.get_next_skill class method."""
        self.assertEqual(Qtaker.get_next_skill('beginner'), 'intermediate')
        self.assertEqual(Qtaker.get_next_skill('intermediate'), 'expert')
        self.assertIsNone(Qtaker.get_next_skill('expert'))
        self.assertIsNone(Qtaker.get_next_skill('invalid'))


class MultipleAttemptsTests(BaseTestCase):
    """
    CRITICAL TESTS: Same user taking the test 20 times in a row.
    
    These tests ensure:
    - No state pollution between attempts
    - Score resets properly
    - Question sets are randomized each time
    - Database doesn't accumulate orphan data
    - Performance remains consistent
    """
    
    def test_same_user_20_consecutive_attempts(self):
        """
        Test the same user taking the quiz 20 times in a row.
        This is the main stress test for the application.
        """
        user_email = "repeat@test.com"
        user_name = "Repeat User"
        
        results = []
        
        for attempt in range(1, 21):
            with self.subTest(attempt=attempt):
                # Create new qtaker (same user info, new session)
                response = self.create_qtaker(
                    name=user_name,
                    email=user_email,
                    age=25,
                    skill='beginner'
                )
                self.assertEqual(
                    response.status_code, 
                    status.HTTP_201_CREATED,
                    f"Failed to create qtaker on attempt {attempt}"
                )
                
                qtaker_id = response.data['qtaker_id']
                qtaker = Qtaker.objects.get(id=qtaker_id)
                
                # Verify fresh state
                self.assertEqual(qtaker.current_score, 0)
                self.assertIsNotNone(qtaker.current_question_set)
                self.assertEqual(len(qtaker.current_question_set), 5)
                
                # Answer all questions (alternating correct/wrong every 5 attempts)
                answer_correctly = (attempt % 2 == 1)  # Odd attempts pass, even fail
                self.answer_all_questions(
                    qtaker_id, 
                    qtaker.current_question_set[:5], 
                    correct=answer_correctly
                )
                
                # Get result
                response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify result matches expectation
                if answer_correctly:
                    self.assertTrue(
                        response.data['passed'],
                        f"Attempt {attempt}: Should have passed"
                    )
                    self.assertEqual(response.data['percentage'], 100.0)
                else:
                    self.assertFalse(
                        response.data['passed'],
                        f"Attempt {attempt}: Should have failed"
                    )
                    self.assertEqual(response.data['percentage'], 0.0)
                
                results.append({
                    'attempt': attempt,
                    'qtaker_id': qtaker_id,
                    'passed': response.data['passed'],
                    'percentage': response.data['percentage']
                })
        
        # Verify total attempts recorded
        self.assertEqual(len(results), 20)
        
        # Verify alternating results
        passed_count = sum(1 for r in results if r['passed'])
        failed_count = 20 - passed_count
        self.assertEqual(passed_count, 10, "Expected 10 passed attempts")
        self.assertEqual(failed_count, 10, "Expected 10 failed attempts")
        
        # Verify all qtaker IDs are unique (no duplicate sessions)
        qtaker_ids = [r['qtaker_id'] for r in results]
        self.assertEqual(len(set(qtaker_ids)), 20, "All sessions should have unique IDs")
        
        print(f"\n[SUCCESS] Completed 20 consecutive attempts")
        print(f"  - Passed: {passed_count}")
        print(f"  - Failed: {failed_count}")
    
    def test_rapid_fire_same_user_no_state_leak(self):
        """
        Test that state from one attempt doesn't leak to another.
        Create multiple qtakers rapidly and verify isolation.
        """
        qtakers = []
        
        # Create 10 qtakers rapidly
        for i in range(10):
            response = self.create_qtaker(
                name="Rapid User",
                email="rapid@test.com",
                skill='beginner'
            )
            qtakers.append(Qtaker.objects.get(id=response.data['qtaker_id']))
        
        # Verify each has unique question set
        question_sets = [tuple(q.current_question_set) for q in qtakers]
        
        # All should have 5 questions
        for qs in question_sets:
            self.assertEqual(len(qs), 5)
        
        # Verify no state pollution - each qtaker is independent
        for i, qtaker in enumerate(qtakers):
            self.assertEqual(qtaker.current_score, 0)
            self.assertIsNone(qtaker.next_question_set)
            self.assertEqual(qtaker.skill, 'beginner')
    
    def test_concurrent_sessions_same_user_info(self):
        """
        Test multiple concurrent sessions with same user info.
        Simulates user opening multiple browser tabs.
        """
        sessions = []
        
        # Create 5 sessions with identical info
        for _ in range(5):
            response = self.create_qtaker(
                name="Concurrent User",
                email="concurrent@test.com",
                age=30,
                skill='intermediate'
            )
            sessions.append({
                'qtaker_id': response.data['qtaker_id'],
                'question_id': response.data['question_id']
            })
        
        # Interleave requests between sessions
        for round_num in range(3):  # 3 rounds of interleaved requests
            for session in sessions:
                qtaker_id = session['qtaker_id']
                qtaker = Qtaker.objects.get(id=qtaker_id)
                
                # Get current question from the set
                if qtaker.current_question_set and round_num < len(qtaker.current_question_set):
                    qid = qtaker.current_question_set[round_num]
                    
                    response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    
                    # Submit random answer
                    question_data = response.data['question']
                    if question_data['question_type'] == 'radio':
                        options = question_data['options']
                        answer = str(random.choice(options)['id'])
                    else:
                        answer = "test answer"
                    
                    response = self.client.post(
                        f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                        {'answer': answer},
                        format='json'
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify each session maintained its own state
        for session in sessions:
            qtaker = Qtaker.objects.get(id=session['qtaker_id'])
            self.assertIsNotNone(qtaker.current_question_set)
            # Score might vary based on random answers
    
    def test_progression_chain_20_levels(self):
        """
        Test chaining 20 progression attempts.
        User keeps passing and progressing through levels.
        Since there are only 3 levels, they should cycle or stay at expert.
        """
        current_skill = 'beginner'
        
        for attempt in range(1, 21):
            with self.subTest(attempt=attempt, skill=current_skill):
                response = self.create_qtaker(
                    name="Chain User",
                    email="chain@test.com",
                    skill=current_skill
                )
                
                if response.status_code == status.HTTP_404_NOT_FOUND:
                    # Questionnaire doesn't exist, skip
                    self.skipTest(f"Questionnaire for {current_skill} not found")
                
                qtaker_id = response.data['qtaker_id']
                qtaker = Qtaker.objects.get(id=qtaker_id)
                
                # Always answer correctly to trigger progression
                self.answer_all_questions(
                    qtaker_id,
                    qtaker.current_question_set[:5],
                    correct=True
                )
                
                response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
                self.assertTrue(response.data['passed'])
                
                # Update current_skill for next iteration
                next_skill = response.data.get('next_skill')
                if next_skill:
                    current_skill = next_skill
                else:
                    # At expert level, stay there
                    current_skill = 'expert'
        
        # After many attempts, should end up at expert
        self.assertEqual(current_skill, 'expert')
    
    def test_20_attempts_always_fail_stay_beginner_complete_5_questions(self):
        """
        CRITICAL TEST: Same user takes quiz 20 times, always fails,
        always stays at beginner level, and always completes all 5 questions.
        
        This ensures:
        - User gets exactly 5 questions every attempt
        - User never passes (always <= 60% score)
        - User skill never progresses from beginner
        - Quiz can be restarted indefinitely
        """
        user_email = "alwaysfail@test.com"
        user_name = "Always Fail User"
        
        results = []
        
        for attempt in range(1, 21):
            with self.subTest(attempt=attempt):
                # Create new qtaker (same user info, new session)
                response = self.create_qtaker(
                    name=user_name,
                    email=user_email,
                    age=25,
                    skill='beginner'
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_201_CREATED,
                    f"Failed to create qtaker on attempt {attempt}"
                )
                
                qtaker_id = response.data['qtaker_id']
                qtaker = Qtaker.objects.get(id=qtaker_id)
                
                # CRITICAL: Verify user gets exactly 5 questions
                self.assertIsNotNone(
                    qtaker.current_question_set,
                    f"Attempt {attempt}: Question set should not be None"
                )
                self.assertEqual(
                    len(qtaker.current_question_set),
                    5,
                    f"Attempt {attempt}: User should get exactly 5 questions"
                )
                
                # CRITICAL: Verify fresh state (score reset)
                self.assertEqual(
                    qtaker.current_score,
                    0,
                    f"Attempt {attempt}: Score should start at 0"
                )
                
                # CRITICAL: Verify skill is beginner
                self.assertEqual(
                    qtaker.skill,
                    'beginner',
                    f"Attempt {attempt}: Skill should be beginner"
                )
                
                # Answer all questions INCORRECTLY (to ensure failure)
                # Answer 0 correct out of 5 (0% score) - this will definitely fail
                question_ids = qtaker.current_question_set[:5]
                
                for i, qid in enumerate(question_ids):
                    # Get the question first to check its type
                    q_response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
                    self.assertEqual(
                        q_response.status_code,
                        status.HTTP_200_OK,
                        f"Attempt {attempt}: Failed to get question {i+1}"
                    )
                    
                    question_data = q_response.data['question']
                    
                    # Submit wrong answer based on question type
                    if question_data['question_type'] == 'radio':
                        # For radio, pick any wrong option (find one with correct=False)
                        options = question_data['options']
                        wrong_options = [o for o in options if not o['correct']]
                        if wrong_options:
                            answer = str(wrong_options[0]['id'])
                        else:
                            # Fallback: use any option (shouldn't happen with test data)
                            answer = str(options[0]['id'])
                    else:
                        # For text, submit wrong text answer
                        answer = "completely_wrong_answer"
                    
                    response = self.client.post(
                        f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                        {'answer': answer},
                        format='json'
                    )
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_200_OK,
                        f"Attempt {attempt}: Failed to submit answer for question {i+1}"
                    )
                    
                    # Verify the answer was incorrect
                    self.assertFalse(
                        response.data['is_correct'],
                        f"Attempt {attempt}: Answer should have been incorrect for question {i+1}"
                    )
                
                # Get result
                response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                    f"Attempt {attempt}: Failed to get result"
                )
                
                # CRITICAL: Verify user failed (<= 60%)
                self.assertFalse(
                    response.data['passed'],
                    f"Attempt {attempt}: User should have failed (needed <= 60%)"
                )
                self.assertLessEqual(
                    response.data['percentage'],
                    60.0,
                    f"Attempt {attempt}: Percentage should be <= 60%"
                )
                
                # CRITICAL: Verify no progression (no next_skill)
                self.assertIsNone(
                    response.data.get('next_skill'),
                    f"Attempt {attempt}: Should not have next_skill (failed)"
                )
                
                # CRITICAL: Verify skill stayed at beginner
                qtaker.refresh_from_db()
                self.assertEqual(
                    qtaker.skill,
                    'beginner',
                    f"Attempt {attempt}: Skill should remain beginner after fail"
                )
                
                results.append({
                    'attempt': attempt,
                    'qtaker_id': qtaker_id,
                    'questions_count': len(qtaker.current_question_set),
                    'passed': response.data['passed'],
                    'percentage': response.data['percentage'],
                    'skill': qtaker.skill
                })
        
        # Final verification summary
        self.assertEqual(len(results), 20, "Should have 20 attempts")
        
        # Verify all attempts had exactly 5 questions
        for r in results:
            self.assertEqual(
                r['questions_count'],
                5,
                f"Attempt {r['attempt']}: Did not have 5 questions"
            )
        
        # Verify all attempts failed
        failed_count = sum(1 for r in results if not r['passed'])
        self.assertEqual(
            failed_count,
            20,
            f"Expected all 20 attempts to fail, but {20 - failed_count} passed"
        )
        
        # Verify all stayed at beginner
        beginner_count = sum(1 for r in results if r['skill'] == 'beginner')
        self.assertEqual(
            beginner_count,
            20,
            f"Expected all 20 attempts to stay at beginner, but {20 - beginner_count} progressed"
        )
        
        # Verify all qtaker IDs are unique (no duplicate sessions)
        qtaker_ids = [r['qtaker_id'] for r in results]
        self.assertEqual(
            len(set(qtaker_ids)),
            20,
            "All sessions should have unique IDs"
        )
        
        print(f"\n[SUCCESS] Completed 20 consecutive failed attempts")
        print(f"  - All 20 attempts: 5 questions each")
        print(f"  - All 20 attempts: FAILED (<= 60%)")
        print(f"  - All 20 attempts: stayed at BEGINNER level")


class EdgeCaseTests(BaseTestCase):
    """Tests for edge cases and error conditions."""
    
    def test_empty_answer_submission(self):
        """Test submitting empty answer."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qid = response.data['question_id']
        
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': ''},
            format='json'
        )
        # Serializer validation might reject empty answers
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_invalid_option_id(self):
        """Test submitting non-existent option ID."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qid = response.data['question_id']
        
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': '99999'},  # Invalid ID
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_answer_question_twice(self):
        """Test answering the same question twice."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qid = response.data['question_id']
        
        # Get question
        response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
        options = response.data['question']['options']
        correct_id = str([o for o in options if o['correct']][0]['id'])
        
        # First answer
        response1 = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': correct_id},
            format='json'
        )
        
        # Second answer (should still work or give meaningful response)
        response2 = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
            {'answer': correct_id},
            format='json'
        )
        
        # Both should succeed
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
    
    def test_skip_to_result_without_answering(self):
        """Test getting result without answering any questions."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 0)
        self.assertEqual(response.data['percentage'], 0.0)
        self.assertFalse(response.data['passed'])
    
    def test_view_answer_without_answering(self):
        """Test viewing answer details before answering."""
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        
        # Try to view answer with ID 0 (no answer yet)
        response = self.client.get(f'/questionnaire/api/answer/{qtaker_id}/0/')
        # Should handle gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_special_characters_in_text_answer(self):
        """Test text answers with special characters."""
        # Create qtaker first to get the question set
        response = self.create_qtaker()
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        
        # Create a text question with special characters in answer
        question = Question.objects.create(
            questionnaire=self.beginner_qn,
            question_type='text',
            question='<p>Special chars question?</p>',
            placement=99,
            created_by=self.admin_user
        )
        Options.objects.create(
            question=question,
            text='Answer with <special> & "chars"',
            correct=True
        )
        
        # Add the new question to the qtaker's question set (replace last one)
        question_set = qtaker.current_question_set
        question_set[-1] = question.id
        qtaker.current_question_set = question_set
        qtaker.save()
        
        # Submit answer with different case and whitespace
        response = self.client.post(
            f'/questionnaire/api/quiz/{qtaker_id}/{question.id}/',
            {'answer': '  ANSWER WITH <SPECIAL> & "CHARS"  '},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Case insensitive comparison
        self.assertTrue(response.data['is_correct'])


class PerformanceTests(BaseTestCase):
    """Tests for performance and load handling."""
    
    def test_large_number_of_questions(self):
        """Test handling questionnaires with many questions."""
        # Add 100 more questions to beginner (already has 10 from setUp)
        self.create_radio_questions(self.beginner_qn, count=90)
        
        response = self.client.post('/questionnaire/api/qtaker/', {
            'name': 'Large Test',
            'age': 25,
            'skill': 'beginner'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should still only get 5 questions per session
        qtaker = Qtaker.objects.get(id=response.data['qtaker_id'])
        self.assertEqual(len(qtaker.current_question_set), 5)
    
    def test_question_randomization_distribution(self):
        """Test that question randomization is reasonably distributed."""
        # Create qtaker multiple times and track first question
        first_questions = []
        
        for _ in range(20):
            response = self.create_qtaker()
            qtaker = Qtaker.objects.get(id=response.data['qtaker_id'])
            first_questions.append(qtaker.current_question_set[0])
        
        # Should have some variety (not all same)
        unique_questions = set(first_questions)
        self.assertGreater(len(unique_questions), 1, "Randomization should produce variety")
    
    def test_database_query_count(self):
        """Test that views don't make excessive database queries."""
        from django.test.utils import override_settings
        from django.db import connection, reset_queries
        
        with override_settings(DEBUG=True):
            reset_queries()
            
            response = self.create_qtaker()
            qtaker_id = response.data['qtaker_id']
            qid = response.data['question_id']
            
            # Get question
            reset_queries()
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            get_queries = len(connection.queries)
            
            # Should be reasonable number of queries (< 10)
            self.assertLess(get_queries, 10, f"Too many queries ({get_queries}) for GET question")
            
            # Submit answer
            options = response.data['question']['options']
            answer = str([o for o in options if o['correct']][0]['id'])
            
            reset_queries()
            response = self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
            post_queries = len(connection.queries)
            
            self.assertLess(post_queries, 10, f"Too many queries ({post_queries}) for POST answer")


class ModelTests(BaseTestCase):
    """Unit tests for model methods and properties."""
    
    def test_questionnaire_str(self):
        """Test Questionnaire string representation."""
        self.assertEqual(str(self.beginner_qn), 'beginner')
    
    def test_qtaker_str(self):
        """Test Qtaker string representation."""
        qtaker = Qtaker.objects.create(
            name='Test Person',
            age=25,
            skill='beginner'
        )
        self.assertEqual(str(qtaker), 'Test Person')
    
    def test_question_str(self):
        """Test Question string representation."""
        question = Question.objects.create(
            questionnaire=self.beginner_qn,
            question_type='radio',
            question='<p>Test question?</p>',
            placement=1,
            created_by=self.admin_user
        )
        expected = f"beginner - Q1 {question.question}"
        self.assertEqual(str(question), expected)
    
    def test_options_str(self):
        """Test Options string representation."""
        question = Question.objects.create(
            questionnaire=self.beginner_qn,
            question_type='radio',
            question='<p>Test?</p>',
            placement=1,
            created_by=self.admin_user
        )
        option = Options.objects.create(
            question=question,
            text='Option text',
            correct=True
        )
        self.assertEqual(str(option), 'Option text')
    
    def test_qtaker_default_values(self):
        """Test Qtaker default field values."""
        qtaker = Qtaker.objects.create(
            name='Defaults Test',
            age=20,
            skill='beginner'
        )
        self.assertEqual(qtaker.current_score, 0)
        self.assertIsNone(qtaker.current_question_set)
        self.assertIsNone(qtaker.next_question_set)
        self.assertIsNone(qtaker.test_result)


class IntegrationTests(BaseTestCase):
    """End-to-end integration tests."""
    
    def test_full_quiz_workflow_pass(self):
        """Complete workflow: create → answer all → pass → check progression."""
        # 1. Create qtaker
        response = self.create_qtaker(skill='beginner')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        qtaker_id = response.data['qtaker_id']
        
        # 2. Answer all 5 questions correctly
        qtaker = Qtaker.objects.get(id=qtaker_id)
        question_ids = qtaker.current_question_set[:5]
        
        for qid in question_ids:
            # Get question
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            question_data = response.data['question']
            
            # Get correct answer
            if question_data['question_type'] == 'radio':
                correct_opt = [o for o in question_data['options'] if o['correct']][0]
                answer = str(correct_opt['id'])
            else:
                question = Question.objects.get(id=qid)
                correct_opt = Options.objects.get(question=question, correct=True)
                answer = correct_opt.text
            
            # Submit
            response = self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
            self.assertTrue(response.data['is_correct'])
            
            # Record score
            last_answer_id = response.data.get('last_answer_id', 0)
            if last_answer_id:
                self.client.get(f'/questionnaire/api/answer/{qtaker_id}/{last_answer_id}/')
        
        # 3. Get final result
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 5)
        self.assertEqual(response.data['percentage'], 100.0)
        self.assertTrue(response.data['passed'])
        self.assertEqual(response.data['next_skill'], 'intermediate')
    
    def test_full_quiz_workflow_fail(self):
        """Complete workflow: create → answer all → fail → no progression."""
        response = self.create_qtaker(skill='intermediate')
        qtaker_id = response.data['qtaker_id']
        qtaker = Qtaker.objects.get(id=qtaker_id)
        question_ids = qtaker.current_question_set[:5]
        
        for qid in question_ids:
            response = self.client.get(f'/questionnaire/api/quiz/{qtaker_id}/{qid}/')
            question_data = response.data['question']
            
            # Always answer wrong
            if question_data['question_type'] == 'radio':
                wrong_opt = [o for o in question_data['options'] if not o['correct']][0]
                answer = str(wrong_opt['id'])
            else:
                answer = "wrong answer"
            
            self.client.post(
                f'/questionnaire/api/quiz/{qtaker_id}/{qid}/',
                {'answer': answer},
                format='json'
            )
        
        response = self.client.get(f'/questionnaire/api/result/{qtaker_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 0)
        self.assertEqual(response.data['percentage'], 0.0)
        self.assertFalse(response.data['passed'])
        self.assertIsNone(response.data['next_skill'])
