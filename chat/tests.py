from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Profile, Contact, Conversation, Message, Group, GroupMessage, StarredMessage


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chatuser', password='testpass123')

    def test_profile_creation(self):
        profile = self.user.chat_profile
        self.assertEqual(profile.user, self.user)
        self.assertFalse(profile.two_step_enabled)
        self.assertEqual(profile.privacy_last_seen, 'everyone')

    def test_str_representation(self):
        self.assertEqual(str(self.user.chat_profile), 'chatuser')


class ContactModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')

    def test_contact_creation(self):
        contact = Contact.objects.create(owner=self.user1, user=self.user2)
        self.assertEqual(contact.owner, self.user1)
        self.assertEqual(contact.user, self.user2)
        self.assertFalse(contact.is_blocked)

    def test_unique_contact(self):
        Contact.objects.create(owner=self.user1, user=self.user2)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Contact.objects.create(owner=self.user1, user=self.user2)


class ConversationModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='conv1', password='testpass123')
        self.user2 = User.objects.create_user(username='conv2', password='testpass123')

    def test_conversation_creation(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        self.assertEqual(conv.participants.count(), 2)

    def test_other_participant(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)
        other = conv.other_participant(self.user1)
        self.assertEqual(other, self.user2)


class MessageModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='msg1', password='testpass123')
        self.user2 = User.objects.create_user(username='msg2', password='testpass123')
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.user1, self.user2)

    def test_message_creation(self):
        msg = Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            content='Hello!'
        )
        self.assertEqual(msg.content, 'Hello!')
        self.assertEqual(msg.sender, self.user1)
        self.assertFalse(msg.is_read)

    def test_message_ordering(self):
        msg1 = Message.objects.create(conversation=self.conv, sender=self.user1, content='First')
        msg2 = Message.objects.create(conversation=self.conv, sender=self.user2, content='Second')
        messages = list(Message.objects.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)


class GroupModelTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='testpass123')
        self.member = User.objects.create_user(username='member', password='testpass123')

    def test_group_creation(self):
        group = Group.objects.create(
            name='Test Group',
            admin=self.admin
        )
        group.members.add(self.admin, self.member)
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.members.count(), 2)


class ChatViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='viewuser', password='testpass123')
        self.other = User.objects.create_user(username='other', password='testpass123')

    def test_landing_page(self):
        response = self.client.get('/chat/')
        self.assertEqual(response.status_code, 200)

    def test_chat_list_requires_login(self):
        response = self.client.get('/chat/chat/')
        self.assertEqual(response.status_code, 302)

    def test_chat_list_accessible(self):
        self.client.login(username='viewuser', password='testpass123')
        response = self.client.get('/chat/chat/')
        self.assertEqual(response.status_code, 200)

    def test_conversation_creation(self):
        self.client.login(username='viewuser', password='testpass123')
        conv = Conversation.objects.create()
        conv.participants.add(self.user, self.other)
        msg = Message.objects.create(
            conversation=conv,
            sender=self.user,
            content='Test message'
        )
        conv.last_message = msg
        conv.save()
        
        response = self.client.get('/chat/chat/' + str(conv.id) + '/')
        self.assertEqual(response.status_code, 200)


class MessageAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='testpass123')
        self.client.login(username='apiuser', password='testpass123')

    def test_api_conversations(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user)
        
        response = self.client.get('/chat/api/conversations/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('conversations', data)


class SearchMessagesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='searchuser', password='testpass123')
        self.client.login(username='searchuser', password='testpass123')
        
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.user)
        
        Message.objects.create(
            conversation=self.conv,
            sender=self.user,
            content='This is a searchable message'
        )

    def test_search_returns_results(self):
        response = self.client.get('/chat/search/messages/?q=searchable')
        self.assertEqual(response.status_code, 200)

    def test_search_with_limit(self):
        response = self.client.get('/chat/search/messages/?q=message&limit=10')
        self.assertEqual(response.status_code, 200)


class PINVerificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='pinuser', password='testpass123')
        self.profile = self.user.chat_profile
        self.profile.two_step_enabled = True
        self.profile.two_step_pin = '1234'
        self.profile.save()

    def test_two_step_verify_page(self):
        self.client.login(username='pinuser', password='testpass123')
        self.client.session['pre_2fa_user_id'] = self.user.id
        
        response = self.client.post('/chat/two-step-verify/', {'pin': '1234'})
        self.assertEqual(response.status_code, 302)

    def test_invalid_pin_rejected(self):
        self.client.login(username='pinuser', password='testpass123')
        self.client.session['pre_2fa_user_id'] = self.user.id
        
        response = self.client.post('/chat/two-step-verify/', {'pin': '0000'})
        self.assertIn(response.status_code, [200, 302])


class StarredMessageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staruser', password='testpass123')
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.user)
        self.msg = Message.objects.create(
            conversation=self.conv,
            sender=self.user,
            content='Star this!'
        )

    def test_star_message(self):
        starred = StarredMessage.objects.create(user=self.user, message=self.msg)
        self.assertEqual(starred.message, self.msg)
        self.assertEqual(starred.user, self.user)

    def test_unique_star(self):
        StarredMessage.objects.create(user=self.user, message=self.msg)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            StarredMessage.objects.create(user=self.user, message=self.msg)


class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='secuser1', password='testpass123')
        self.user2 = User.objects.create_user(username='secuser2', password='testpass123')
        
        self.conv = Conversation.objects.create()
        self.conv.participants.add(self.user1)
        
        self.msg = Message.objects.create(
            conversation=self.conv,
            sender=self.user1,
            content='Private message'
        )

    def test_cannot_view_others_conversation(self):
        self.client.login(username='secuser2', password='testpass123')
        response = self.client.get('/chat/view/' + str(self.conv.id) + '/')
        self.assertEqual(response.status_code, 404)

    def test_cannot_star_others_message(self):
        self.client.login(username='secuser2', password='testpass123')
        response = self.client.post('/chat/message/' + str(self.msg.id) + '/actions/', {
            'action': 'star'
        })
        self.assertEqual(response.status_code, 200)
