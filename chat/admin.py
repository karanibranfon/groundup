from django.contrib import admin
from .models import (
    Profile, Contact, Conversation, Message, MessageAttachment,
    Group, GroupMessage, GroupMessageAttachment, Status, StatusReply,
    CallLog, StarredMessage, MessageSearch
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_online', 'two_step_enabled', 'created_at')
    list_filter = ('is_online', 'two_step_enabled')
    search_fields = ('user__username', 'phone')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('owner', 'user', 'nickname', 'is_muted', 'is_blocked', 'created_at')
    list_filter = ('is_muted', 'is_blocked')
    search_fields = ('owner__username', 'user__username', 'nickname')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at', 'is_pinned', 'is_muted', 'is_archived')
    list_filter = ('is_pinned', 'is_muted', 'is_archived')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'message_type', 'timestamp', 'is_read', 'is_deleted_for_me', 'is_deleted_for_everyone')
    list_filter = ('message_type', 'is_read', 'is_deleted_for_me', 'is_deleted_for_everyone')
    search_fields = ('content', 'sender__username')
    date_hierarchy = 'timestamp'


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file_name', 'file_type', 'file_size')
    list_filter = ('file_type',)
    search_fields = ('file_name',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'created_at', 'is_pinned', 'is_muted')
    list_filter = ('is_pinned', 'is_muted')
    filter_horizontal = ('members',)
    search_fields = ('name', 'description')


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'sender', 'message_type', 'timestamp', 'is_deleted')
    list_filter = ('message_type', 'is_deleted')
    search_fields = ('content', 'sender__username')
    date_hierarchy = 'timestamp'


@admin.register(GroupMessageAttachment)
class GroupMessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file_name', 'file_type')
    list_filter = ('file_type',)
    search_fields = ('file_name',)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_type', 'created_at', 'expires_at')
    list_filter = ('media_type',)
    date_hierarchy = 'created_at'


@admin.register(StatusReply)
class StatusReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'user', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'caller', 'receiver', 'call_type', 'status', 'timestamp', 'duration')
    list_filter = ('call_type', 'status')
    date_hierarchy = 'timestamp'


@admin.register(StarredMessage)
class StarredMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'starred_at')
    date_hierarchy = 'starred_at'


@admin.register(MessageSearch)
class MessageSearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'query', 'searched_at')
    date_hierarchy = 'searched_at'
