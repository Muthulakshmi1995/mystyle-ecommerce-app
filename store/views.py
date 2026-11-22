import uuid
from decimal import Decimal
import razorpay
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q, Sum, F
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import *
from .forms import RegisterForm, AddressForm, ReviewForm

DEPARTMENTS = [('men','Men'),('women','Women'),('kids','Kids'),('accessories','Accessories')]
ACCESSORY_TYPES = {'bags':'accessories', 'footwear':'footwear', 'watches':'watches'}


def home(request):
    sections=[]
    for slug,title in DEPARTMENTS:
        if slug=='accessories':
            qs=Product.objects.filter(is_active=True,category__department__in=['accessories','footwear','watches'])
            # A balanced preview: show bags, footwear and watches together under Accessories.
            featured=[]
            for sub in ['accessories','footwear','watches']:
                featured.extend(list(qs.filter(category__department=sub).order_by('name')[:2]))
            products=featured[:5]
        else:
            products=Product.objects.filter(is_active=True,category__department=slug).order_by('name')[:5]
        sections.append({'slug':slug,'title':title,'products':products})
    return render(request,'store/home.html',{'home_sections':sections})


def department(request, department):
    allowed=['men','women','kids','accessories','footwear','watches']
    if department not in allowed: return redirect('home')
    selected_type=request.GET.get('type','').lower()
    if department=='accessories' and selected_type in ACCESSORY_TYPES:
        departments=[ACCESSORY_TYPES[selected_type]]
        heading={'bags':'Bags','footwear':'Footwear','watches':'Watches'}[selected_type]
    elif department=='accessories':
        departments=['accessories','footwear','watches']; heading='Accessories'
    else:
        departments=[department]; heading=department.title()
    cats=Category.objects.filter(department__in=departments)
    products=Product.objects.filter(category__in=cats,is_active=True).prefetch_related('variants').order_by('name')
    sort=request.GET.get('sort')
    if sort=='low': products=products.order_by('price')
    elif sort=='high': products=products.order_by('-price')
    elif sort=='new': products=products.order_by('-created_at')
    return render(request,'store/listing.html',{'products':products,'categories':cats,'heading':heading,'is_accessories':department=='accessories'})


def category(request, slug):
    cat=get_object_or_404(Category,slug=slug)
    products=Product.objects.filter(category=cat,is_active=True).prefetch_related('variants')
    return render(request,'store/listing.html',{'products':products,'heading':cat.name,'categories':[cat]})


def offers(request):
    products=Product.objects.filter(is_active=True,price__lt=F('mrp')).order_by('-created_at').prefetch_related('variants')
    return render(request,'store/listing.html',{'products':products,'heading':'Offers & Deals','offers_page':True})


def search(request):
    q=request.GET.get('q','').strip()
    products=Product.objects.filter(is_active=True).filter(
        Q(name__icontains=q)|Q(brand__icontains=q)|Q(description__icontains=q)|
        Q(category__name__icontains=q)|Q(category__department__icontains=q)
    ).distinct().prefetch_related('variants') if q else Product.objects.none()
    return render(request,'store/listing.html',{'products':products,'heading':f'Search: {q}'})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    recommended_products = Product.objects.filter(
    category=product.category,
    is_active=True
).exclude(id=product.id).order_by('-created_at')[:4]
    variants = list(product.variants.all().order_by('size', 'id'))

    size_order = [
        'XS', 'S', 'M', 'L', 'XL',
        '2-3Y', '4-5Y', '6-7Y', '8-9Y', '10-11Y',
        '6', '7', '8', '9', '10', 'One Size'
    ]

    size_options = [
        {
            'size': variant.size,
            'variant_id': variant.id,
            'stock': variant.stock
        }
        for variant in sorted(
            variants,
            key=lambda variant: (
                size_order.index(variant.size)
                if variant.size in size_order else 99
            )
        )
    ]

    available_stock = sum(
        variant.stock for variant in variants
    )

    return render(request, 'store/product.html', {
        'product': product,
        'size_options': size_options,
        'available_stock': available_stock,
        'reviews': product.reviews.all(),
        'recommended_products': recommended_products,
    })


