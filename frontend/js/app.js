// Load API_URL from window.ENV (defined in env.js) or fallback to localhost
const API_URL = (window.ENV && window.ENV.API_URL) ? window.ENV.API_URL : 'http://127.0.0.1:8000/api';

// Core State
let state = {
    token: localStorage.getItem('token'),
    user: null,
    cart: { items: [], total: 0 }
};

// Formatting utilities
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES' }).format(amount);
};

// API calls mapping
const api = {
    async request(endpoint, options = {}) {
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (state.token) {
            headers['Authorization'] = `Token ${state.token}`;
        }

        try {
            const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    logout();
                }
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || err.error || 'API Request failed');
            }
            // Some endpoints might return no content
            const text = await response.text();
            return text ? JSON.parse(text) : {};
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    getProducts: async (query = '', page = 1) => {
        const paramStr = query ? `&search=${encodeURIComponent(query)}` : '';
        return api.request(`/products/?page=${page}${paramStr}`);
    },

    getProduct(id) {
        return this.request(`/products/${id}/`);
    },

    getCart() {
        return this.request('/cart/');
    },

    updateCart(productId, quantity) {
        return this.request('/cart/items/', {
            method: 'POST',
            body: JSON.stringify({ product_id: productId, quantity })
        });
    },

    checkout: async () => api.request('/checkout/', { method: 'POST' }),
    paystackInit: async (orderId) => api.request('/payments/paystack/initialize/', { method: 'POST', body: JSON.stringify({ order_id: orderId }) }),
    paystackVerify: async (reference) => api.request('/payments/paystack/verify/', { method: 'POST', body: JSON.stringify({ reference }) }),
    getOrders: async () => api.request('/orders/'),

    login(username, password) {
        return this.request('/users/token/', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    register(data) {
        return this.request('/users/register/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    getUser() {
        return this.request('/users/me/');
    }
};

// UI and App logic
async function initApp() {
    updateAuthUI();
    if (state.token) {
        try {
            state.user = await api.getUser();
            updateAuthUI();
            updateCartCount();
        } catch (e) {
            logout();
        }
    }
}

function updateAuthUI() {
    const authLinksArea = document.getElementById('auth-links');
    const dashboardLink = document.getElementById('nav-dashboard');

    // Quick safeguard if we aren't on a page with top nav
    if (!authLinksArea) return;

    if (state.token) {
        // User is logged in
        dashboardLink.style.display = 'block';
        const name = state.user ? state.user.username : 'Account';
        authLinksArea.innerHTML = `
            <span class="text-ms-gray160 mr-4 text-sm font-medium">Hello, ${name}</span>
            <button onclick="logout()" class="text-[#0078D4] hover:underline text-sm font-semibold transition-colors">Sign out</button>
        `;
    } else {
        // User is logged out
        dashboardLink.style.display = 'none';
        authLinksArea.innerHTML = `
            <a href="login.html" class="text-ms-gray160 hover:text-ms-blue hover:underline font-medium px-2 py-1 transition-colors">Sign in</a>
            <a href="register.html" class="ms-btn-primary px-4 py-1.5 min-w-[80px] text-center font-semibold ml-2">Register</a>
        `;
    }
}

async function updateCartCount() {
    const cartCountEl = document.getElementById('cart-count');
    if (!cartCountEl) return;

    if (state.token) {
        try {
            const cartData = await api.getCart();
            const totalItems = (cartData.items || []).reduce((acc, curr) => acc + curr.quantity, 0);
            if (totalItems > 0) {
                cartCountEl.textContent = totalItems > 99 ? '99+' : totalItems;
                cartCountEl.classList.remove('hidden');
            } else {
                cartCountEl.classList.add('hidden');
            }
        } catch (e) {
            console.error("Failed to load cart count", e);
        }
    } else {
        cartCountEl.classList.add('hidden');
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('token');
    window.location.href = 'index.html';
}

// Product Rendering for Index Page
let searchTimeout;
const activeFilters = { search: '', category: '', min_price: '', max_price: '', page: 1 };

async function fetchProducts() {
    try {
        const container = document.getElementById('products-container');
        const loader = document.getElementById('loader');
        const emptyState = document.getElementById('empty-state');
        const pageTitle = document.getElementById('page-title');
        const pageSubtitle = document.getElementById('page-subtitle');
        const resultsCount = document.getElementById('results-count');

        if (!container) return; // Not on index page

        loader.classList.remove('hidden');
        container.classList.add('hidden');
        emptyState.classList.add('hidden');

        // Build query string
        const params = new URLSearchParams();
        if (activeFilters.page) params.append('page', activeFilters.page);
        if (activeFilters.search) params.append('search', activeFilters.search);
        if (activeFilters.category) params.append('category', activeFilters.category);
        if (activeFilters.min_price) params.append('min_price', activeFilters.min_price);
        if (activeFilters.max_price) params.append('max_price', activeFilters.max_price);

        const qs = params.toString() ? `?${params.toString()}` : '';
        const responseData = await api.request(`/products/${qs}`);

        // Handle pagination response structure (drf PageNumberPagination)
        const products = responseData.results || responseData;
        const totalCount = responseData.count || (products ? products.length : 0);

        loader.classList.add('hidden');

        // Update Titles
        if (activeFilters.category) {
            pageTitle.textContent = activeFilters.category;
            pageSubtitle.classList.remove('hidden');
            pageSubtitle.textContent = activeFilters.search ? `Results for "${activeFilters.search}"` : "Browse category items";
        } else if (activeFilters.search) {
            pageTitle.textContent = "Search Results";
            pageSubtitle.classList.remove('hidden');
            pageSubtitle.textContent = `Showing all matches for "${activeFilters.search}"`;
        } else {
            pageTitle.textContent = "All Products";
            pageSubtitle.classList.add('hidden');
        }

        resultsCount.textContent = totalCount;

        // Toggle clear filters button visibility
        const clearBtn = document.getElementById('clear-filters');
        if (activeFilters.search || activeFilters.category || activeFilters.min_price || activeFilters.max_price) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }

        if (!products || products.length === 0) {
            emptyState.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');

        // Flat grid rendering
        container.innerHTML = products.map(p => `
            <div class="ms-card flex flex-col h-full bg-white relative cursor-pointer group hover:-translate-y-1 transition-transform duration-200" onclick="window.location.href='product.html?id=${p.id}'">
                <div class="relative h-48 bg-ms-gray10 flex items-center justify-center p-4 border-b border-ms-gray30">
                    ${p.image ?
                `<img src="${p.image}" alt="${p.name}" class="object-contain h-full w-full opacity-90 group-hover:opacity-100 transition-opacity" />` :
                `<i class="fas fa-box-open text-4xl text-ms-gray40"></i>`
            }
                    ${p.stock === 0 ? `<div class="absolute top-2 left-2 bg-[#FDE7E9] text-[#A4262C] text-[11px] font-semibold px-2 py-0.5 border border-[#A4262C] shadow-sm">Out of Stock</div>` : ''}
                </div>
                <div class="p-4 flex-grow flex flex-col">
                    <span class="text-[10px] font-bold text-ms-blue uppercase tracking-widest mb-1">${p.category || 'General'}</span>
                    <h3 class="text-[15px] font-semibold text-ms-gray190 mb-1 line-clamp-2 leading-tight group-hover:text-ms-blue transition-colors">${p.name}</h3>
                    <p class="text-ms-gray130 text-[13px] mb-3 line-clamp-2 flex-grow">${p.description}</p>
                    <div class="mt-auto pt-2 flex items-center justify-between">
                        <span class="text-[18px] font-bold text-ms-gray190">${formatCurrency(p.price)}</span>
                    </div>
                </div>
            </div>
        `).join('');

        // Add Pagination Controls
        if (responseData.count !== undefined && Math.ceil(responseData.count / 10) > 1) { // Check if we have multiple pages
            const totalPages = Math.ceil(responseData.count / 10);
            let pageBtns = '';
            for (let i = 1; i <= totalPages; i++) {
                pageBtns += `<button onclick="goToPage(${i})" class="px-3 py-1 border ${activeFilters.page === i ? 'bg-ms-blue text-white border-ms-blue' : 'bg-white text-ms-gray160 border-ms-gray40 hover:bg-ms-gray10'} rounded-sm text-sm font-semibold transition-colors">${i}</button>`;
            }
            container.innerHTML += `
               <div class="mt-8 flex justify-center gap-2 items-center">
                    ${responseData.previous ? `<button onclick="goToPage(${activeFilters.page - 1})" class="px-3 py-1 border bg-white text-ms-gray160 border-ms-gray40 hover:bg-ms-gray10 rounded-sm text-sm font-semibold transition-colors"><i class="fas fa-chevron-left"></i> Prev</button>` : `<button disabled class="px-3 py-1 border bg-ms-gray10 text-ms-gray40 border-ms-gray30 rounded-sm text-sm font-semibold cursor-not-allowed"><i class="fas fa-chevron-left"></i> Prev</button>`}
                    ${pageBtns}
                    ${responseData.next ? `<button onclick="goToPage(${activeFilters.page + 1})" class="px-3 py-1 border bg-white text-ms-gray160 border-ms-gray40 hover:bg-ms-gray10 rounded-sm text-sm font-semibold transition-colors">Next <i class="fas fa-chevron-right"></i></button>` : `<button disabled class="px-3 py-1 border bg-ms-gray10 text-ms-gray40 border-ms-gray30 rounded-sm text-sm font-semibold cursor-not-allowed">Next <i class="fas fa-chevron-right"></i></button>`}
               </div>
            `;
        }

    } catch (e) {
        console.error("Fetch products failed", e);
        document.getElementById('loader').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
        document.getElementById('empty-state').innerHTML = `<p class="text-[#A4262C] font-semibold">Error loading products. Is the backend running?</p>`;
    }
}

// Side-effects: load categories dynamically based on unique categories in the DB
async function setupFilters() {
    const catContainer = document.getElementById('category-filters');
    if (!catContainer) return;

    try {
        const res = await api.getProducts();
        const products = res.results || res; // handle pagination
        const categories = [...new Set(products.map(p => p.category || 'General'))].sort();

        window.applyCategory = (cat) => {
            activeFilters.category = cat;
            activeFilters.page = 1; // reset page on new filter
            document.querySelectorAll('.cat-link').forEach(el => {
                if (el.dataset.cat === cat) el.classList.add('font-bold', 'text-ms-blue', 'border-l-2', 'border-ms-blue', 'pl-2', '-ml-[2px]');
                else el.classList.remove('font-bold', 'text-ms-blue', 'border-l-2', 'border-ms-blue', 'pl-2', '-ml-[2px]');
            });
            fetchProducts();
        };

        catContainer.innerHTML = `
            <button class="cat-link block w-full text-left py-1.5 text-ms-gray160 hover:text-ms-blue transition-colors font-bold text-ms-blue border-l-2 border-ms-blue pl-2 -ml-[2px]" data-cat="" onclick="applyCategory('')">All Categories</button>
            ${categories.map(c => `
                <button class="cat-link block w-full text-left py-1.5 text-ms-gray160 hover:text-ms-blue transition-colors" data-cat="${c}" onclick="applyCategory('${c}')">${c}</button>
            `).join('')}
        `;
    } catch (e) {
        catContainer.innerHTML = `<span class="text-ms-gray40 text-xs">Failed to load categories</span>`;
        console.error(e);
    }
}

// Setup static bindings when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const mainSearch = document.getElementById('search-input');
    const mobileSearch = document.getElementById('mobile-search-input');
    const minPrice = document.getElementById('min-price');
    const maxPrice = document.getElementById('max-price');
    const applyPriceBtn = document.getElementById('apply-price-btn');
    const clearFiltersBtn = document.getElementById('clear-filters');

    const handleSearch = (e) => {
        const query = e.target.value;
        activeFilters.search = query;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => fetchProducts(), 300);

        if (e.target.id === 'search-input' && mobileSearch) mobileSearch.value = query;
        if (e.target.id === 'mobile-search-input' && mainSearch) mainSearch.value = query;
    };

    if (mainSearch) mainSearch.addEventListener('input', handleSearch);
    if (mobileSearch) mobileSearch.addEventListener('input', handleSearch);

    if (applyPriceBtn) {
        applyPriceBtn.addEventListener('click', () => {
            activeFilters.min_price = minPrice.value;
            activeFilters.max_price = maxPrice.value;
            fetchProducts();
        });
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            activeFilters.search = '';
            activeFilters.category = '';
            activeFilters.min_price = '';
            activeFilters.max_price = '';
            activeFilters.page = 1;
            if (mainSearch) mainSearch.value = '';
            if (mobileSearch) mobileSearch.value = '';
            if (minPrice) minPrice.value = '';
            if (maxPrice) maxPrice.value = '';
            if (window.applyCategory) window.applyCategory('');
        });
    }

    window.goToPage = (page) => {
        activeFilters.page = page;
        fetchProducts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    setupFilters();
});

// Global initialization
window.addEventListener('DOMContentLoaded', initApp);
