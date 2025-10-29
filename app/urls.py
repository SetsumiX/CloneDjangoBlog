from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/create', views.post_create, name='post_create'),
    path('post/<int:post_id>/delete', views.del_post, name='del_post'),
]
