from django import forms
from .models import Qtaker, Options


class Userform(forms.ModelForm):
    class Meta:
        model = Qtaker
        fields = "__all__"
        exclude = ['test_result',"date_taken"]


class AnswerForm(forms.Form):
   def __init__(self, *args, **kwargs):
       question = kwargs.pop("question")
       super().__init__(*args, **kwargs)

       if question.question_type == "radio":
           self.fields["answer"] = forms.ModelChoiceField(queryset=Options.objects.filter(question=question),
           widget=forms.RadioSelect, required=True, empty_label=None)
       elif question.question_type == "text":
           self.fields["answer"] = forms.CharField(widget=forms.Textarea(attrs={"rows":4}), required=True, max_length=1000)
           