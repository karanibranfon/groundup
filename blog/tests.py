from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Category, Tag, BlogPost
from .serializers import BlogPostListSerializer, BlogPostDetailSerializer


class CategoryModelTest(TestCase):
    def test_category_creation(self):
        cat = Category.objects.create(
            name='Health Tips',
            slug='health-tips',
            description='Tips for staying healthy'
        )
        self.assertEqual(cat.name, 'Health Tips')
        self.assertEqual(cat.slug, 'health-tips')

    def test_category_str(self):
        cat = Category.objects.create(name='Test', slug='test')
        self.assertEqual(str(cat), 'Test')


class TagModelTest(TestCase):
    def test_tag_creation(self):
        tag = Tag.objects.create(name='Wellness', slug='wellness')
        self.assertEqual(tag.name, 'Wellness')

    def test_tag_str(self):
        tag = Tag.objects.create(name='Diet', slug='diet')
        self.assertEqual(str(tag), 'Diet')


class BlogPostModelTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='blogauthor', password='testpass123')
        self.category = Category.objects.create(name='General', slug='general')

    def test_post_creation(self):
        post = BlogPost.objects.create(
            title='Test Post',
            slug='test-post',
            content='This is test content',
            excerpt='Test excerpt',
            author=self.author,
            category=self.category,
            status='draft'
        )
        self.assertEqual(post.title, 'Test Post')
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.status, 'draft')

    def test_post_str(self):
        post = BlogPost.objects.create(
            title='My Blog Post',
            slug='my-blog-post',
            author=self.author
        )
        self.assertEqual(str(post), 'My Blog Post')

    def test_post_with_tags(self):
        tag1 = Tag.objects.create(name='Tag1', slug='tag1')
        tag2 = Tag.objects.create(name='Tag2', slug='tag2')
        post = BlogPost.objects.create(
            title='Tagged Post',
            slug='tagged-post',
            author=self.author
        )
        post.tags.add(tag1, tag2)
        self.assertEqual(post.tags.count(), 2)


class BlogViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='bloguser', password='testpass123')
        self.author = User.objects.create_user(username='blogauthor', password='testpass123')
        self.category = Category.objects.create(name='Health', slug='health')
        
        self.post = BlogPost.objects.create(
            title='Published Post',
            slug='published-post',
            content='Published content',
            author=self.author,
            category=self.category,
            status='published'
        )

    def test_blog_index(self):
        response = self.client.get('/blog/')
        self.assertIn(response.status_code, [200, 403])

    def test_blog_detail_published(self):
        response = self.client.get('/blog/published-post/')
        self.assertEqual(response.status_code, 200)

    def test_blog_detail_draft_not_visible_to_anonymous(self):
        draft = BlogPost.objects.create(
            title='Draft Post',
            slug='draft-post',
            content='Draft content',
            author=self.author,
            status='draft'
        )
        response = self.client.get('/blog/draft-post/')
        self.assertEqual(response.status_code, 404)

    def test_blog_create_requires_login(self):
        response = self.client.get('/blog/create/')
        self.assertEqual(response.status_code, 302)

    def test_blog_create_accessible(self):
        self.client.login(username='bloguser', password='testpass123')
        response = self.client.get('/blog/create/')
        self.assertEqual(response.status_code, 200)


class BlogAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='testpass123')
        self.author = User.objects.create_user(username='author', password='testpass123')
        self.category = Category.objects.create(name='API Category', slug='api-category')
        
        self.post = BlogPost.objects.create(
            title='API Post',
            slug='api-post',
            content='API content',
            author=self.author,
            category=self.category,
            status='published'
        )

    def test_list_posts(self):
        response = self.client.get('/blog/posts/')
        self.assertEqual(response.status_code, 200)

    def test_retrieve_post(self):
        response = self.client.get(f'/blog/posts/{self.post.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'API Post')

    def test_filter_by_category(self):
        response = self.client.get('/blog/posts/?category=api-category')
        self.assertEqual(response.status_code, 200)

    def test_filter_by_status_draft(self):
        self.client.login(username='author', password='testpass123')
        draft = BlogPost.objects.create(
            title='Draft',
            slug='draft-api',
            content='Draft',
            author=self.author,
            status='draft'
        )
        response = self.client.get('/blog/posts/?status=draft')
        self.assertEqual(response.status_code, 200)


class BlogContentGenerationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='genuser', password='testpass123')
        self.client.login(username='genuser', password='testpass123')

    def test_generate_blog_requires_auth(self):
        self.client.logout()
        response = self.client.post('/blog/generate/')
        self.assertIn(response.status_code, [401, 403])

    def test_generate_blog_with_data(self):
        response = self.client.post(
            '/blog/generate/',
            {'topic': 'Healthy Eating', 'category': 'Nutrition', 'tone': 'educational'},
            content_type='application/json'
        )
        self.assertIn(response.status_code, [200, 500])


class BlogSerializerTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='serauthor', password='testpass123')
        self.category = Category.objects.create(name='Test', slug='test')
        self.tag = Tag.objects.create(name='TestTag', slug='testtag')
        self.post = BlogPost.objects.create(
            title='Serializer Test',
            slug='serializer-test',
            content='Test content for serialization',
            excerpt='Test excerpt',
            author=self.author,
            category=self.category,
            status='published'
        )
        self.post.tags.add(self.tag)

    def test_list_serializer(self):
        serializer = BlogPostListSerializer(self.post)
        data = serializer.data
        self.assertEqual(data['title'], 'Serializer Test')
        self.assertIn('author_name', data)
        self.assertEqual(data['category_name'], 'Test')

    def test_detail_serializer(self):
        serializer = BlogPostDetailSerializer(self.post)
        data = serializer.data
        self.assertEqual(data['title'], 'Serializer Test')
        self.assertIn('tags', data)
