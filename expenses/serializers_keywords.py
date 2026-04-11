"""
DRF serializers and viewsets for CategoryKeyword management API.
"""
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from .models import CategoryKeyword, Category


class CategoryKeywordSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)

    class Meta:
        model = CategoryKeyword
        fields = ['id', 'category', 'category_name', 'category_icon', 'keyword', 'added_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'added_by']

    def create(self, validated_data):
        """Create a new keyword with added_by='user'"""
        validated_data['added_by'] = 'user'
        return super().create(validated_data)


class CategoryWithKeywordsSerializer(serializers.ModelSerializer):
    """Serialize a category with its associated keywords grouped"""
    keywords = CategoryKeywordSerializer(source='keywords.all', many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'is_active', 'keywords']
        read_only_fields = ['id']


class CategoryKeywordViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing category keywords.
    
    Endpoints:
    - GET /api/category-keywords/ - List all keywords for user
    - POST /api/category-keywords/ - Add a new keyword
    - DELETE /api/category-keywords/<id>/ - Delete a keyword
    - GET /api/category-keywords/grouped/ - List keywords grouped by category
    """
    serializer_class = CategoryKeywordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        """Return keywords only for the authenticated user's categories"""
        return CategoryKeyword.objects.filter(
            category__user=self.request.user
        ).select_related('category')

    def perform_create(self, serializer):
        """Ensure keyword is only added to user's categories"""
        category = serializer.validated_data.get('category')

        # Verify the category belongs to the user
        if category.user != self.request.user:
            raise serializers.ValidationError("You can only add keywords to your own categories.")

        try:
            serializer.save()
        except IntegrityError:
            raise serializers.ValidationError(
                f"Keyword '{serializer.validated_data['keyword']}' already exists for this category."
            )

    def perform_destroy(self, instance):
        """Ensure keyword can only be deleted by its owner"""
        if instance.category.user != self.request.user:
            raise serializers.ValidationError("You can only delete keywords from your own categories.")

        # Allow deletion only if added_by is 'user' (user-created), not system defaults
        # Uncomment below to prevent deletion of system keywords:
        # if instance.added_by == 'system':
        #     raise serializers.ValidationError("System keywords cannot be deleted.")

        instance.delete()

    @action(detail=False, methods=['get'])
    def grouped(self, request):
        """
        Return all keywords grouped by category.
        Useful for displaying in UI.
        
        Response format:
        [
            {
                "id": 1,
                "name": "Food",
                "icon": "🍔",
                "color": "#FF5722",
                "is_active": true,
                "keywords": [
                    {"id": 1, "keyword": "lunch", "added_by": "system", ...},
                    ...
                ]
            }
        ]
        """
        categories = Category.objects.filter(
            user=request.user,
            is_active=True
        ).prefetch_related('keywords')

        serializer = CategoryWithKeywordsSerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_add(self, request):
        """
        Bulk add multiple keywords at once.
        
        Request format:
        {
            "keywords": [
                {"category": 1, "keyword": "lunch"},
                {"category": 1, "keyword": "dinner"},
                ...
            ]
        }
        """
        keywords_data = request.data.get('keywords', [])

        if not keywords_data:
            return Response(
                {'error': 'No keywords provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {
            'added': [],
            'skipped': [],
            'errors': []
        }

        for keyword_item in keywords_data:
            category_id = keyword_item.get('category')
            keyword = keyword_item.get('keyword', '').strip().lower()

            if not keyword:
                results['errors'].append('Empty keyword provided')
                continue

            try:
                # Verify category belongs to user
                category = Category.objects.get(id=category_id, user=request.user)

                # Try to create keyword
                kw, created = CategoryKeyword.objects.get_or_create(
                    category=category,
                    keyword=keyword,
                    defaults={'added_by': 'user'}
                )

                if created:
                    results['added'].append({
                        'id': kw.id,
                        'category': category.name,
                        'keyword': kw.keyword
                    })
                else:
                    results['skipped'].append({
                        'category': category.name,
                        'keyword': kw.keyword,
                        'reason': 'Already exists'
                    })

            except Category.DoesNotExist:
                results['errors'].append(f"Category {category_id} not found or not owned by you")
            except Exception as e:
                results['errors'].append(f"Error adding keyword '{keyword}': {str(e)}")

        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """
        Bulk delete multiple keywords at once.
        
        Request format:
        {
            "ids": [1, 2, 3]
        }
        """
        keyword_ids = request.data.get('ids', [])

        if not keyword_ids:
            return Response(
                {'error': 'No keyword IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only delete keywords belonging to user's categories
        deleted_count, _ = CategoryKeyword.objects.filter(
            id__in=keyword_ids,
            category__user=request.user
        ).delete()

        return Response(
            {'deleted': deleted_count},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get keywords for a specific category.
        
        Query parameter: category_id=<id>
        """
        category_id = request.query_params.get('category_id')

        if not category_id:
            return Response(
                {'error': 'category_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = Category.objects.get(id=category_id, user=request.user)
        except Category.DoesNotExist:
            return Response(
                {'error': 'Category not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        keywords = category.keywords.all()
        serializer = CategoryKeywordSerializer(keywords, many=True)

        return Response({
            'category': {
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
            },
            'keywords': serializer.data
        })