def register(request):
    # Staff accounts must sign out of the admin session before creating/using a customer account.
    if request.user.is_authenticated and request.user.is_staff:
        messages.info(request,'Please use the Staff Logout link before creating a customer account.')
        return redirect('home')
    if request.user.is_authenticated:
        return redirect('home')
    form=RegisterForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        user=form.save()
        login(request,user)
        messages.success(request,'Welcome to MYSTYLE! Your customer account is ready.')
        return redirect('home')
    return render(request,'store/register.html',{'form':form})


def customer_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard' if request.user.is_staff else 'home')
    form=AuthenticationForm(request,data=request.POST or None)
    if request.method=='POST' and form.is_valid():
        user=form.get_user()
        if user.is_staff:
            form.add_error(None,'This is a staff/admin account. Use the Admin Portal instead.')
        else:
            login(request,user)
            return redirect(request.GET.get('next') or 'home')
    return render(request,'store/login.html',{'form':form})


@login_required
@require_POST
def customer_logout(request):
    logout(request)
    messages.success(request,'You have been logged out safely.')
    return redirect('home')


@login_required
def add_to_cart(request,variant_id):
    if request.user.is_staff:
        messages.warning(request,'You are signed in with a Staff/Admin account. Please Logout, then Register or Login with a Customer account to shop.')
        return redirect('home')
    if request.method!='POST': return redirect('home')
    variant=get_object_or_404(ProductVariant.objects.select_related('product'),id=variant_id)
    if not variant.product.is_active:
        messages.error(request,'This product is no longer available.')
        return redirect('home')
    if variant.stock<1:
        messages.error(request,'This size is currently out of stock.')
        return redirect('product_detail',slug=variant.product.slug)
    try: quantity=max(1,min(int(request.POST.get('quantity',1) or 1),10))
    except (TypeError,ValueError): quantity=1
    item,created=CartItem.objects.get_or_create(user=request.user,variant=variant)
    new_quantity=quantity if created else item.quantity+quantity
    if new_quantity>variant.stock:
        messages.error(request,f'Only {variant.stock} available for {variant.product.name} in size {variant.size}.')
    else:
        item.quantity=new_quantity; item.save()
        messages.success(request,f'{variant.product.name} added to your shopping cart.')
    return redirect('cart')


@login_required
def cart(request):
    if request.user.is_staff: return redirect('dashboard')
    items=CartItem.objects.filter(user=request.user,variant__product__is_active=True).select_related('variant__product').order_by('id')
    subtotal=sum((i.quantity*i.variant.product.price for i in items),Decimal('0'))
    return render(request,'store/cart.html',{'items':items,'subtotal':subtotal})


@login_required
@require_POST
def update_cart(request,item_id):
    if request.user.is_staff: return redirect('dashboard')
    item=get_object_or_404(CartItem,id=item_id,user=request.user)
    try: qty=max(1,int(request.POST.get('quantity',1)))
    except (TypeError,ValueError): qty=1
    if qty<=item.variant.stock:
        item.quantity=qty; item.save(); messages.success(request,'Cart quantity updated.')
    else: messages.error(request,'Not enough stock available.')
    return redirect('cart')


@login_required
@require_POST
def remove_cart(request,item_id):
    if request.user.is_staff: return redirect('dashboard')
    get_object_or_404(CartItem,id=item_id,user=request.user).delete()
    messages.success(request,'Product removed from cart.')
    return redirect('cart')


@login_required
@require_POST
def toggle_wishlist(request,product_id):
    if request.user.is_staff:
        messages.warning(request,'Please Logout from the Staff account and Login with a Customer account to use Wishlist.')
        return redirect('home')
    product=get_object_or_404(Product,id=product_id,is_active=True)
    item,created=WishlistItem.objects.get_or_create(user=request.user,product=product)
    if not created:
        item.delete(); messages.info(request,'Removed from wishlist.')
    else:
        messages.success(request,'Added to wishlist.')
    return redirect(request.POST.get('next') or 'wishlist')


