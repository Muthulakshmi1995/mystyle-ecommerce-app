# MYSTYLE — Django Fashion E-Commerce

## What this update contains
- MYSTYLE storefront in ivory, black and burgundy, with four homepage sections: Men, Women, Kids and Accessories.
- Top navigation: Home, Men, Women, Kids, Accessories and About Us. Bags, Footwear and Watches appear inside the Accessories menu.
- Four homepage collection sections, each previewing five products (20 products shown on the homepage).
- 90 active demo products in total: 15 Men, 15 Women, 15 Kids, 15 Bags, 15 Footwear and 15 Watches. Bags, Footwear and Watches are shown under one Accessories menu.
- A five-second auto-rotating hero slider; manual arrows continue to work. Only the arrow artwork embedded in the supplied campaign banners is visible; transparent click areas handle manual navigation to avoid duplicate controls.
- Product detail flow: click the single “Add to Cart” button, then choose one of five colours, choose a size, and add the selected variant to the cart.
- Five colour variants per product, size-specific stock for clothing and footwear, and separate colour images that recolour the product object while preserving the studio background.
- Customer registration/login, profile, saved shipping addresses, My Orders, wishlist, cart, order detail, reviews and Cash on Delivery checkout.
- Staff-only dashboard and Django Admin portal, with a visible Staff Logout action in the storefront header.
- About Us page with an image and expanded brand introduction.

## Important about product images
This demo package includes distinct product image files for all 90 catalogue items. Men's products use generated flat-lay product photography; the first Kids styles include matching boy/girl model photos. The remaining Women, Kids, Bags, Footwear and Watches products use distinct styled catalogue illustrations created for this demo. These are demonstration assets, not supplier photographs of real inventory. Replace them with licensed supplier photography before using the site for real sales.

## Run locally (Windows / VS Code)
The update archive deliberately does not include `db.sqlite3` or `venv`. Extract the update files into the existing `MYSTYLE_Complete_Update` project folder, choose **Replace files** when Windows asks, and keep your existing `db.sqlite3` and `venv` folders. This keeps the superuser you already created.

With the existing virtual environment activated, run:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py check
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## Customer and admin login
- The existing superuser is a staff/admin account. Use it for `/django-admin/` and `/dashboard/` only.
- In the storefront header, use **Logout** to end the staff session.
- Then choose **Register** or open `/register/` and create a separate customer account. Use that customer account for Profile, Wishlist, Cart, Checkout and My Orders.
- A staff session is intentionally not allowed to place customer orders or use the customer wishlist/cart.

## Demo catalogue and coupon
Run `python manage.py seed_demo` after replacing files. It updates the same 90 demo products and their image mappings; it preserves stock for existing matching variants. Old starter products are made inactive rather than being deleted. The demo coupon is `STYLE10` (10% off; minimum order ₹999).

## Payments and production readiness
- Cash on Delivery is the available checkout method. COD orders show “Pay on delivery”; their payment status remains pending until collection.
- Razorpay is **not connected** in this update. Do not choose or advertise online payments until test key configuration, order creation, signature verification, payment-failure handling and stock reconciliation have been implemented and tested.
- Password reset uses Django's console email backend locally; configure SMTP for real emails.
- Contact form currently displays an acknowledgement; it is not saved to a database.
- Review submission is available to signed-in customer accounts.

## Backup and deployment
Back up `db.sqlite3` and the complete `media/` directory together before making further changes. For deployment, set a strong `SECRET_KEY`, `DEBUG=False`, correct `ALLOWED_HOSTS`, PostgreSQL `DATABASE_URL`, SMTP and persistent media storage. Never commit `.env`, database credentials or Razorpay secrets.
