from django.urls import path
from .views import (
    CategoryListView,
    ProductListView,
    ProductDetailView,
    AddToCartView,
    CartDetailView,
    RemoveFromCartView,
    CheckoutView,
    OrderConfirmationView,
    AddReviewView,
    AboutView,
    TeamView,
    FeatureView,
    TestimonialView,
    ContactView,
    AppointmentView,
    service_view,
    service_detail_view,
    login_view,
    logout_view,
    custom_404,
)
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from rest_framework.permissions import IsAuthenticated
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.contrib.auth.decorators import user_passes_test

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=False,
    authentication_classes=[SessionAuthentication, BasicAuthentication],  # Authentification requise
    permission_classes=[IsAuthenticated],  # Nécessite d'être connecté
)

# Fonction pour vérifier si l'utilisateur est admin
def is_admin(user):
    return user.is_authenticated and user.is_staff
# Vue pour la documentation avec vérification d'accès et template personnalisé
api_docs_view = user_passes_test(is_admin, login_url='access_denied')(schema_view.with_ui('swagger', cache_timeout=0))

# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets
from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register(r'categories', viewsets.CategoryViewSet)
router.register(r'products', viewsets.ProductViewSet)
router.register(r'carts', viewsets.CartViewSet, basename='cart')
router.register(r'orders', viewsets.OrderViewSet, basename='order')
router.register(r'reviews', viewsets.ReviewViewSet, basename='review')

urlpatterns = [
    # Liste des catégories
    path('', CategoryListView.as_view(), name='index'),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    path('', CategoryListView.as_view(), name='index'),
    path('products/<slug:category_slug>/', ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('add-to-cart/<int:product_id>/', AddToCartView.as_view(), name='add_to_cart'),
    path('cart/', CartDetailView.as_view(), name='cart_detail'),
    path('remove-from-cart/<int:item_id>/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-confirmation/<int:order_id>/', OrderConfirmationView.as_view(), name='order_confirmation'),
    path('add-review/<slug:slug>/', AddReviewView.as_view(), name='add_review'),
    path('about/', AboutView.as_view(), name='about'),
    path('team/', TeamView.as_view(), name='team'),
    path('feature/', FeatureView.as_view(), name='feature'),
    path('testimonial/', TestimonialView.as_view(), name='testimonial'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('appointment/', AppointmentView.as_view(), name='appointment'),
    path('404/', custom_404, name='404'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('services/', service_view, name='services'),
    path('services/<int:service_id>/', service_detail_view, name='service_detail'),
]
