from django.shortcuts import render, get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Questionnaire, Question, Qtaker, Options
from .serializers import AnswerFormSerializer, QtakerSerializer
from .utils import get_next_question

@api_view(['GET', 'POST'])
def QtakerView(request):
    if request.method == "POST":
        serializer = QtakerSerializer(data=request.data)
        if serializer.is_valid():
            qtaker = serializer.save()
            skill = qtaker.skill
            
            # Get questionnaire based on skill level
            try:
                questionnaire = Questionnaire.objects.get(title=skill)
                all_questions = Question.objects.filter(questionnaire=questionnaire)
                
                # Define how many questions per session
                QUESTIONS_PER_SESSION = 4  # Adjust as needed
                
                if all_questions.exists():
                    # Randomize questions and limit to session count
                    question_count = all_questions.count()
                    questions_to_take = min(QUESTIONS_PER_SESSION, question_count)
                    
                    # Get randomized questions
                    randomized_questions = all_questions.order_by('?')[:questions_to_take]
                    randomized_question_ids = list(randomized_questions.values_list('id', flat=True))
                    
                    # Store the randomized question set in qtaker
                    qtaker.current_question_set = randomized_question_ids
                    qtaker.save()
                    
                    # Get the first question from randomized set
                    first_question = randomized_questions.first()
                    
                    response_data = {
                        "qtaker_id": qtaker.id,
                        "message": "User created successfully",
                        "skill": skill,
                        "total_questions_in_session": len(randomized_question_ids)
                    }
                    
                    if first_question:
                        response_data["question_id"] = first_question.id
                    
                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        "error": f"No questions found for skill level: {skill}"
                    }, status=status.HTTP_404_NOT_FOUND)
                    
            except Questionnaire.DoesNotExist:
                return Response({
                    "error": f"No questionnaire found for skill level: {skill}"
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # GET request - return form data
        serializer = QtakerSerializer()
        skills = [choice[0] for choice in Qtaker.chess_level]
        return Response({
            "form": serializer.data,
            "available_skills": skills,
            "message": "GET request successful"
        })


@api_view(['GET', 'POST'])
def quiz(request, Qtakerid, question_id):
    qtaker = get_object_or_404(Qtaker, id=Qtakerid)
    skill = qtaker.skill

    try:
        questionnaire = Questionnaire.objects.get(title=skill)
        
        # Check if we have a next_question_set (for starting new level)
        if hasattr(qtaker, 'next_question_set') and qtaker.next_question_set and len(qtaker.next_question_set) > 0:
            # Move next_question_set to current_question_set
            qtaker.current_question_set = qtaker.next_question_set
            qtaker.next_question_set = []  # Clear it
            qtaker.save()
            question_ids = qtaker.current_question_set
            current_question = Question.objects.get(id=question_ids[0])
            
        # Check if we have a current_question_set
        elif hasattr(qtaker, 'current_question_set') and qtaker.current_question_set and len(qtaker.current_question_set) > 0:
            question_ids = qtaker.current_question_set
            
            # Find current question in the set
            if question_id:
                try:
                    current_question = Question.objects.get(id=question_id)
                    if current_question.id not in question_ids:
                        current_question = Question.objects.get(id=question_ids[0])
                except (Question.DoesNotExist, ValueError):
                    current_question = Question.objects.get(id=question_ids[0])
            else:
                current_question = Question.objects.get(id=question_ids[0])
        else:
            # Fallback - create new set
            all_questions = Question.objects.filter(questionnaire=questionnaire)
            QUESTIONS_PER_SESSION = 4
            
            if all_questions.exists():
                question_count = all_questions.count()
                questions_to_take = min(QUESTIONS_PER_SESSION, question_count)
                
                randomized_questions = all_questions.order_by('?')[:questions_to_take]
                randomized_question_ids = list(randomized_questions.values_list('id', flat=True))
                
                qtaker.current_question_set = randomized_question_ids
                qtaker.save()
                
                current_question = randomized_questions.first()
            else:
                return Response({
                    "error": f"No questions found for skill level: {skill}"
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Find next question
        question_ids = qtaker.current_question_set
        current_index = question_ids.index(current_question.id)
        next_question_id = question_ids[current_index + 1] if current_index + 1 < len(question_ids) else None


        if request.method == "POST":
            serializer = AnswerFormSerializer(data=request.data, question=current_question)
            if serializer.is_valid():
                answer = serializer.validated_data["options"]
                return Response({
                    "answer_id": answer.pk,
                    "qtaker_id": qtaker.id,
                    "message": "Answer submitted successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # GET request - return current question and options
            serializer = AnswerFormSerializer(question=current_question)
            question_data = {
                "id": current_question.id,
                "text": current_question.question,
                "placement": current_question.placement,
                "options": list(Options.objects.filter(question=current_question).values('id', 'text', 'correct'))
            }
            
            response_data = {
                "qtaker": {
                    "id": qtaker.id,
                    "name": qtaker.name,
                    "skill": qtaker.skill,
                    "age": qtaker.age,
                    "current_score": qtaker.current_score  
                },
                "question": question_data,
                "questionnaire": {
                    "id": questionnaire.id,
                    "title": questionnaire.title
                },
                "form": serializer.data,
            }
            
            # Add next question info if available
            if next_question_id:
                response_data["next_question"] = {"id": next_question_id}
            
            return Response(response_data)

    except Questionnaire.DoesNotExist:
        return Response({
            "error": f"No questionnaire found for skill level: {skill}"
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def view_answer(request, Qtakerid, id):
    answer = get_object_or_404(Options, pk=id)
    question = answer.question
    qtaker = get_object_or_404(Qtaker, id=Qtakerid)
    
    correct_answer = Options.objects.filter(question=question, correct=True).first()
    
    # Get next question based on randomized set or fallback
    if hasattr(qtaker, 'current_question_set') and qtaker.current_question_set:
        question_ids = qtaker.current_question_set
        try:
            current_index = question_ids.index(question.id)
            next_question_id = question_ids[current_index + 1] if current_index + 1 < len(question_ids) else None
            next_question = Question.objects.get(id=next_question_id) if next_question_id else None
        except (ValueError, Question.DoesNotExist):
            next_question = None
    else:
        next_question = get_next_question(question)

    # Update database score if answer is correct
    if answer.correct:
        qtaker.current_score += 1
        qtaker.save()
    
    response_data = {
        "qtaker": {
            "id": qtaker.id,
            "name": qtaker.name,
            "skill": qtaker.skill
        },
        "answer": {
            "id": answer.id,
            "text": answer.text,
            "correct": answer.correct
        },
        "correct_answer": {
            "id": correct_answer.id if correct_answer else None,
            "text": correct_answer.text if correct_answer else None
        },
        "question": {
            "id": question.id,
            "text": question.question
        },
        "next_question": {
            "id": next_question.id if next_question else None,
            "text": next_question.question if next_question else None
        },
        "score": qtaker.current_score,
        "is_correct": answer.correct
    }
    
    return Response(response_data)


@api_view(['GET'])
def result(request, Qtakerid):
    qtaker = get_object_or_404(Qtaker, id=Qtakerid)
    original_skill = qtaker.skill
    
    try:
        questionnaire = Questionnaire.objects.get(title=original_skill)
        
        if hasattr(qtaker, 'current_question_set') and qtaker.current_question_set:
            total_questions_in_session = len(qtaker.current_question_set)
        else:
            total_questions_in_session = Question.objects.filter(questionnaire=questionnaire).count()
        
        percent = (qtaker.current_score * 100 / total_questions_in_session) if total_questions_in_session > 0 else 0
        qtaker.test_result = percent 
        
        passed = percent > 60
        next_skill = None
        next_questionnaire_data = None
        first_question_id = None  # Add this
        
        if passed:
            next_skill = Qtaker.get_next_skill(original_skill)
            
            if next_skill:
                try:
                    next_questionnaire = Questionnaire.objects.get(title=next_skill)
                    all_questions = Question.objects.filter(questionnaire=next_questionnaire)
                    
                    if all_questions.exists():
                        # Create the randomized question set for the NEXT level
                        QUESTIONS_PER_SESSION = 2
                        question_count = all_questions.count()
                        questions_to_take = min(QUESTIONS_PER_SESSION, question_count)
                        
                        randomized_questions = all_questions.order_by('?')[:questions_to_take]
                        randomized_question_ids = list(randomized_questions.values_list('id', flat=True))
                        
                        # Store the NEXT level question set in qtaker
                        qtaker.next_question_set = randomized_question_ids  # Use different field
                        first_question = randomized_questions.first()
                        first_question_id = first_question.id if first_question else None
                        
                        next_questionnaire_data = {
                            "id": next_questionnaire.id,
                            "title": next_questionnaire.title,
                            "first_question_id": first_question_id  # Include the actual question ID
                        }
                except Questionnaire.DoesNotExist:
                    next_questionnaire_data = None
        
        response_data = {
            "current_skill": original_skill,
            "current_questionnaire": {
                "id": questionnaire.id,
                "title": questionnaire.title
            },
            "qtaker": QtakerSerializer(qtaker).data,
            "score": qtaker.current_score,
            "total_questions": total_questions_in_session,
            "percentage": percent,
            "passed": passed,
            "next_skill": next_skill,
            "next_questionnaire": next_questionnaire_data
        }
        
        # Update qtaker only if there's a valid next skill
        if passed and next_skill:
            qtaker.skill = next_skill
        
        # Reset score but DON'T clear question set yet
        qtaker.current_score = 0
        qtaker.save()
        
        return Response(response_data)
        
    except Questionnaire.DoesNotExist:
        return Response({
            "error": f"No questionnaire found for skill level: {original_skill}"
        }, status=status.HTTP_404_NOT_FOUND)
