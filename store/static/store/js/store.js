
document.addEventListener('DOMContentLoaded', () => {

    // HOME PAGE SLIDER
    const slider = document.querySelector('[data-slider]');

    if (slider) {
        const slides = [...slider.querySelectorAll('.hero-slide')];
        const dots = [...slider.querySelectorAll('.slider-dots button')];

        let index = 0;
        let timer = null;

        const show = n => {
            index = (n + slides.length) % slides.length;

            slides.forEach((s, i) => {
                s.classList.toggle('active', i === index);
            });

            dots.forEach((d, i) => {
                d.classList.toggle('active', i === index);
            });
        };

        const restart = () => {
            if (timer) clearInterval(timer);
            timer = setInterval(() => show(index + 1), 5000);
        };

        slider.querySelector('.prev')?.addEventListener('click', () => {
            show(index - 1);
            restart();
        });

        slider.querySelector('.next')?.addEventListener('click', () => {
            show(index + 1);
            restart();
        });

        dots.forEach((d, i) => {
            d.addEventListener('click', () => {
                show(i);
                restart();
            });
        });

        show(0);
        restart();
    }


    // PRODUCT SIZE AND ADD TO CART
    const form = document.getElementById('variant-cart-form');

    if (form) {
        const modal = document.getElementById('variant-modal');
        const open = document.getElementById('open-variant-modal');
        const close = document.getElementById('close-variant-modal');
        const sizes = [...form.querySelectorAll('.size-option')];
        const variantInput = document.getElementById('selected-variant-id');
        const add = document.getElementById('add-to-cart-button');
        const hint = document.getElementById('variant-hint');
        const stockLine = document.getElementById('stock-message');
        const qty = document.getElementById('product-quantity');

        let chosen = null;

        const updateSelection = button => {
            chosen = button ? {
                id: button.dataset.variantId,
                size: button.dataset.size,
                stock: Number(button.dataset.stock || 0)
            } : null;

            variantInput.value = chosen ? chosen.id : '';
            add.disabled = !chosen || chosen.stock < 1;

            if (!chosen) {
                hint.textContent = 'Choose a size to check stock.';
                return;
            }

            if (chosen.stock < 1) {
                hint.textContent = 'This size is currently out of stock.';
                stockLine.textContent = 'Currently unavailable in this size';
                add.disabled = true;
                return;
            }

            hint.textContent =
                `${chosen.stock} available in size ${chosen.size} · Ready to ship`;

            stockLine.textContent = chosen.stock <= 5
                ? `Only ${chosen.stock} left in size ${chosen.size}`
                : 'In stock · Ready to ship';

            qty.max = Math.min(10, chosen.stock);

            if (Number(qty.value) > chosen.stock) {
                qty.value = chosen.stock;
            }
        };

        open?.addEventListener('click', () => {
            modal.hidden = false;
            modal.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        });

        close?.addEventListener('click', () => {
            modal.hidden = true;
        });

        sizes.forEach(button => {
            button.addEventListener('click', () => {
                if (button.disabled) return;

                sizes.forEach(other => {
                    other.classList.toggle('selected', other === button);
                });

                updateSelection(button);
            });
        });

        form.addEventListener('submit', event => {
            if (!chosen || chosen.stock < 1) {
                event.preventDefault();
                modal.hidden = false;
                hint.textContent = 'Please choose an available size.';
                return;
            }

            form.action = form.dataset.cartUrl.replace('/0/', '/' + chosen.id + '/');
        });
    }


    // PRODUCT IMAGE GALLERY
    document.querySelectorAll('.gallery-thumb').forEach(button => {
        button.addEventListener('click', () => {
            const img = document.getElementById('main-product-image');
            if (img) img.src = button.dataset.image;
        });
    });


    // MYSTYLE ACCESSORIES DROPDOWN - DESKTOP AND MOBILE

    const dropdowns = [
        ...document.querySelectorAll('.nav-dropdown')
    ];

    dropdowns.forEach(dropdown => {

        const toggle = dropdown.querySelector(
            ':scope > .nav-dropdown-toggle'
        );

        if (!toggle) return;

        toggle.setAttribute('aria-haspopup', 'true');
        toggle.setAttribute('aria-expanded', 'false');

        toggle.addEventListener('click', event => {

            event.preventDefault();
            event.stopPropagation();

            const willOpen = !dropdown.classList.contains('open');

            dropdowns.forEach(item => {
                item.classList.remove('open');

                item.querySelector(':scope > .nav-dropdown-toggle')
                    ?.setAttribute('aria-expanded', 'false');
            });

            if (willOpen) {
                dropdown.classList.add('open');
                toggle.setAttribute('aria-expanded', 'true');
            }
        });
    });


    // CLOSE DROPDOWN WHEN CLICKING OUTSIDE

    document.addEventListener('click', event => {

        if (!event.target.closest('.nav-dropdown')) {

            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('open');

                dropdown.querySelector(':scope > .nav-dropdown-toggle')
                    ?.setAttribute('aria-expanded', 'false');
            });
        }
    });


    // CLOSE DROPDOWN WITH ESCAPE KEY

    document.addEventListener('keydown', event => {

        if (event.key === 'Escape') {

            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('open');

                const toggle = dropdown.querySelector(
                    ':scope > .nav-dropdown-toggle'
                );

                toggle?.setAttribute('aria-expanded', 'false');
            });
        }
    });

});
