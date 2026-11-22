from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class Category(models.Model):
    DEPARTMENTS = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('kids', 'Kids'),
        ('accessories', 'Accessories'),
        ('footwear', 'Footwear'),
        ('watches', 'Watches')
    ]

    name = models.CharField(max_length=100)
    department = models.CharField(max_length=20, choices=DEPARTMENTS)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    name = models.CharField(max_length=220)
    brand = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    material = models.CharField(max_length=120, blank=True)
    fit = models.CharField(max_length=80, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True)
    deal_ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return int((self.mrp - self.price) * 100 / self.mrp)
        return 0

    @property
    def deal_active(self):
        return bool(self.deal_ends_at and self.deal_ends_at > timezone.now())

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    @property
    def average_rating(self):
        vals = list(self.reviews.values_list('rating', flat=True))
        return round(sum(vals) / len(vals), 1) if vals else None

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    colour = models.CharField(max_length=40)
    colour_hex = models.CharField(max_length=7, default='#722B3A')
    size = models.CharField(max_length=12)
    sku = models.CharField(max_length=60, unique=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='variants/', blank=True)
class Meta:
    unique_together = ('product', 'size')
    def __str__(self):
        return f'{self.product} / {self.colour} / {self.size}'


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery'
    )
    image = models.ImageField(upload_to='gallery/')
    alt_text = models.CharField(max_length=160, blank=True)


class Address(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    line1 = models.CharField(max_length=220)
    line2 = models.CharField(max_length=220, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=12)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.full_name}, {self.city}'


class CartItem(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('user', 'variant')


class WishlistItem(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'product')


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField(default=10)
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def valid(self, subtotal):
        return (
            self.active
            and subtotal >= self.minimum_order
            and (not self.expires_at or self.expires_at > timezone.now())
        )


class Order(models.Model):
    STATUSES = [
        ('placed', 'Placed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]

    PAYMENTS = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay Test')
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    order_number = models.CharField(max_length=24, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default='placed'
    )
    payment_method = models.CharField(max_length=12, choices=PAYMENTS)
    payment_status = models.CharField(max_length=20, default='pending')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Razorpay payment details
    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )
    razorpay_payment_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )
    razorpay_signature = models.CharField(
        max_length=255,
        blank=True
    )
    payment_failure_reason = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    product_name = models.CharField(max_length=220)
    colour = models.CharField(max_length=40)
    size = models.CharField(max_length=12)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=120)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product} - {self.rating} stars'


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f'{self.name} - {self.email}'
