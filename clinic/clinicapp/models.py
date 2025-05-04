from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Modèle pour les catégories de produits
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

# Modèle pour les produits (médicaments et produits de santé)
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    requires_prescription = models.BooleanField(default=False)  # Pour les médicaments sur ordonnance
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=200, unique=True)

    def __str__(self):
        return self.name

# Modèle pour le panier
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

# Modèle pour les articles dans le panier
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_total_price(self):
        return self.quantity * self.product.price

# Modèle pour les commandes
class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "En attente"),
        ("processing", "En traitement"),
        ("shipped", "Expédié"),
        ("delivered", "Livré"),
        ("cancelled", "Annulé"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    shipping_address = models.TextField()
    prescription_file = models.FileField(upload_to="prescriptions/", blank=True, null=True)  # Pour ordonnances

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

# Modèle pour les articles de la commande
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Prix au moment de la commande

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"

# Modèle pour les avis sur les produits
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

    class Meta:
        unique_together = ("product", "user")  # Un utilisateur ne peut commenter qu'une fois par produit

from django.db import models
from django.utils.translation import gettext_lazy as _

class Service(models.Model):
    """
    Modèle pour représenter un service médical.
    """
    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'))
    icon_class = models.CharField(_('classe icône'), max_length=50, help_text="Classe Font Awesome, ex. 'fa-heartbeat'")
    delay = models.CharField(_('délai animation'), max_length=10, default="0.1s", help_text="Délai pour l'animation WOW, ex. '0.1s'")
    
    class Meta:
        verbose_name = _('service')
        verbose_name_plural = _('services')

    def __str__(self):
        return self.name