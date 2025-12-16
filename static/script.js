// Shop Details JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Sidebar Toggle Logic
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const closeSidebar = document.getElementById('closeSidebar');
    const overlay = document.getElementById('overlay');

    function toggleSidebar() {
        if (sidebar && overlay) {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        }
    }

    if (menuToggle) {
        menuToggle.addEventListener('click', toggleSidebar);
    }

    if (closeSidebar) {
        closeSidebar.addEventListener('click', toggleSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', toggleSidebar);
    }

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });

    // Search input focus effect
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('focus', function () {
            this.parentElement.classList.add('focused');
        });

        searchInput.addEventListener('blur', function () {
            this.parentElement.classList.remove('focused');
        });
    }

    // Confirm delete
    const deleteButtons = document.querySelectorAll('.btn-danger');
    deleteButtons.forEach(btn => {
        const form = btn.closest('form');
        if (form && form.classList.contains('delete-form')) {
            form.addEventListener('submit', function (e) {
                if (!confirm('আপনি কি নিশ্চিতভাবে এই দোকানটি মুছে ফেলতে চান?')) {
                    e.preventDefault();
                }
            });
        }
    });

    // Add smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Mobile phone link - add tel: prefix
    document.querySelectorAll('.mobile-link').forEach(link => {
        if (!link.href.startsWith('tel:')) {
            const phone = link.textContent.trim().replace(/[^\d]/g, '');
            if (phone) {
                link.href = 'tel:' + phone;
            }
        }
    });


    // Toggle New Category Input in Shop Form
    const categorySelect = document.getElementById('category_id');
    const newCategoryInput = document.getElementById('new_category_name');

    if (categorySelect && newCategoryInput) {
        // Run on change
        categorySelect.addEventListener('change', function () {
            if (this.value === 'new') {
                newCategoryInput.style.display = 'block';
                newCategoryInput.required = true;
                newCategoryInput.focus();
            } else {
                newCategoryInput.style.display = 'none';
                newCategoryInput.required = false;
            }
        });

        // Run on load (in case of validation error return)
        if (categorySelect.value === 'new') {
            newCategoryInput.style.display = 'block';
            newCategoryInput.required = true;
        }
    }
});

// Live search (optional - requires API endpoint)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize live search if needed
function initLiveSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    const resultsContainer = document.createElement('div');
    resultsContainer.className = 'live-search-results';
    searchInput.parentElement.appendChild(resultsContainer);

    const performSearch = debounce(async (query) => {
        if (query.length < 2) {
            resultsContainer.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const shops = await response.json();

            if (shops.length === 0) {
                resultsContainer.innerHTML = '<div class="no-result">কোনো ফলাফল পাওয়া যায়নি</div>';
                return;
            }

            resultsContainer.innerHTML = shops.slice(0, 5).map(shop => `
                <a href="/shop/${shop.id}" class="search-result-item">
                    <strong>${shop.name}</strong>
                    <span>${shop.mobile || ''}</span>
                </a>
            `).join('');
        } catch (error) {
            console.error('Search error:', error);
        }
    }, 300);

    searchInput.addEventListener('input', (e) => performSearch(e.target.value));
}