@login_required
def wishlist(request):
    if request.user.is_staff: return redirect('dashboard')
    return render(request,'store/wishlist.html',{'items':WishlistItem.objects.filter(user=request.user,product__is_active=True).select_related('product').order_by('-id')})


@login_required
def profile(request):
    if request.user.is_staff: return redirect('dashboard')
    addresses=Address.objects.filter(user=request.user).order_by('-is_default','id')
    form=AddressForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        obj=form.save(commit=False); obj.user=request.user
        if obj.is_default: Address.objects.filter(user=request.user).update(is_default=False)
        if not addresses.exists(): obj.is_default=True
        obj.save(); messages.success(request,'Shipping address saved successfully.'); return redirect('profile')
    return render(request,'store/profile.html',{'addresses':addresses,'form':form})


@login_required
@require_POST
def delete_address(request,address_id):
    if request.user.is_staff: return redirect('dashboard')
    address=get_object_or_404(Address,id=address_id,user=request.user)
    was_default=address.is_default; address.delete()
    if was_default:
        next_address=Address.objects.filter(user=request.user).first()
        if next_address: next_address.is_default=True; next_address.save(update_fields=['is_default'])
    messages.success(request,'Address removed.')
    return redirect('profile')

@login_required
def checkout(request):
    if request.user.is_staff:
        return redirect('dashboard')

    items = list(
        CartItem.objects.filter(
            user=request.user,
            variant__product__is_active=True
        ).select_related('variant__product')
    )

    if not items:
        messages.info(request, 'Your cart is empty.')
        return redirect('cart')

    addresses = Address.objects.filter(user=request.user)

    subtotal = sum(
        (i.quantity * i.variant.product.price for i in items),
        Decimal('0')
    )

    coupon_code = ''
    discount = Decimal('0')
    total = subtotal
    coupon_applied = False
    coupon_error = ''
    payment_method = 'cod'

    if request.method == 'POST':
        if not addresses.exists():
            messages.error(request, 'Please save a shipping address first.')
            return redirect('profile')

        address = get_object_or_404(
            Address,
            id=request.POST.get('address'),
            user=request.user
        )

        method = request.POST.get('payment_method', 'cod')
        payment_method = method
        action = request.POST.get('action', 'continue_payment')

        coupon_code = request.POST.get('coupon', '').strip().upper()

        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code).first()

            if coupon and coupon.valid(subtotal):
                discount = (
                    subtotal * coupon.discount_percent / 100
                ).quantize(Decimal('0.01'))
                coupon_applied = True
            else:
                coupon_error = (
                    'Coupon is invalid, expired, or the minimum '
                    'order value has not been reached.'
                )

        elif action == 'apply_coupon':
            coupon_error = 'Please enter a coupon code.'

        total = subtotal - discount

        # APPLY COUPON ONLY - DO NOT START PAYMENT YET
        if action == 'apply_coupon':
            return render(request, 'store/checkout.html', {
                'items': items,
                'addresses': addresses,
                'subtotal': subtotal,
                'discount': discount,
                'total': total,
                'coupon_code': coupon_code,
                'coupon_applied': coupon_applied,
                'coupon_error': coupon_error,
                'payment_method': payment_method,
            })

        # DO NOT CONTINUE PAYMENT WITH AN INVALID COUPON
        if coupon_error:
            return render(request, 'store/checkout.html', {
                'items': items,
                'addresses': addresses,
                'subtotal': subtotal,
                'discount': discount,
                'total': total,
                'coupon_code': coupon_code,
                'coupon_applied': False,
                'coupon_error': coupon_error,
                'payment_method': payment_method,
            })

        # RAZORPAY TEST MODE
        if method == 'razorpay':

            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                messages.error(request, 'Razorpay keys are not configured.')
                return redirect('checkout')

            for item in items:
                if item.variant.stock < item.quantity:
                    messages.error(
                        request,
                        f'Insufficient stock for {item.variant.product.name} in size {item.variant.size}.'
                    )
                    return redirect('cart')

            order_number = 'MY' + uuid.uuid4().hex[:10].upper()
            amount_paise = int(total * 100)

            try:
                client = razorpay.Client(
                    auth=(
                        settings.RAZORPAY_KEY_ID,
                        settings.RAZORPAY_KEY_SECRET
                    )
                )

                payment_order = client.order.create(data={
                    'amount': amount_paise,
                    'currency': 'INR',
                    'receipt': order_number,
                    'payment_capture': 1
                })

                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user,
                        address=address,
                        order_number=order_number,
                        payment_method='razorpay',
                        payment_status='pending',
                        subtotal=subtotal,
                        discount=discount,
                        total=total,
                        razorpay_order_id=payment_order['id']
                    )

                    for item in items:
                        OrderItem.objects.create(
                            order=order,
                            variant=item.variant,
                            product_name=item.variant.product.name,
                            colour='Standard',
                            size=item.variant.size,
                            unit_price=item.variant.product.price,
                            quantity=item.quantity
                        )

                return render(request, 'store/checkout.html', {
                    'items': items,
                    'addresses': addresses,
                    'subtotal': subtotal,
                    'discount': discount,
                    'total': total,
                    'coupon_code': coupon_code,
                    'coupon_applied': False,
                    'coupon_error': '',
                    'payment_method': payment_method,
                    'razorpay_order_id': payment_order['id'],
                    'razorpay_amount': amount_paise,
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'order_number': order_number
                })

            except Exception:
                messages.error(
                    request,
                    'Unable to start Razorpay payment. Please try again.'
                )
                return redirect('checkout')

        # CASH ON DELIVERY
        elif method == 'cod':

            with transaction.atomic():
                locked = []

                for item in items:
                    variant = ProductVariant.objects.select_for_update().get(
                        pk=item.variant_id
                    )

                    if variant.stock < item.quantity:
                        messages.error(
                            request,
                            f'Insufficient stock for {variant.product.name} in size {variant.size}.'
                        )
                        return redirect('cart')

                    locked.append((item, variant))

                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    order_number='MY' + uuid.uuid4().hex[:10].upper(),
                    payment_method='cod',
                    subtotal=subtotal,
                    discount=discount,
                    total=total,
                    payment_status='pending'
                )

                for item, variant in locked:
                    OrderItem.objects.create(
                        order=order,
                        variant=variant,
                        product_name=variant.product.name,
                        colour='Standard',
                        size=variant.size,
                        unit_price=variant.product.price,
                        quantity=item.quantity
                    )

                    variant.stock -= item.quantity
                    variant.save(update_fields=['stock'])

                CartItem.objects.filter(user=request.user).delete()

            messages.success(
                request,
                'Your Cash on Delivery order has been placed.'
            )
            return redirect('order_detail', number=order.order_number)

        else:
            messages.error(request, 'Please select a valid payment method.')
            return redirect('checkout')

    return render(request, 'store/checkout.html', {
        'items': items,
        'addresses': addresses,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'coupon_code': coupon_code,
        'coupon_applied': coupon_applied,
        'coupon_error': coupon_error,
        'payment_method': payment_method,
    })

