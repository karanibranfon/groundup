from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    Profile, Contact, Conversation, Message, MessageAttachment,
    Group, GroupMessage, Status, StatusReply, CallLog, StarredMessage
)
import json


def landing(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    return render(request, 'chat/landing.html')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            profile = user.chat_profile
            if profile.two_step_enabled:
                request.session['pre_2fa_user_id'] = user.id
                return redirect('two_step_verify')
            login(request, user)
            return redirect('chat_list')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'chat/login.html')


def user_register(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone', '')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'chat/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'chat/register.html')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.chat_profile.phone = phone
        user.chat_profile.save()
        
        login(request, user)
        return redirect('chat_list')
    
    return render(request, 'chat/register.html')


def two_step_verify(request):
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        pin = request.POST.get('pin')
        if user.chat_profile.two_step_pin == pin:
            login(request, user)
            del request.session['pre_2fa_user_id']
            return redirect('chat_list')
        else:
            messages.error(request, 'Invalid PIN')
    
    return render(request, 'chat/two_step_verify.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def chat_list(request):
    conversations = Conversation.objects.filter(
        participants=request.user
    ).prefetch_related('participants', 'last_message').order_by('-updated_at')
    
    pinned = conversations.filter(is_pinned=True)
    others = conversations.filter(is_pinned=False, is_archived=False)
    archived = conversations.filter(is_archived=True)
    
    contacts = Contact.objects.filter(owner=request.user, is_blocked=False)
    groups = Group.objects.filter(members=request.user)
    
    for conv in list(pinned) + list(others) + list(archived):
        conv.other_user = conv.participants.exclude(id=request.user.id).first()
    
    context = {
        'pinned': pinned,
        'conversations': others,
        'archived': archived,
        'contacts': contacts,
        'groups': groups,
    }
    return render(request, 'chat/chat_list.html', context)


@login_required
def chat_view(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    messages_list = conversation.messages.filter(
        is_deleted_for_everyone=False
    ).exclude(
        is_deleted_for_me=True,
        sender=request.user
    ).order_by('timestamp')
    
    Message.objects.filter(
        conversation=conversation,
        sender__in=conversation.participants.exclude(id=request.user.id),
        is_read=False
    ).update(is_read=True)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        message_type = request.POST.get('message_type', 'text')
        
        if content or request.FILES:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
                message_type=message_type
            )
            
            if request.FILES.get('file'):
                file = request.FILES['file']
                attachment = MessageAttachment.objects.create(
                    message=message,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type,
                    file_size=file.size
                )
            
            conversation.updated_at = timezone.now()
            conversation.last_message = message
            conversation.save()
        
        return redirect('chat_view', conversation_id=conversation.id)
    
    context = {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages_list,
    }
    return render(request, 'chat/chat_view.html', context)


@login_required
def new_chat(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        other_user = get_object_or_404(User, id=user_id)
        
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
        
        return redirect('chat_view', conversation_id=conversation.id)
    
    contacts = Contact.objects.filter(owner=request.user, is_blocked=False).select_related('user')
    return render(request, 'chat/new_chat.html', {'contacts': contacts})


@login_required
def search_users(request):
    query = request.GET.get('q', '')
    users = []
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(email__icontains=query) |
            Q(profile__phone__icontains=query)
        ).exclude(id=request.user.id)[:20]
    
    return render(request, 'chat/search_users.html', {'users': users, 'query': query})


@login_required
def contacts_list(request):
    contacts = Contact.objects.filter(owner=request.user).select_related('user')
    blocked = Contact.objects.filter(owner=request.user, is_blocked=True).select_related('user')
    
    context = {
        'contacts': contacts,
        'blocked': blocked,
    }
    return render(request, 'chat/contacts.html', context)


@login_required
def add_contact(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            if user == request.user:
                messages.error(request, "You cannot add yourself")
                return redirect('contacts')
            
            contact, created = Contact.objects.get_or_create(
                owner=request.user,
                user=user
            )
            if created:
                messages.success(request, f'Added {user.username} to contacts')
            else:
                messages.info(request, f'{user.username} is already in your contacts')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    
    return redirect('contacts')


@login_required
def block_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id, owner=request.user)
    contact.is_blocked = True
    contact.save()
    return redirect('contacts')


@login_required
def unblock_contact(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id, owner=request.user, is_blocked=True)
    contact.is_blocked = False
    contact.save()
    return redirect('contacts')


@login_required
def groups_list(request):
    groups = Group.objects.filter(members=request.user)
    return render(request, 'chat/groups.html', {'groups': groups})


@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        member_ids = request.POST.getlist('members')
        
        group = Group.objects.create(
            name=name,
            admin=request.user,
            description=description
        )
        
        if request.FILES.get('avatar'):
            group.avatar = request.FILES['avatar']
            group.save()
        
        group.members.add(request.user)
        for member_id in member_ids:
            group.members.add(member_id)
        
        return redirect('group_view', group_id=group.id)
    
    contacts = Contact.objects.filter(owner=request.user, is_blocked=False).select_related('user')
    return render(request, 'chat/create_group.html', {'contacts': contacts})


@login_required
def group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id, members=request.user)
    messages_list = group.messages.filter(is_deleted=False).order_by('timestamp')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        message_type = request.POST.get('message_type', 'text')
        
        if content or request.FILES:
            message = GroupMessage.objects.create(
                group=group,
                sender=request.user,
                content=content,
                message_type=message_type
            )
            
            if request.FILES.get('file'):
                file = request.FILES['file']
                from chat.models import GroupMessageAttachment
                GroupMessageAttachment.objects.create(
                    message=message,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type
                )
        
        return redirect('group_view', group_id=group.id)
    
    context = {
        'group': group,
        'messages': messages_list,
    }
    return render(request, 'chat/group_view.html', context)


