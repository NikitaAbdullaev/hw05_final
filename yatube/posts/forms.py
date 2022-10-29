from django import forms
from .models import Comment, Post
from django.core.exceptions import ValidationError


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')

    def clean_text(self):
        text = self.cleaned_data['text']
        if len(text) == 0:
            raise ValidationError('Заполните поле "Текст поста"')
        return text


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

    def clean_text(self):
        text = self.cleaned_data['text']
        if len(text) == 0:
            raise ValidationError('Напишите комментарий')
        return text
