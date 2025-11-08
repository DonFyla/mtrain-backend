from django import forms
from rest_framework import serializers
from .models import Qtaker, Options, Question, Questionnaire

class QtakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qtaker
        fields = ['id', 'name', 'age', 'email', 'skill', 'test_result']
        read_only_fields = ['test_result',"date_taken"]
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True}
        }
class QuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questionnaire
        fields = ['id', 'title', 'description', 'created_at', 'created_by']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'questionnaire', 'question', 'placement', 'created_at', 'created_by']

class OptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Options
        fields = ['id', 'question', 'text', 'correct']

class UserformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qtaker
        fields = ['name', 'age', 'email', 'skill']
        # No longer excluding test_result since it's read-only

class AnswerFormSerializer(serializers.ModelSerializer):
    options = serializers.PrimaryKeyRelatedField(
        queryset=Options.objects.all()
    )

    def __init__(self, *args, **kwargs):
        question = kwargs.pop("question", None)
        super().__init__(*args, **kwargs)

        if question:
            self.fields["options"].queryset = Options.objects.filter(question=question)

    class Meta:
        model = Options
        fields = ['options']