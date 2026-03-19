from rest_framework import serializers
from .models import Category, Tag, BlogPost


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'posts_count']
        read_only_fields = ['id', 'slug', 'created_at']

    def get_posts_count(self, obj):
        return obj.posts.filter(status='published').count()


class BlogPostListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tags_list = serializers.ListField(write_only=True, required=False)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'author_name', 'category', 
            'category_name', 'tags', 'tags_list', 'status', 'is_ai_generated',
            'ai_model_used', 'published_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'author_name', 'is_ai_generated', 
                          'ai_model_used', 'published_at', 'created_at', 'updated_at']

    def create(self, validated_data):
        tags_data = validated_data.pop('tags_list', [])
        post = BlogPost.objects.create(**validated_data)
        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            post.tags.add(tag)
        return post


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_email = serializers.CharField(source='author.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tags_list = serializers.ListField(write_only=True, required=False)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'author', 'author_name',
            'author_email', 'category', 'category_name', 'category_slug', 'tags',
            'tags_list', 'status', 'is_ai_generated', 'ai_model_used',
            'published_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'author', 'author_name', 'author_email',
                          'is_ai_generated', 'ai_model_used', 'published_at',
                          'created_at', 'updated_at']

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags_list', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if tags_data is not None:
            instance.tags.clear()
            for tag_name in tags_data:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)
        return instance


class BlogGenerateSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500, help_text='Healthcare topic for blog generation')
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_audience = serializers.CharField(max_length=200, required=False, allow_blank=True)
    tone = serializers.ChoiceField(
        choices=['professional', 'friendly', 'educational', 'empathetic'],
        default='educational'
    )
    length = serializers.ChoiceField(
        choices=['short', 'medium', 'long'],
        default='medium'
    )