@login_required
def group_info(request, group_id):
    group = get_object_or_404(Group, id=group_id, members=request.user)
    return render(request, 'chat/group_info.html', {'group': group})


@login_required
def add_group_members(request, group_id):
    group = get_object_or_404(Group, id=group_id, admin=request.user)
    
    if request.method == 'POST':
        member_ids = request.POST.getlist('members')
        for member_id in member_ids:
            group.members.add(member_id)
        return redirect('group_info', group_id=group.id)
    
    contacts = Contact.objects.filter(owner=request.user, is_blocked=False).exclude(
        user__in=group.members.all()
    ).select_related('user')
    
    return render(request, 'chat/add_group_members.html', {'group': group, 'contacts': contacts})


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id, members=request.user)
    group.members.remove(request.user)
    return redirect('groups_list')


@login_required
def remove_group_member(request, group_id, member_id):
    group = get_object_or_404(Group, id=group_id, admin=request.user)
    member = get_object_or_404(User, id=member_id)
    group.members.remove(member)
    return redirect('group_info', group_id=group.id)


@login_required
def status_list(request):
    contacts = Contact.objects.filter(owner=request.user, is_blocked=False).select_related('user')
    my_statuses = Status.objects.filter(user=request.user)
    
    contact_statuses = []
    for contact in contacts:
        statuses = Status.objects.filter(
            user=contact.user,
            expires_at__gt=timezone.now()
        ).exclude(is_viewed_by=request.user)
        if statuses:
            contact_statuses.append({
                'user': contact.user,
                'statuses': statuses,
                'unread_count': statuses.count()
            })
    
    context = {
        'my_statuses': my_statuses,
        'contact_statuses': contact_statuses,
    }
    return render(request, 'chat/status_list.html', context)


@login_required
def add_status(request):
    if request.method == 'POST':
        text = request.POST.get('text', '')
        media = request.FILES.get('media')
        media_type = 'text'
        
        if media:
            if media.type.startswith('image'):
                media_type = 'image'
            elif media.type.startswith('video'):
                media_type = 'video'
        
        status = Status.objects.create(
            user=request.user,
            text=text,
            media=media,
            media_type=media_type
        )
        
        return redirect('status_list')
    
    return render(request, 'chat/add_status.html')


