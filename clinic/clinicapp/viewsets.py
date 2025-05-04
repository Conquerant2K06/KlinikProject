# viewsets.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review
from .serializers import (
    CategorySerializer, ProductSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, OrderItemSerializer, ReviewSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_slug = request.query_params.get('category', None)
        if category_slug:
            products = Product.objects.filter(category__slug=category_slug)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "Category parameter is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def prescription_required(self, request):
        requires_prescription = request.query_params.get('required', 'true').lower() == 'true'
        products = Product.objects.filter(requires_prescription=requires_prescription)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response(
                {"error": "Product ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if product requires prescription
        if product.requires_prescription:
            # You might want to handle this case differently
            # For now, just informing the user
            return Response(
                {"error": "This product requires a prescription"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock availability
        if quantity > product.stock:
            return Response(
                {"error": f"Not enough stock. Only {product.stock} available."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        cart = self.get_object()
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response(
                {"error": "Item ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_quantity(self, request, pk=None):
        cart = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or not quantity:
            return Response(
                {"error": "Item ID and quantity are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                return Response(
                    {"error": "Quantity must be positive"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            item = CartItem.objects.get(id=item_id, cart=cart)
            
            # Check stock availability
            if quantity > item.product.stock:
                return Response(
                    {"error": f"Not enough stock. Only {item.product.stock} available."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            item.quantity = quantity
            item.save()
            
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {"error": "Invalid quantity value"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        # Get user's active cart
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "No active cart found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if cart is empty
        cart_items = cart.items.all()
        if not cart_items:
            return Response(
                {"error": "Cart is empty"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any product requires prescription
        requires_prescription = any(item.product.requires_prescription for item in cart_items)
        if requires_prescription and not request.data.get('prescription_file'):
            return Response(
                {"error": "Prescription file is required for some products in your cart"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate total price
        total_price = sum(item.get_total_price() for item in cart_items)
        
        # Create order
        order_data = {
            'user': request.user,
            'total_price': total_price,
            'shipping_address': request.data.get('shipping_address', ''),
            'prescription_file': request.data.get('prescription_file')
        }
        order = Order.objects.create(**order_data)
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Update product stock
            product = cart_item.product
            product.stock -= cart_item.quantity
            product.save()
        
        # Clear the cart
        cart.items.all().delete()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        
        if order.status == 'delivered':
            return Response(
                {"error": "Cannot cancel a delivered order"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restore product stock
        for order_item in order.items.all():
            product = order_item.product
            product.stock += order_item.quantity
            product.save()
        
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.all()
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        reviews = Review.objects.filter(user=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def product_reviews(self, request):
        product_slug = request.query_params.get('product', None)
        if not product_slug:
            return Response(
                {"error": "Product slug is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            product = Product.objects.get(slug=product_slug)
            reviews = Review.objects.filter(product=product)
            serializer = self.get_serializer(reviews, many=True)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )