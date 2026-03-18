import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_profile')
    avatar = models.ImageField(upload_to=upload_to, default='default-avatar.png', blank=True)
    phone = models.CharField(max_length=20, blank=True)
    about = models.CharField(max_length=255, default='', blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=False)
    two_step_enabled = models.BooleanField(default=False)
    two_step_pin = models.CharField(max_length=128, blank=True)
    qr_code = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    privacy_last_seen = models.CharField(max_length=20, default='everyone')
    privacy_profile = models.CharField(max_length=20, default='everyone')
    privacy_read_receipts = models.CharField(max_length=20, default='everyone')

    def __str__(self):
        return self.user.username


class Contact(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_of')
    nickname = models.CharField(max_length=100, blank=True)
    is_muted = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'user')

    def __str__(self):
        return f"{self.owner.username} - {self.user.username}"


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    last_message = models.ForeignKey('Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_in_conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    wallpaper = models.ImageField(upload_to=upload_to, blank=True)

    def __str__(self):
        return f"Conversation {self.id}"

    def other_participant(self, user):
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('location', 'Location'),
        ('contact', 'Contact'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_deleted_for_me = models.BooleanField(default=False)
    is_deleted_for_everyone = models.BooleanField(default=False)
    reactions = models.JSONField(default=dict)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    forwarded_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='forwards')
    is_starred = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message {self.id} from {self.sender.username}"


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=upload_to, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.IntegerField(default=0)
    thumbnail = models.ImageField(upload_to=upload_to, blank=True)
    is_view_once = models.BooleanField(default=False)
    duration = models.IntegerField(default=0)

    def __str__(self):
        return f"Attachment {self.id} for message {self.message_id}"


class Group(models.Model):
    name = models.CharField(max_length=100)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='administered_groups')
    members = models.ManyToManyField(User, related_name='group_memberships')
    avatar = models.ImageField(upload_to=upload_to, default='default-group.png', blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_messages')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    reactions = models.JSONField(default=dict)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='group_replies')

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"GroupMessage {self.id} in {self.group.name}"


class GroupMessageAttachment(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=upload_to, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    thumbnail = models.ImageField(upload_to=upload_to, blank=True)
    is_view_once = models.BooleanField(default=False)

    def __str__(self):
        return f"GroupAttachment {self.id}"


class Status(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statuses')
    media = models.FileField(upload_to=upload_to, blank=True)
    thumbnail = models.ImageField(upload_to=upload_to, blank=True)
    text = models.TextField(blank=True)
    media_type = models.CharField(max_length=20, default='image')
    views = models.ManyToManyField(User, related_name='viewed_statuses', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_viewed_by = models.ManyToManyField(User, related_name='viewed_status_list', blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Status by {self.user.username}"


class StatusReply(models.Model):
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to status {self.status_id}"


class CallLog(models.Model):
    CALL_TYPES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]
    STATUS_CHOICES = [
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='made_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_calls')
    call_type = models.CharField(max_length=10, choices=CALL_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.call_type} call from {self.caller.username} to {self.receiver.username}"


class StarredMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='starred_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='starred_by')
    starred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'message')

    def __str__(self):
        return f"Starred message {self.message_id} by {self.user.username}"


class MessageSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    searched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search '{self.query}' by {self.user.username}"
