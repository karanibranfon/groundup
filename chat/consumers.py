import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.room_group_name = f"chat_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.update_online_status(True)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'is_online': True
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            await self.update_online_status(False)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'is_online': False
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'read_receipt':
            await self.handle_read_receipt(data)
        elif message_type == 'group_message':
            await self.handle_group_message(data)
        elif message_type == 'call_signal':
            await self.handle_call_signal(data)

    async def handle_chat_message(self, data):
        conversation_id = data.get('conversation_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        message = await self.create_message(conversation_id, content, message_type)
        
        await self.channel_layer.group_send(
            f"chat_conversation_{conversation_id}",
            {
                'type': 'new_message',
                'message': {
                    'id': message['id'],
                    'content': message['content'],
                    'message_type': message['message_type'],
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': message['timestamp'],
                }
            }
        )
        
        await self.channel_layer.group_send(
            f"chat_{self.user.id}",
            {
                'type': 'new_message',
                'message': {
                    'id': message['id'],
                    'content': message['content'],
                    'message_type': message['message_type'],
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': message['timestamp'],
                }
            }
        )

    async def handle_typing(self, data):
        conversation_id = data.get('conversation_id')
        is_typing = data.get('is_typing', True)
        
        await self.channel_layer.group_send(
            f"chat_conversation_{conversation_id}",
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_read_receipt(self, data):
        conversation_id = data.get('conversation_id')
        message_ids = data.get('message_ids', [])
        
        await self.mark_messages_read(conversation_id, message_ids)
        
        await self.channel_layer.group_send(
            f"chat_conversation_{conversation_id}",
            {
                'type': 'messages_read',
                'user_id': self.user.id,
                'message_ids': message_ids
            }
        )

    async def handle_group_message(self, data):
        group_id = data.get('group_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        message = await self.create_group_message(group_id, content, message_type)
        
        await self.channel_layer.group_send(
            f"chat_group_{group_id}",
            {
                'type': 'new_group_message',
                'message': {
                    'id': message['id'],
                    'content': message['content'],
                    'message_type': message['message_type'],
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': message['timestamp'],
                }
            }
        )

    async def handle_call_signal(self, data):
        target_user_id = data.get('target_user_id')
        signal_type = data.get('signal_type')
        signal_data = data.get('signal_data')
        
        await self.channel_layer.send(
            f"chat_{target_user_id}",
            {
                'type': 'call_signal',
                'from_user_id': self.user.id,
                'from_username': self.user.username,
                'signal_type': signal_type,
                'signal_data': signal_data
            }
        )

    async def new_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def messages_read(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'user_id': event['user_id'],
                'message_ids': event['message_ids']
            }))

    async def new_group_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'group_message',
            'message': event['message']
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'is_online': event['is_online']
        }))

    async def call_signal(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_signal',
            'from_user_id': event['from_user_id'],
            'from_username': event['from_username'],
            'signal_type': event['signal_type'],
            'signal_data': event['signal_data']
        }))

    @database_sync_to_async
    def create_message(self, conversation_id, content, message_type):
        from chat.models import Conversation, Message
        from django.utils import timezone
        
        conversation = Conversation.objects.get(id=conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type=message_type
        )
        conversation.updated_at = timezone.now()
        conversation.last_message = message
        conversation.save()
        
        return {
            'id': message.id,
            'content': message.content,
            'message_type': message.message_type,
            'timestamp': message.timestamp.isoformat()
        }

    @database_sync_to_async
    def create_group_message(self, group_id, content, message_type):
        from chat.models import Group, GroupMessage
        from django.utils import timezone
        
        group = Group.objects.get(id=group_id)
        message = GroupMessage.objects.create(
            group=group,
            sender=self.user,
            content=content,
            message_type=message_type
        )
        
        return {
            'id': message.id,
            'content': message.content,
            'message_type': message.message_type,
            'timestamp': message.timestamp.isoformat()
        }

    @database_sync_to_async
    def mark_messages_read(self, conversation_id, message_ids):
        from chat.models import Message
        Message.objects.filter(
            conversation_id=conversation_id,
            id__in=message_ids
        ).update(is_read=True)

    @database_sync_to_async
    def update_online_status(self, is_online):
        from chat.models import Profile
        profile = self.user.chat_profile
        profile.is_online = is_online
        profile.save()


class ConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.room_group_name = f"chat_conversation_{self.conversation_id}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass

    async def new_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user_id': event['user_id'],
            'message_ids': event['message_ids']
        }))
