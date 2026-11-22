def cart_count(request):
    if request.user.is_authenticated:
        return {
            'cart_count': sum(i.quantity for i in request.user.cart_items.filter(variant__product__is_active=True)),
            'wishlist_ids': list(request.user.wishlist_items.filter(product__is_active=True).values_list('product_id', flat=True)),
        }
    return {'cart_count': 0, 'wishlist_ids': []}
