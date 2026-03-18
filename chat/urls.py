from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('two-step-verify/', views.two_step_verify, name='two_step_verify'),
    
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/new/', views.new_chat, name='new_chat'),
    path('chat/<int:conversation_id>/', views.chat_view, name='chat_view'),
    path('chat/<int:conversation_id>/pin/', views.toggle_pin_conversation, name='toggle_pin_conversation'),
    path('chat/<int:conversation_id>/mute/', views.toggle_mute_conversation, name='toggle_mute_conversation'),
    path('chat/<int:conversation_id>/archive/', views.archive_conversation, name='archive_conversation'),
    path('chat/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    
    path('search/', views.search_users, name='search_users'),
    path('search/messages/', views.search_messages, name='search_messages'),
    
    path('contacts/', views.contacts_list, name='contacts'),
    path('contacts/add/', views.add_contact, name='add_contact'),
    path('contacts/<int:contact_id>/block/', views.block_contact, name='block_contact'),
    path('contacts/<int:contact_id>/unblock/', views.unblock_contact, name='unblock_contact'),
    
    path('groups/', views.groups_list, name='groups_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:group_id>/', views.group_view, name='group_view'),
    path('groups/<int:group_id>/info/', views.group_info, name='group_info'),
    path('groups/<int:group_id>/add-members/', views.add_group_members, name='add_group_members'),
    path('groups/<int:group_id>/remove-member/<int:member_id>/', views.remove_group_member, name='remove_group_member'),
    path('groups/<int:group_id>/leave/', views.leave_group, name='leave_group'),
    
    path('status/', views.status_list, name='status_list'),
    path('status/add/', views.add_status, name='add_status'),
    path('status/<int:status_id>/', views.view_status, name='view_status'),
    
    path('calls/', views.calls_list, name='calls_list'),
    path('calls/start/<int:user_id>/<str:call_type>/', views.start_call, name='start_call'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/settings/', views.privacy_settings, name='privacy_settings'),
    
    path('messages/starred/', views.starred_messages, name='starred_messages'),
    path('message/<int:message_id>/actions/', views.message_actions, name='message_actions'),
    path('message/<int:message_id>/react/', views.message_reaction, name='message_reaction'),
    path('message/<int:message_id>/forward/', views.forward_message, name='forward_message'),
    
    path('api/conversations/', views.api_get_conversations, name='api_conversations'),
    path('api/online/', views.mark_online, name='mark_online'),
    path('api/offline/', views.mark_offline, name='mark_offline'),
]
