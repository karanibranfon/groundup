from django.contrib import admin
from .models import Category, Tag, BlogPost


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'category', 'is_ai_generated', 'published_at', 'created_at']
    list_filter = ['status', 'category', 'is_ai_generated', 'created_at', 'published_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at', 'published_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content')
        }),
        ('Categorization', {
            'fields': ('category', 'tags')
        }),
        ('Metadata', {
            'fields': ('author', 'status', 'is_ai_generated', 'ai_model_used', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
