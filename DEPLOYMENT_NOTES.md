# MYSTYLE local update notes

This update package is a source/media overlay. It intentionally omits `db.sqlite3` and `venv` so the existing customer/admin database and local virtual environment can be preserved when overwriting the project files.

Run `python manage.py migrate`, then `python manage.py seed_demo`, then `python manage.py check`. The storefront is local demo software. Cash on Delivery is enabled; Razorpay is not connected.
