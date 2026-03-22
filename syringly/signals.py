from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Vote, Answer, Question


@receiver(post_save, sender=Vote)
def update_vote_count(sender, instance, **kwargs):
    content_type = instance.content_type
    obj_id = instance.object_id
    
    if content_type.model == 'question':
        question = Question.objects.filter(pk=obj_id).first()
        if question:
            question.votes = Vote.objects.filter(
                content_type=content_type,
                object_id=obj_id
            ).aggregate(total=Sum('value'))['total'] or 0
            question.save(update_fields=['votes'])
    
    elif content_type.model == 'answer':
        answer = Answer.objects.filter(pk=obj_id).first()
        if answer:
            answer.votes = Vote.objects.filter(
                content_type=content_type,
                object_id=obj_id
            ).aggregate(total=Sum('value'))['total'] or 0
            answer.save(update_fields=['votes'])


@receiver(post_delete, sender=Vote)
def update_vote_count_on_delete(sender, instance, **kwargs):
    content_type = instance.content_type
    obj_id = instance.object_id
    
    if content_type.model == 'question':
        question = Question.objects.filter(pk=obj_id).first()
        if question:
            question.votes = Vote.objects.filter(
                content_type=content_type,
                object_id=obj_id
            ).aggregate(total=Sum('value'))['total'] or 0
            question.save(update_fields=['votes'])
    
    elif content_type.model == 'answer':
        answer = Answer.objects.filter(pk=obj_id).first()
        if answer:
            answer.votes = Vote.objects.filter(
                content_type=content_type,
                object_id=obj_id
            ).aggregate(total=Sum('value'))['total'] or 0
            answer.save(update_fields=['votes'])


@receiver(post_save, sender=Answer)
def update_question_answer_count(sender, instance, **kwargs):
    question = instance.question
    question.update_answer_count()


@receiver(post_delete, sender=Answer)
def update_question_answer_count_on_delete(sender, instance, **kwargs):
    question = instance.question
    question.update_answer_count()
