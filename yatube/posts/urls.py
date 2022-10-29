from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    # Страница группы
    path('group/<slug:slug>/', views.group_posts, name='group_list'),
    # Профайл пользователя
    path('profile/<str:username>/', views.profile, name='profile'),
    # Страница для создания записи
    path('create/', views.post_create, name='post_create'),
    # Страница редактирования записи
    path('posts/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    # Страница для просмотра записи
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    # Комментарии
    path(
        'posts/<int:post_id>/comment/',
        views.add_comment,
        name='add_comment'
    ),
    # Страница с постами авторов, на которых подписан пользователь
    path('follow/', views.follow_index, name='follow_index'),
    # Старница для подписки на нового автора
    path(
        'profile/<str:username>/follow/',
        views.profile_follow,
        name='profile_follow'
    ),
    # Страница для отписки от автора
    path(
        'profile/<str:username>/unfollow/',
        views.profile_unfollow,
        name='profile_unfollow'
    ),
    # Главная страница
    path('', views.index, name='index'),
]
