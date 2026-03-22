from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from blog import views as blog_views

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.svg', permanent=True)),
    path('admin/', admin.site.urls),
    
    # Syringly app routes (Q&A for medics) - MUST be before root
    path('syringly/', include('syringly.urls')),

    # Blog app routes
    path('blog/', include('blog.urls')),
    path('blog/', include([
        path('', blog_views.blog_index, name='blog_index'),
        path('create/', blog_views.blog_create, name='blog_create'),
        path('<slug:slug>/', blog_views.blog_detail, name='post_detail'),
        path('<slug:slug>/edit/', blog_views.blog_edit, name='blog_edit'),
    ])),
    
    # Chat app routes
    path('chat/', include('chat.urls')),
    
    # Unified authentication URLs (at root level)
    path('login/', auth_views.LoginView.as_view(template_name='telemed/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', include('accounts.urls')),
    
    # JWT Token URLs
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Root URL - landing page and main app routes (MUST be last)
    path('', include('telemed.urls')),
    
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='telemed/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='telemed/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='telemed/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='telemed/password_reset_complete.html'), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
