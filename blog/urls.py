from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'posts', views.BlogPostViewSet, basename='blogpost')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'tags', views.TagViewSet, basename='tag')

app_name = 'blog'

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', views.generate_blog_content, name='generate_blog'),
    path('save/', views.save_generated_blog, name='save_blog'),
]
