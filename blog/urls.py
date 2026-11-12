from django.urls import path
from .views import Categories, PostDetail, PostList

urlpatterns = [
    path('categories/', Categories.as_view()),
    path('posts/', PostList.as_view()),
    path('posts/<slug:slug>/', PostDetail.as_view()),
]
