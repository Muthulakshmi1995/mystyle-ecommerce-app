from pathlib import Path
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from store.models import Category, Product, ProductVariant, ProductImage, Coupon

COLOURS = [
    ('Burgundy', '#722B3A', 'burgundy'),
    ('Black', '#171717', 'black'),
    ('Ivory', '#F5F0E8', 'ivory'),
    ('Navy', '#24324A', 'navy'),
    ('Olive', '#68734A', 'olive'),
]

DEPARTMENTS = {
    'men': ('Men', 'men-collection', [
        'Burgundy Polo T-Shirt', 'Black Casual Shirt', 'White Crew Neck Tee',
        'Olive Overshirt', 'Slim Fit Blue Jeans', 'Charcoal Hoodie',
        'Cream Linen Shirt', 'Navy Chino Trousers', 'Blue Denim Jacket',
        'Tan Casual Shorts', 'Forest Green Sweatshirt', 'Striped Casual Shirt',
        'Black Track Pants', 'Light Blue Formal Shirt', 'Burgundy Bomber Jacket',
    ]),
    'women': ('Women', 'women-collection', [
        'Floral Midi Dress', 'Everyday Top', 'Straight Kurta', 'Wide Leg Trousers',
        'Co-ord Set', 'Evening Gown', 'Printed Shirt', 'Denim Jeans',
        'Pleated Skirt', 'Casual Tunic', 'Wrap Dress', 'Knit Top',
        'Palazzo Pants', 'Festive Kurta', 'Jumpsuit',
    ]),
    'kids': ('Kids', 'kids-collection', [
        'Boys Graphic Tee', 'Girls Party Frock', 'Kids Casual Set', 'Printed Hoodie',
        'Denim Dungaree', 'Girls Cotton Dress', 'Boys Polo Tee', 'Girls Floral Dress',
        'Kids Jogger Set', 'Kids Ethnic Kurta Set', 'Kids Shorts Set',
        'Kids Sweatshirt', 'Boys Casual Shirt', 'Girls Festive Outfit',
        'Kids Everyday Leggings Set',
    ]),
    'accessories': ('Accessories', 'accessories-collection', [
        'Everyday Tote Bag', 'Classic Shoulder Bag', 'Mini Crossbody Bag',
        'Leather Wallet', 'Slim Belt Bag', 'Quilted Handbag', 'Structured Satchel',
        'Travel Backpack', 'Evening Clutch', 'Mini Bucket Bag', 'Canvas Shopper Bag',
        'Phone Sling Bag', 'Zip Card Holder', 'Weekend Duffel Bag', 'Chain Shoulder Bag',
    ]),
    'footwear': ('Footwear', 'footwear-collection', [
        'Classic White Sneakers', 'Everyday Slip-ons', 'Casual Loafers', 'Running Shoes',
        'Strap Sandals', 'Block Heel Sandals', 'Canvas Sneakers', 'Formal Lace-ups',
        'Ankle Boots', 'Slides', 'Ballet Flats', 'Sports Trainers',
        'Chelsea Boots', 'Daily Wear Flats', 'Party Heels',
    ]),
    'watches': ('Watches', 'watches-collection', [
        'Classic Analog Watch', 'Minimal Dial Watch', 'Chronograph Watch',
        'Rose Gold Watch', 'Black Mesh Watch', 'Leather Strap Watch',
        'Silver Bracelet Watch', 'Sport Digital Watch', 'Square Dial Watch',
        'Two-tone Watch', 'Everyday Casual Watch', 'Slim Dress Watch',
        'Blue Dial Watch', 'Classic Couple Watch', 'Modern Minimal Watch',
    ]),
}

PRICE = {
    'men': (899, 1499), 'women': (999, 2499), 'kids': (499, 1599),
    'accessories': (399, 1999), 'footwear': (799, 2999), 'watches': (999, 4999),
}

SIZES = {
    'men': ['XS', 'S', 'M', 'L', 'XL'],
    'women': ['XS', 'S', 'M', 'L', 'XL'],
    'kids': ['2-3Y', '4-5Y', '6-7Y', '8-9Y', '10-11Y'],
    'accessories': ['One Size'],
    'footwear': ['6', '7', '8', '9', '10'],
    'watches': ['One Size'],
}