@login_required
@require_POST
def razorpay_verify(request):
    if request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Not allowed.'}, status=403)

    order_number = request.POST.get('order_number', '')
    payment_id = request.POST.get('razorpay_payment_id', '')
    gateway_order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')

    order = get_object_or_404(
        Order, order_number=order_number, user=request.user,
        payment_method='razorpay'
    )

    if order.payment_status == 'paid':
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('order_detail', args=[order.order_number])
        })

    if not all([payment_id, gateway_order_id, signature]):
        return JsonResponse({
            'success': False,
            'message': 'Payment details are incomplete.'
        }, status=400)

    if gateway_order_id != order.razorpay_order_id:
        return JsonResponse({
            'success': False,
            'message': 'Invalid payment order.'
        }, status=400)

    client = razorpay.Client(auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    ))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order.razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'Payment signature verification failed.'
        }, status=400)

    try:
        payment = client.payment.fetch(payment_id)
    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'Unable to confirm payment status. Please contact support.'
        }, status=502)

    if (
        payment.get('order_id') != order.razorpay_order_id
        or payment.get('status') != 'captured'
        or payment.get('amount') != int(order.total * 100)
        or payment.get('currency') != 'INR'
    ):
        return JsonResponse({
            'success': False,
            'message': 'Payment is not confirmed as captured.'
        }, status=400)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)

        if order.payment_status == 'paid':
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('order_detail', args=[order.order_number])
            })

        order_items = list(order.items.select_related('variant').all())
        locked_variants = []

        for order_item in order_items:
            if order_item.variant_id is None:
                return JsonResponse({
                    'success': False,
                    'message': 'Product stock information is missing. Please contact support.'
                }, status=409)

            variant = ProductVariant.objects.select_for_update().get(
                pk=order_item.variant_id
            )

            if variant.stock < order_item.quantity:
                return JsonResponse({
                    'success': False,
                    'message': 'Stock changed after payment. Please contact support for a refund.'
                }, status=409)

            locked_variants.append((variant, order_item.quantity))

        for variant, quantity in locked_variants:
            variant.stock -= quantity
            variant.save(update_fields=['stock'])

        order.payment_status = 'paid'
        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.paid_at = timezone.now()
        order.payment_failure_reason = ''
        order.save(update_fields=[
            'payment_status',
            'razorpay_payment_id',
            'razorpay_signature',
            'paid_at',
            'payment_failure_reason'
        ])

        CartItem.objects.filter(
            user=request.user,
            variant_id__in=[v.pk for v, q in locked_variants]
        ).delete()

    return JsonResponse({
        'success': True,
        'redirect_url': reverse('order_detail', args=[order.order_number])
    })


