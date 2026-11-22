
from django.contrib import admin
from .models import *


class VariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'mrp', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'brand')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [VariantInline, ImageInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('is_read',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'


admin.site.register([
    Category,
    ProductVariant,
    Address,
    CartItem,
    WishlistItem,
    Coupon,
    Order,
    OrderItem,
    Review
])
