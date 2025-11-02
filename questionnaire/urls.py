from django.urls import path
from . import views

urlpatterns = [
    path('api/qtaker/', views.QtakerView, name='qtaker-create'),
    path('api/quiz/<int:Qtakerid>/<int:question_id>/', views.quiz, name='quiz_question'),
    path('api/answer/<int:Qtakerid>/<int:id>/', views.view_answer, name='quiz_answer'),
    path('api/result/<int:Qtakerid>/', views.result, name='result'),
]