@login_required
@require_POST
def razorpay_failure(request):
    if request.user.is_staff:
        return JsonResponse({'success': False}, status=403)

    order_number = request.POST.get('order_number', '')

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
        payment_method='razorpay'
    )

    if order.payment_status != 'paid':
        order.payment_status = 'failed'
        order.payment_failure_reason = (
            request.POST.get('error_description', 'Payment failed')[:2000]
        )
        order.save(update_fields=[
            'payment_status',
            'payment_failure_reason'
        ])

    return JsonResponse({'success': True})


@login_required
def orders(request):
    if request.user.is_staff: return redirect('dashboard')
    return render(request,'store/orders.html',{'orders':Order.objects.filter(user=request.user).order_by('-created_at')})


@login_required
def order_detail(request,number):
    if request.user.is_staff: return redirect('dashboard')
    order=get_object_or_404(Order,order_number=number,user=request.user)
    return render(request,'store/order_detail.html',{'order':order})


def add_review(request,slug):
    if not request.user.is_authenticated: return redirect('login')
    if request.user.is_staff: return redirect('dashboard')
    product=get_object_or_404(Product,slug=slug,is_active=True)
    form=ReviewForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        Review.objects.update_or_create(user=request.user,product=product,defaults=form.cleaned_data)
        messages.success(request,'Review saved.')
    return redirect('product_detail',slug=slug)


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, 'Please fill in all fields.')
        else:
            ContactMessage.objects.create(
                name=name,
                email=email,
                message=message
            )

            try:
                send_mail(
                    subject='New MYSTYLE Contact Message',
                    message=(
                        f'Customer Name: {name}\n'
                        f'Customer Email: {email}\n\n'
                        f'Message:\n{message}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.EMAIL_HOST_USER],
                    fail_silently=False,
                )

                messages.success(
                    request,
                    'Thank you! Your message has been sent successfully.'
                )

            except Exception:
                messages.warning(
                    request,
                    'Your message has been saved. Our team will review it shortly.'
                )

    return render(request, 'store/contact.html')


def about(request): return render(request,'store/about.html')


@user_passes_test(lambda u:u.is_staff)
def dashboard(request):
    return render(request,'store/dashboard.html',{'orders':Order.objects.count(),'products':Product.objects.filter(is_active=True).count(),'users':User.objects.filter(is_staff=False).count(),'sales':Order.objects.filter(payment_status='paid').aggregate(s=Sum('total'))['s'] or 0,'recent':Order.objects.order_by('-created_at')[:8]})
