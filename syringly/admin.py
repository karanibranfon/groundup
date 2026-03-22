from django.contrib import admin
from .models import UserProfile, Tag, Question, Answer, Vote, Comment


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialty', 'reputation', 'created_at']
    search_fields = ['user__username', 'specialty']
    list_filter = ['created_at']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'question_count']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'votes', 'view_count', 'answer_count', 'is_answered', 'created_at']
    list_filter = ['created_at', 'is_answered', 'tags']
    search_fields = ['title', 'body']
    filter_horizontal = ['tags']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'author', 'votes', 'is_accepted', 'created_at']
    list_filter = ['is_accepted', 'created_at']
    search_fields = ['body']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'value', 'content_type', 'object_id', 'created_at']
    list_filter = ['value', 'content_type']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'body', 'content_type', 'object_id', 'created_at']
    search_fields = ['body']
