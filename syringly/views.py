from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from .models import UserProfile, Question, Answer, Tag, Vote


def home(request):
    sort = request.GET.get('sort', 'newest')
    tag_slug = request.GET.get('tag')
    
    questions = Question.objects.all()
    
    if tag_slug:
        questions = questions.filter(tags__slug=tag_slug)
    
    if sort == 'active':
        questions = questions.order_by('-updated_at')
    elif sort == 'unanswered':
        questions = questions.filter(answer_count=0).order_by('-created_at')
    elif sort == 'votes':
        questions = questions.order_by('-votes')
    else:
        questions = questions.order_by('-created_at')
    
    popular_tags = Tag.objects.all()[:10]
    
    context = {
        'questions': questions[:20],
        'sort': sort,
        'popular_tags': popular_tags,
        'tag_slug': tag_slug,
    }
    return render(request, 'syringly/home.html', context)


def questions_list(request):
    return home(request)


@login_required
def ask_question(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        tags_str = request.POST.get('tags', '').strip()
        
        if not title or not body:
            messages.error(request, 'Title and body are required.')
            return redirect('syringly:ask_question')
        
        question = Question.objects.create(
            author=user_profile,
            title=title,
            body=body
        )
        
        for tag_name in [t.strip() for t in tags_str.split(',') if t.strip()]:
            tag, _ = Tag.objects.get_or_create(
                slug=tag_name.lower().replace(' ', '-'),
                defaults={'name': tag_name}
            )
            question.tags.add(tag)
        
        messages.success(request, 'Question posted successfully!')
        return redirect('syringly:question_detail', question_id=question.id)
    
    popular_tags = Tag.objects.all()[:20]
    return render(request, 'syringly/ask_question.html', {'popular_tags': popular_tags})


def question_detail(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    question.view_count += 1
    question.save(update_fields=['view_count'])
    
    answers = question.answers.all().order_by('-is_accepted', '-votes', 'created_at')
    
    user_vote = None
    user_answer_votes = {}
    
    if request.user.is_authenticated:
        user_profile = getattr(request.user, 'syringly_profile', None)
        if user_profile:
            q_ct = ContentType.objects.get_for_model(Question)
            user_vote = Vote.objects.filter(
                user=user_profile,
                content_type=q_ct,
                object_id=question.id
            ).first()
            
            a_ct = ContentType.objects.get_for_model(Answer)
            for answer in answers:
                vote = Vote.objects.filter(
                    user=user_profile,
                    content_type=a_ct,
                    object_id=answer.id
                ).first()
                if vote:
                    user_answer_votes[answer.id] = vote.value
    
    context = {
        'question': question,
        'answers': answers,
        'user_vote': user_vote,
        'user_answer_votes': user_answer_votes,
    }
    return render(request, 'syringly/question_detail.html', context)


@login_required
def post_answer(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        
        if not body:
            messages.error(request, 'Answer body is required.')
            return redirect('syringly:question_detail', question_id=question.id)
        
        Answer.objects.create(
            question=question,
            author=user_profile,
            body=body
        )
        
        messages.success(request, 'Answer posted successfully!')
        return redirect('syringly:question_detail', question_id=question.id)
    
    return redirect('syringly:question_detail', question_id=question.id)


@login_required
def accept_answer(request, question_id, answer_id):
    question = get_object_or_404(Question, pk=question_id)
    answer = get_object_or_404(Answer, pk=answer_id, question=question)
    
    if request.user == question.author.user:
        Answer.objects.filter(question=question).update(is_accepted=False)
        answer.is_accepted = True
        answer.save(update_fields=['is_accepted'])
        question.update_answer_count()
        messages.success(request, 'Answer accepted!')
    else:
        messages.error(request, 'Only the question author can accept answers.')
    
    return redirect('syringly:question_detail', question_id=question.id)


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    
    if question.author.user != request.user:
        messages.error(request, 'You can only edit your own questions.')
        return redirect('syringly:question_detail', question_id=question.id)
    
    if request.method == 'POST':
        question.title = request.POST.get('title', '').strip()
        question.body = request.POST.get('body', '').strip()
        question.save()
        
        messages.success(request, 'Question updated successfully!')
        return redirect('syringly:question_detail', question_id=question.id)
    
    return render(request, 'syringly/edit_question.html', {'question': question})


@login_required
def edit_answer(request, answer_id):
    answer = get_object_or_404(Answer, pk=answer_id)
    
    if answer.author.user != request.user:
        messages.error(request, 'You can only edit your own answers.')
        return redirect('syringly:question_detail', question_id=answer.question.id)
    
    if request.method == 'POST':
        answer.body = request.POST.get('body', '').strip()
        answer.save()
        
        messages.success(request, 'Answer updated successfully!')
        return redirect('syringly:question_detail', question_id=answer.question.id)
    
    return render(request, 'syringly/edit_answer.html', {'answer': answer})


def tag_list(request):
    tags = Tag.objects.all()
    return render(request, 'syringly/tag_list.html', {'tags': tags})


def tag_questions(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    questions = Question.objects.filter(tags=tag).order_by('-created_at')
    
    context = {
        'tag': tag,
        'questions': questions[:20],
    }
    return render(request, 'syringly/tag_questions.html', context)


def user_profile(request, user_id):
    user_profile = get_object_or_404(UserProfile, pk=user_id)
    questions = user_profile.questions.all()[:10]
    answers = user_profile.answers.all()[:10]
    
    context = {
        'profile': user_profile,
        'questions': questions,
        'answers': answers,
    }
    return render(request, 'syringly/user_profile.html', context)


def user_questions(request, user_id):
    user_profile = get_object_or_404(UserProfile, pk=user_id)
    questions = user_profile.questions.all().order_by('-created_at')
    
    return render(request, 'syringly/user_questions.html', {
        'profile': user_profile,
        'questions': questions,
    })


def user_answers(request, user_id):
    user_profile = get_object_or_404(UserProfile, pk=user_id)
    answers = user_profile.answers.all().order_by('-created_at')
    
    return render(request, 'syringly/user_answers.html', {
        'profile': user_profile,
        'answers': answers,
    })


@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    questions = user_profile.questions.all().order_by('-created_at')
    
    context = {
        'profile': user_profile,
        'questions': questions,
    }
    return render(request, 'syringly/profile.html', context)


@login_required
def edit_profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_profile.specialty = request.POST.get('specialty', '').strip()
        user_profile.bio = request.POST.get('bio', '').strip()
        user_profile.save()
        
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        if first_name or last_name:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('syringly:profile')
    
    context = {
        'profile': user_profile,
    }
    return render(request, 'syringly/edit_profile.html', context)


@login_required
def vote(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    content_type_id = request.POST.get('content_type_id')
    object_id = request.POST.get('object_id')
    value = int(request.POST.get('value', 0))
    
    if value not in [1, -1]:
        return JsonResponse({'error': 'Invalid vote value'}, status=400)
    
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
    except ContentType.DoesNotExist:
        return JsonResponse({'error': 'Invalid content type'}, status=400)
    
    vote, created = Vote.objects.update_or_create(
        user=user_profile,
        content_type=content_type,
        object_id=object_id,
        defaults={'value': value}
    )
    
    if not created:
        if vote.value == value:
            vote.delete()
            new_votes = 0
        else:
            vote.value = value
            vote.save()
            new_votes = value
    else:
        new_votes = value
    
    return JsonResponse({
        'success': True,
        'new_votes': new_votes,
    })
