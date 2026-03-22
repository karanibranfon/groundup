from django.urls import path
from . import views

app_name = 'syringly'

urlpatterns = [
    path('', views.home, name='home'),
    path('questions/', views.questions_list, name='questions'),
    path('questions/ask/', views.ask_question, name='ask_question'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
    path('questions/<int:question_id>/answer/', views.post_answer, name='post_answer'),
    path('questions/<int:question_id>/accept/<int:answer_id>/', views.accept_answer, name='accept_answer'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('answers/<int:answer_id>/edit/', views.edit_answer, name='edit_answer'),
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/<slug:tag_slug>/', views.tag_questions, name='tag_questions'),
    path('users/<int:user_id>/', views.user_profile, name='user_profile'),
    path('users/<int:user_id>/questions/', views.user_questions, name='user_questions'),
    path('users/<int:user_id>/answers/', views.user_answers, name='user_answers'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('vote/', views.vote, name='vote'),
]
