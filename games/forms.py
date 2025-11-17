from django import forms
from crispy_forms.helper import FormHelper
from .models import Game


class AddGameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ["title", "ps4", "ps5", "status", "ownership"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "addGameForm"
