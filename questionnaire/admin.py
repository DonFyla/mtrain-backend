from django.contrib import admin
from django.utils.safestring import mark_safe

# Register your models here.
from .models import (
    Qtaker,Question,Questionnaire,Options
)

@admin.register(Qtaker)
class QtakerAdmin(admin.ModelAdmin):
    list_display = ["name","age","email","skill","test_result","date_taken"]

class AnswerInline(admin.TabularInline):
    model = Options    

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["questionnaire", "question_preview", "placement", "created_at", "updated_at", "created_by"]
    inlines = [AnswerInline]
    
    # Add this method to display formatted question text
    def question_preview(self, obj):
        return mark_safe(obj.question)  # This renders the HTML content
    
    question_preview.short_description = "Question"  # Sets the column header
    

@admin.register(Questionnaire)   
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["title", "description", "created_at", "created_by"] 

