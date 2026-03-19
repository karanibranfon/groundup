import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response

from .models import Category, Tag, BlogPost
from .serializers import (
    CategorySerializer, TagSerializer, 
    BlogPostListSerializer, BlogPostDetailSerializer,
    BlogGenerateSerializer
)
from .services.ai_writer import HealthcareAIBlogWriter


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_staff


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Category.objects.all()
        if self.request.query_params.get('search'):
            search = self.request.query_params.get('search')
            queryset = queryset.filter(name__icontains=search)
        return queryset


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Tag.objects.all()
        if self.request.query_params.get('search'):
            search = self.request.query_params.get('search')
            queryset = queryset.filter(name__icontains=search)
        return queryset


class BlogPostViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        queryset = BlogPost.objects.select_related('author', 'category').prefetch_related('tags')
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            if not self.request.user.is_authenticated or not self.request.user.is_staff:
                queryset = queryset.filter(status='published')
        
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        tag_slug = self.request.query_params.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        
        author_username = self.request.query_params.get('author')
        if author_username:
            queryset = queryset.filter(author__username=author_username)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(content__icontains=search)
        
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return BlogPostListSerializer
        return BlogPostDetailSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_blog_content(request):
    serializer = BlogGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    topic = serializer.validated_data['topic']
    category_name = serializer.validated_data.get('category', '')
    target_audience = serializer.validated_data.get('target_audience', '')
    tone = serializer.validated_data.get('tone', 'educational')
    length = serializer.validated_data.get('length', 'medium')
    
    try:
        ai_writer = HealthcareAIBlogWriter()
        result = ai_writer.generate_blog_post(
            topic=topic,
            category_name=category_name,
            target_audience=target_audience,
            tone=tone,
            length=length
        )
        return Response(result)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@require_http_methods(["POST"])
def save_generated_blog(request):
    data = json.loads(request.body)
    
    title = data.get('title', '')
    content = data.get('content', '')
    excerpt = data.get('excerpt', '')
    category_name = data.get('category', '')
    tags = data.get('tags', [])
    ai_model = data.get('ai_model', 'unknown')
    
    if not title or not content:
        return JsonResponse({'error': 'Title and content are required'}, status=400)
    
    category = None
    if category_name:
        category, _ = Category.objects.get_or_create(
            name=category_name,
            defaults={'slug': category_name.lower().replace(' ', '-')}
        )
    
    post = BlogPost.objects.create(
        title=title,
        content=content,
        excerpt=excerpt,
        category=category,
        author=request.user,
        status='draft',
        is_ai_generated=True,
        ai_model_used=ai_model
    )
    
    for tag_name in tags:
        tag, _ = Tag.objects.get_or_create(name=tag_name)
        post.tags.add(tag)
    
    return JsonResponse({
        'id': post.id,
        'slug': post.slug,
        'message': 'Blog post saved successfully'
    })


def blog_index(request):
    posts = BlogPost.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags')[:20]
    categories = Category.objects.all()
    tags = Tag.objects.all()
    
    context = {
        'posts': posts,
        'categories': categories,
        'tags': tags,
    }
    return render(request, 'blog/post_list.html', context)


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    
    if post.status != 'published':
        if not request.user.is_authenticated or (request.user != post.author and not request.user.is_staff):
            from django.http import Http404
            raise Http404("Post not found")
    
    related_posts = BlogPost.objects.filter(
        category=post.category,
        status='published'
    ).exclude(id=post.id).prefetch_related('tags')[:3]
    
    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'blog/post_detail.html', context)


@login_required
def blog_create(request):
    categories = Category.objects.all()
    context = {'categories': categories}
    return render(request, 'blog/post_create.html', context)


@login_required
def blog_edit(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if request.user != post.author and not request.user.is_staff:
        from django.http import Http403
        raise Http403("You don't have permission to edit this post")
    
    categories = Category.objects.all()
    context = {'post': post, 'categories': categories}
    return render(request, 'blog/post_create.html', context)
