from django.shortcuts import render, get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Questionnaire, Question, Qtaker, Options
from .serializers import AnswerFormSerializer, QtakerSerializer
from .utils import get_next_question

@api_view(['GET', 'POST'])
def QtakerView(request):
    # print(f"Request method: {request.method}")
    # print(f"Request data: {request.data}")
    
    if request.method == "POST":
        print("Processing POST request")
        
        serializer = QtakerSerializer(data=request.data)
        if serializer.is_valid():
            print("Serializer is valid")
            qtaker = serializer.save()
            print(f"Qtaker created with ID: {qtaker.id}")

            skill = qtaker.skill
            
            # Get questionnaire based on skill level
            try:
                questionnaire = Questionnaire.objects.get(title=skill)
                questions = Question.objects.filter(questionnaire=questionnaire).order_by("placement")
                question = questions.first() if questions.exists() else None
                
                response_data = {
                    "qtaker_id": qtaker.id,
                    "message": "User created successfully",
                    "skill": skill
                }
                
                if question:
                    response_data["question_id"] = question.id
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Questionnaire.DoesNotExist:
                print(f"No questionnaire found for skill: {skill}")
                return Response({
                    "error": f"No questionnaire found for skill level: {skill}"
                }, status=status.HTTP_404_NOT_FOUND)
                
        else:
            print(f"Serializer errors: {serializer.errors}")
            return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # For GET request - use QtakerSerializer
        print("Processing GET request")
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
        questions = Question.objects.filter(questionnaire=questionnaire).order_by("placement")

        if question_id is None or question_id == 'null' or question_id == 'undefined':
            current_question = questions.first()
        else:
            current_question = get_object_or_404(Question, id=question_id)

        # print(f"Quiz view - Question ID: {question_id}, Database score: {qtaker.current_score}")

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
            
            return Response({
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
            })

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
    next_question = get_next_question(question)

    # Update database score if answer is correct
    if answer.correct:
        qtaker.current_score += 1
        qtaker.save()
        print(f"Updated database score to: {qtaker.current_score}")
    
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
        "score": qtaker.current_score,  # Use database score
        "is_correct": answer.correct
    }
    
    return Response(response_data)

@api_view(['GET'])
def result(request, Qtakerid):
    qtaker = get_object_or_404(Qtaker, id=Qtakerid)
    original_skill = qtaker.skill
    
    try:
        questionnaire = Questionnaire.objects.get(title=original_skill)
        total = Question.objects.filter(questionnaire=questionnaire).count()
        
        percent = qtaker.current_score * 100 / total if total > 0 else 0
        qtaker.test_result = percent 
        
        passed = percent > 60
        next_skill = None
        next_questionnaire_data = None
        
        if passed:
            next_skill = Qtaker.get_next_skill(original_skill)
            
            # Only proceed if there's actually a next skill (not None)
            if next_skill:
                try:
                    next_questionnaire = Questionnaire.objects.get(title=next_skill)
                    questions = Question.objects.filter(questionnaire=next_questionnaire).order_by("placement")
                    next_question = questions.first() if questions.exists() else None
                    
                    if next_question:
                        next_questionnaire_data = {
                            "id": next_questionnaire.id,
                            "title": next_questionnaire.title,
                            "first_question_id": next_question.id
                        }
                except Questionnaire.DoesNotExist:
                    # Next skill exists but no questionnaire found
                    next_questionnaire_data = None
        
        response_data = {
            "current_skill": original_skill,
            "current_questionnaire": {
                "id": questionnaire.id,
                "title": questionnaire.title
            },
            "qtaker": QtakerSerializer(qtaker).data,
            "score": qtaker.current_score,
            "total_questions": total,
            "percentage": percent,
            "passed": passed,
            "next_skill": next_skill,  # This will be None for expert level
            "next_questionnaire": next_questionnaire_data  # This will be None for expert level
        }
        
        print("=== BACKEND DEBUG ===")
        print(f"Original skill: {original_skill}")
        print(f"Next skill: {next_skill}")
        print(f"Next questionnaire: {next_questionnaire_data}")
        print("=====================")
        
        # Update qtaker only if there's a valid next skill
        if passed and next_skill:
            qtaker.skill = next_skill
        qtaker.current_score = 0
        qtaker.save()
        
        return Response(response_data)
        
    except Questionnaire.DoesNotExist:
        return Response({
            "error": f"No questionnaire found for skill level: {original_skill}"
        }, status=status.HTTP_404_NOT_FOUND)