@login_required
def view_status(request, status_id):
    status = get_object_or_404(Status, id=status_id)
    
    if request.user not in status.is_viewed_by.all():
        status.is_viewed_by.add(request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            StatusReply.objects.create(status=status, user=request.user, content=content)
    
    replies = status.replies.all()
    return render(request, 'chat/view_status.html', {'status': status, 'replies': replies})


@login_required
def calls_list(request):
    made_calls = CallLog.objects.filter(caller=request.user).order_by('-timestamp')[:50]
    received_calls = CallLog.objects.filter(receiver=request.user).order_by('-timestamp')[:50]
    
    calls = (made_calls | received_calls).distinct().order_by('-timestamp')
    
    return render(request, 'chat/calls.html', {'calls': calls})


@login_required
def start_call(request, user_id, call_type):
    receiver = get_object_or_404(User, id=user_id)
    
    call = CallLog.objects.create(
        caller=request.user,
        receiver=receiver,
        call_type=call_type,
        status='completed'
    )
    
    return render(request, 'chat/call.html', {
        'call': call,
        'receiver': receiver,
        'call_type': call_type
    })


@login_required
def profile(request):
    user = request.user
    profile = user.chat_profile
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.save()
        
        profile.about = request.POST.get('about', '')
        profile.phone = request.POST.get('phone', '')
        
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        messages.success(request, 'Profile updated successfully')
        return redirect('profile')
    
    return render(request, 'chat/profile.html', {'user': user, 'profile': profile})


@login_required
def privacy_settings(request):
    profile = request.user.chat_profile
    
    if request.method == 'POST':
        profile.privacy_last_seen = request.POST.get('privacy_last_seen', 'everyone')
        profile.privacy_profile = request.POST.get('privacy_profile', 'everyone')
        profile.privacy_read_receipts = request.POST.get('privacy_read_receipts', 'everyone')
        profile.save()
        messages.success(request, 'Privacy settings updated')
        return redirect('privacy_settings')
    
    return render(request, 'chat/privacy_settings.html', {'profile': profile})


@login_required
def starred_messages(request):
    starred = StarredMessage.objects.filter(
        user=request.user
    ).select_related('message__conversation').order_by('-starred_at')
    
    return render(request, 'chat/starred.html', {'starred': starred})


@login_required
def search_messages(request):
    query = request.GET.get('q', '')
    results = []
    
    if query:
        my_messages = Message.objects.filter(
            Q(content__icontains=query),
            conversation__participants=request.user,
            is_deleted_for_everyone=False
        ).select_related('conversation', 'sender')[:50]
        
        results = my_messages
    
    return render(request, 'chat/search_messages.html', {'results': results, 'query': query})


@login_required
def toggle_pin_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    conversation.is_pinned = not conversation.is_pinned
    conversation.save()
    return redirect('chat_list')


@login_required
def toggle_mute_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    conversation.is_muted = not conversation.is_muted
    conversation.save()
    return redirect('chat_list')


@login_required
def archive_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    conversation.is_archived = True
    conversation.save()
    return redirect('chat_list')


@login_required
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    conversation.messages.update(is_deleted_for_me=True, sender=request.user)
    return redirect('chat_list')


@login_required
def message_actions(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete_me':
            message.is_deleted_for_me = True
            message.save()
        elif action == 'delete_everyone':
            if message.sender == request.user:
                message.is_deleted_for_everyone = True
                message.save()
        elif action == 'star':
            if not StarredMessage.objects.filter(user=request.user, message=message).exists():
                StarredMessage.objects.create(user=request.user, message=message)
        elif action == 'unstar':
            StarredMessage.objects.filter(user=request.user, message=message).delete()
        elif action == 'forward':
            return JsonResponse({'status': 'ok', 'message_id': message.id, 'content': message.content})
    
    return JsonResponse({'status': 'ok'})


@login_required
def forward_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        conversation_id = request.POST.get('conversation_id')
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        
        new_message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message.content,
            message_type=message.message_type,
            forwarded_from=message
        )
        
        for attachment in message.attachments.all():
            MessageAttachment.objects.create(
                message=new_message,
                file=attachment.file,
                file_name=attachment.file_name,
                file_type=attachment.file_type,
                file_size=attachment.file_size
            )
        
        conversation.updated_at = timezone.now()
        conversation.last_message = new_message
        conversation.save()
        
        return JsonResponse({'status': 'ok'})
    
    conversations = Conversation.objects.filter(participants=request.user)
    return render(request, 'chat/forward_message.html', {
        'message': message,
        'conversations': conversations
    })


@login_required
def mark_online(request):
    profile = request.user.chat_profile
    profile.is_online = True
    profile.save()
    return JsonResponse({'status': 'ok'})


@login_required
def mark_offline(request):
    profile = request.user.chat_profile
    profile.is_online = False
    profile.last_seen = timezone.now()
    profile.save()
    return JsonResponse({'status': 'ok'})


@login_required
def api_get_conversations(request):
    conversations = Conversation.objects.filter(
        participants=request.user
    ).order_by('-updated_at')
    
    data = []
    for conv in conversations:
        other = conv.participants.exclude(id=request.user.id).first()
        data.append({
            'id': conv.id,
            'other_user': {
                'id': other.id,
                'username': other.username,
                'avatar': other.chat_profile.avatar.url if other.chat_profile.avatar else None,
                'is_online': other.chat_profile.is_online
            } if other else None,
            'last_message': {
                'content': conv.last_message.content[:50] if conv.last_message else None,
                'timestamp': conv.last_message.timestamp.isoformat() if conv.last_message else None
            },
            'is_pinned': conv.is_pinned,
            'is_muted': conv.is_muted,
            'unread_count': conv.messages.filter(is_read=False).exclude(sender=request.user).count()
        })
    
    return JsonResponse({'conversations': data})


@login_required
def message_reaction(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        emoji = request.POST.get('emoji')
        if emoji:
            reactions = message.reactions or {}
            user_id = str(request.user.id)
            reactions[user_id] = emoji
            message.reactions = reactions
            message.save()
    
    return JsonResponse({'status': 'ok'})
