from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, View, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django import forms
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review, Service

# Vue pour la liste des catégories (page d'accueil)
class CategoryListView(ListView):
    model = Category
    template_name = 'index.html'
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'index'
        return context

# Vue pour la liste des produits par catégorie
class ProductListView(ListView):
    model = Product
    template_name = 'pharmacy/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            return Product.objects.filter(category__slug=category_slug)
        return Product.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'services'  # On peut considérer que la liste des produits fait partie des "services"
        return context

# Vue pour les détails d'un produit
class ProductDetailView(DetailView):
    model = Product
    template_name = 'pharmacy/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.object.reviews.all()
        context['active_page'] = 'services'  # Détails du produit liés aux "services"
        return context

# Vue pour ajouter un produit au panier
class AddToCartView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))
        
        # Vérifier le stock
        if quantity > product.stock:
            messages.error(request, f"Stock insuffisant pour {product.name}.")
            return redirect('product_detail', slug=product.slug)

        # Récupérer ou créer le panier de l'utilisateur
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not item_created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        
        cart_item.save()
        messages.success(request, f"{product.name} ajouté au panier.")
        return redirect('cart_detail')

# Vue pour afficher le panier
class CartDetailView(LoginRequiredMixin, View):
    def get(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        return render(request, 'pharmacy/cart_detail.html', {'cart': cart, 'active_page': 'cart'})

# Vue pour supprimer un article du panier
class RemoveFromCartView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, "Article retiré du panier.")
        return redirect('cart_detail')

# Vue pour passer une commande
class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        return render(request, 'pharmacy/checkout.html', {'cart': cart, 'active_page': 'checkout'})

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        shipping_address = request.POST.get('shipping_address')
        prescription_file = request.FILES.get('prescription_file')

        # Vérifier si une ordonnance est requise
        requires_prescription = any(item.product.requires_prescription for item in cart.items.all())
        if requires_prescription and not prescription_file:
            messages.error(request, "Une ordonnance est requise pour certains produits.")
            return redirect('checkout')

        # Calculer le prix total
        total_price = cart.items.aggregate(total=Sum('product__price'))['total'] or 0

        # Créer la commande
        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
            shipping_address=shipping_address,
            prescription_file=prescription_file
        )

        # Créer les articles de la commande
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Vider le panier
        cart.items.all().delete()
        messages.success(request, "Commande passée avec succès.")
        return redirect('order_confirmation', order_id=order.id)

# Vue pour confirmer la commande
class OrderConfirmationView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'pharmacy/order_confirmation.html', {'order': order, 'active_page': 'order_confirmation'})

# Vue pour ajouter un avis sur un produit
class AddReviewView(LoginRequiredMixin, CreateView):
    model = Review
    fields = ['rating', 'comment']
    template_name = 'pharmacy/add_review.html'

    def form_valid(self, form):
        product = get_object_or_404(Product, slug=self.kwargs['slug'])
        form.instance.user = self.request.user
        form.instance.product = product
        try:
            return super().form_valid(form)
        except ValidationError:
            messages.error(self.request, "Vous avez déjà laissé un avis sur ce produit.")
            return redirect('product_detail', slug=product.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'services'  # Avis lié aux produits, donc "services"
        return context

    def get_success_url(self):
        return reverse_lazy('product_detail', kwargs={'slug': self.kwargs['slug']})

# Formulaire pour la page Contact
class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Votre nom")
    email = forms.EmailField(label="Votre email")
    message = forms.CharField(widget=forms.Textarea, label="Votre message")

# Formulaire pour la page Appointment
class AppointmentForm(forms.Form):
    name = forms.CharField(max_length=100, label="Votre nom")
    email = forms.EmailField(label="Votre email")
    phone = forms.CharField(max_length=20, label="Numéro de téléphone", required=False)
    date = forms.DateField(label="Date souhaitée", widget=forms.DateInput(attrs={'type': 'date'}))
    message = forms.CharField(widget=forms.Textarea, label="Détails", required=False)

# Vue pour la page About
class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'about'
        return context

# Vue pour la page Team
class TeamView(TemplateView):
    template_name = 'team.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'team'
        return context

# Vue pour la page Feature
class FeatureView(TemplateView):
    template_name = 'feature.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'feature'
        return context

# Vue pour la page Testimonial
class TestimonialView(TemplateView):
    template_name = 'testimonial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'testimonial'
        return context

# Vue pour la page Contact
class ContactView(FormView):
    template_name = 'contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        messages.success(self.request, "Merci pour votre message ! Nous vous répondrons bientôt.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'contact'
        return context

# Vue pour la page Appointment
class AppointmentView(FormView):
    template_name = 'appointment.html'
    form_class = AppointmentForm
    success_url = reverse_lazy('appointment')

    def form_valid(self, form):
        messages.success(self.request, "Votre demande de rendez-vous a été enregistrée !")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'appointment'
        return context

# Vue pour la page 404 personnalisée
def custom_404(request):
    return render(request, '404.html', {'active_page': '404'})

# Vue pour la page de login
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                
                send_mail(
                    'Connexion réussie',
                    f'Bonjour {username}, vous venez de vous connecter à votre compte.',
                    'angeemmanuel2k06@gmail.com',
                    [user.email],
                    fail_silently=False,
                )
                
                return redirect('index')
            else:
                messages.error(request, "Vous n'avez pas les droits d'accès nécessaires.")
                return render(request, 'login.html', {'active_page': 'login'})
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            
            User = get_user_model()
            try:
                user_obj = User.objects.get(username=username)
                send_mail(
                    'Tentative de connexion échouée',
                    'Une tentative de connexion à votre compte a échoué.',
                    'angeemmanuel2k06@gmail.com',
                    [user_obj.email],
                    fail_silently=False,
                )
            except User.DoesNotExist:
                pass
            
            return render(request, 'login.html', {'active_page': 'login'})
    
    return render(request, 'login.html', {'active_page': 'login'})

# Vue pour la déconnexion
@require_http_methods(['GET', 'POST'])
@never_cache
def logout_view(request):
    """
    Log out the user and render the logged out template.
    """
    if request.method == 'POST':
        @method_decorator(csrf_protect)
        def post_handler():
            auth_logout(request)
            return render(request, 'logout.html', {'active_page': 'logout'})
        return post_handler()
    
    auth_logout(request)
    return render(request, 'logout.html', {'active_page': 'logout'})

# Vue pour les services
@require_http_methods(['GET'])
def service_view(request):
    """
    Affiche la liste des services médicaux dynamiques.
    """
    services = Service.objects.all()
    return render(request, 'services.html', {'services': services, 'active_page': 'services'})

# Vue pour les détails d'un service
def service_detail_view(request, service_id):
    """
    Affiche les détails d'un service.
    """
    service = get_object_or_404(Service, id=service_id)
    services = Service.objects.all()  # Pour le footer
    return render(request, 'service_detail.html', {'service': service, 'services': services, 'active_page': 'services'})