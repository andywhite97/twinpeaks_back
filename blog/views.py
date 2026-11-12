from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from .models import BlogCategory, BlogPost


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ('id', 'name', 'slug')


class PostSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    solutions = serializers.SerializerMethodField()

    def get_solutions(self, obj):
        return [{'id': item.pk, 'title': item.title} for item in obj.solutions.all() if item.is_active]

    class Meta:
        model = BlogPost
        fields = ('id', 'title', 'slug', 'excerpt', 'cover_image', 'cover_alt', 'author_name', 'category', 'solutions', 'published_at', 'reading_minutes', 'is_featured')


class PostDetailSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ('body',)


class BlogPagination(PageNumberPagination):
    page_size = 12


class PostList(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PostSerializer
    pagination_class = BlogPagination

    def get_queryset(self):
        posts = BlogPost.published().select_related('category').prefetch_related('solutions')
        category = self.request.query_params.get('category')
        if category:
            posts = posts.filter(category__slug=category)
        return posts.order_by('-is_featured', '-published_at', '-pk')


class PostDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PostDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return BlogPost.published().select_related('category').prefetch_related('solutions')


class Categories(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = BlogCategory.objects.all()
