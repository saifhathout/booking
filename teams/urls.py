from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('find/', views.find_players, name='find_players'),
    path('create/', views.create_post, name='create_post'),
    path('join/<int:post_id>/', views.join_post, name='join_post'),
    path('chat/<int:post_id>/', views.chat_view, name='chat'),
    path('delete-chat/<int:post_id>/', views.delete_chat, name='delete_chat'),
    path('my-chats/', views.my_chats, name='my_chats'),
]