class Command(BaseCommand):
    help = 'Create/update the 90-product MYSTYLE demo catalogue with unique product images and colour/size variants.'

    def handle(self, *args, **kwargs):
        media = Path(settings.MEDIA_ROOT)
        product_dir = media / 'products'
        variant_dir = media / 'variants'

        # Reuse the existing 15 demo rows in each department when available. This keeps
        # product IDs stable and avoids creating a second set of 90 rows on an update.
        existing_catalog = {}
        for department, (title, category_slug, names) in DEPARTMENTS.items():
            old_category = Category.objects.filter(slug=category_slug).first()
            existing_catalog[department] = list(
                Product.objects.filter(category=old_category).order_by('id')[:15]
            ) if old_category else []

        # Hide older starter/demo products, but do not delete their orders or user data.
        Product.objects.update(is_active=False)

        for department, (title, category_slug, names) in DEPARTMENTS.items():
            category, _ = Category.objects.get_or_create(
                slug=category_slug,
                defaults={'name': title, 'department': department},
            )
            category.name = title
            category.department = department
            category.save(update_fields=['name', 'department'])

            for index, name in enumerate(names, start=1):
                slug = slugify(f'{name}-{department}')
                image_name = f'{department}-catalog-{index:02d}.jpg'
                image_path = product_dir / image_name
                if not image_path.exists():
                    raise FileNotFoundError(f'Missing catalogue image: {image_path}')

                mrp_base, price_base = PRICE[department]
                mrp = mrp_base + (index - 1) * 37
                price = min(mrp - 1, price_base + (index - 1) * 29)
                price = max(int(mrp * 0.62), price)
                if price >= mrp:
                    price = int(mrp * 0.72)

                if index <= len(existing_catalog[department]):
                    product = existing_catalog[department][index - 1]
                    # Slugs are globally unique. Keep a safe deterministic suffix if an older
                    # inactive starter product already uses the preferred slug.
                    if Product.objects.exclude(pk=product.pk).filter(slug=slug).exists():
                        slug = f'{slug}-{product.pk}'
                else:
                    product = Product.objects.filter(slug=slug).first()
                    if product is None:
                        product = Product.objects.create(
                            slug=slug, category=category, name=name, brand='MYSTYLE',
                            description=f'{name} from the MYSTYLE {title.lower()} collection.',
                            material='Premium blend', fit='Regular fit', mrp=mrp, price=price,
                            image=f'products/{image_name}', is_active=False,
                        )
                product.slug = slug
                product.category = category
                product.name = name
                product.brand = 'MYSTYLE'
                product.description = (
                    f'{name} from the MYSTYLE {title.lower()} collection. '
                    'A curated demo catalogue item with colour and size options, '
                    'clear pricing and stock details.'
                )
                product.material = 'Premium blend'
                product.fit = 'Regular fit'
                product.mrp = mrp
                product.price = price
                product.is_active = True
                product.image.name = f'products/{image_name}'
                product.save()

                sizes = SIZES[department]
                active_colour_names = [c[0] for c in COLOURS]
                # Remove unused old colour/size combinations for this demo catalogue.
                product.variants.exclude(colour__in=active_colour_names).delete()
                product.variants.exclude(size__in=sizes).delete()

                # Refresh the product gallery so it matches the colour options shown on screen.
                product.gallery.all().delete()
                for colour_index, (colour, hex_value, colour_slug) in enumerate(COLOURS, start=1):
                    variant_image = f'variants/{department}-catalog-{index:02d}-{colour_slug}.jpg'
                    variant_image_path = variant_dir / f'{department}-catalog-{index:02d}-{colour_slug}.jpg'
                    if not variant_image_path.exists():
                        raise FileNotFoundError(f'Missing colour variant image: {variant_image_path}')
                    for size in sizes:
                        sku = f'MYS{product.pk:05d}-{colour_index}-{slugify(size).upper()}'
                        variant, created = ProductVariant.objects.get_or_create(
                            product=product,
                            colour=colour,
                            size=size,
                            defaults={'colour_hex': hex_value, 'sku': sku, 'stock': 8, 'image': variant_image},
                        )
                        variant.colour_hex = hex_value
                        variant.sku = sku
                        variant.image.name = variant_image
                        # Preserve the current stock value when this command is re-run.
                        if created:
                            variant.stock = 8
                        variant.save()
                    ProductImage.objects.create(
                        product=product,
                        image=variant_image,
                        alt_text=f'{colour} colour view of {name}',
                    )

        Coupon.objects.update_or_create(
            code='STYLE10',
            defaults={'discount_percent': 10, 'minimum_order': 999, 'active': True},
        )
        self.stdout.write(self.style.SUCCESS(
            'MYSTYLE catalogue updated: 90 products (15 each in Men, Women, Kids, Bags, Footwear and Watches), '
            '5 colours and size-specific stock variants. Demo coupon: STYLE10.'
        ))
