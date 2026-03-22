from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.utils.text import slugify


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='syringly_profile')
    specialty = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    reputation = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username
    
    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    question_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Tags'
        ordering = ['-question_count', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Question(models.Model):
    SORT_CHOICES = [
        ('newest', 'Newest'),
        ('active', 'Active'),
        ('unanswered', 'Unanswered'),
        ('votes', 'Most Votes'),
    ]
    
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=300)
    body = models.TextField()
    tags = models.ManyToManyField(Tag, related_name='questions', blank=True)
    votes = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    answer_count = models.IntegerField(default=0)
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    votes_record = GenericRelation('Vote', related_query_name='question')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def update_answer_count(self):
        self.answer_count = self.answers.count()
        self.is_answered = self.answers.filter(is_accepted=True).exists()
        self.save(update_fields=['answer_count', 'is_answered'])


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='answers')
    body = models.TextField()
    votes = models.IntegerField(default=0)
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    votes_record = GenericRelation('Vote', related_query_name='answer')
    
    class Meta:
        ordering = ['-is_accepted', '-votes', 'created_at']
    
    def __str__(self):
        return f"Answer by {self.author} on {self.question.title}"


class Vote(models.Model):
    VOTE_CHOICES = [
        (1, 'Upvote'),
        (-1, 'Downvote'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='votes')
    value = models.SmallIntegerField(choices=VOTE_CHOICES)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'content_type', 'object_id']
    
    def __str__(self):
        return f"{self.user} {self.get_value_display()} on {self.content_object}"


class Comment(models.Model):
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField(max_length=600)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"
