
// API Base URL
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Utility Functions
const API = {
    // Generic fetch wrapper
    async fetch(endpoint, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...defaultOptions,
                ...options,
                headers: {
                    ...defaultOptions.headers,
                    ...options.headers,
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Auth methods
    async login(email, password) {
        return await this.fetch('/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },
    
    async register(userData) {
        return await this.fetch('/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    },
    
    async logout() {
        return await this.fetch('/logout', {
            method: 'POST'
        });
    },
    
    // Services methods
    async getServices(search = '', category = '') {
        let url = '/services?';
        if (search) url += `search=${search}&`;
        if (category) url += `category=${category}`;
        return await this.fetch(url);
    },
    
    async getService(id) {
        return await this.fetch(`/services/${id}`);
    },
    
    async createService(serviceData) {
        return await this.fetch('/services', {
            method: 'POST',
            body: JSON.stringify(serviceData)
        });
    },

    async getMyServices() {
        return await this.fetch('/my-services');
    },
    
    // Subscriptions methods
    async getSubscriptions() {
        return await this.fetch('/subscriptions');
    },
    
    async createSubscription(subscriptionData) {
        return await this.fetch('/subscriptions', {
            method: 'POST',
            body: JSON.stringify(subscriptionData)
        });
    },
    
    async updateSubscription(id, data) {
        return await this.fetch(`/subscriptions/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    async cancelSubscription(id) {
        return await this.fetch(`/subscriptions/${id}`, {
            method: 'DELETE'
        });
    },
    
    // Service Requests methods
    async getServiceRequests() {
        return await this.fetch('/service-requests');
    },
    
    async updateServiceRequest(id, status) {
        return await this.fetch(`/service-requests/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    },
    
    // Dashboard stats
    async getDashboardStats() {
        return await this.fetch('/dashboard/stats');
    },

    // Customer service requests
    async getCustomerServiceRequests() {
        return await this.fetch('/customer/service-requests');
    },

    async createServiceRequest(requestData) {
        return await this.fetch('/customer/service-requests', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
    },

    // Notifications
    async getNotifications() {
        return await this.fetch('/notifications');
    },

    async markNotificationRead(notificationId) {
        return await this.fetch(`/notifications/${notificationId}/read`, {
            method: 'PUT'
        });
    },

    // Provider customer requests
    async getCustomerRequests(status = 'scheduled') {
        return await this.fetch(`/provider/customer-requests?status=${status}`);
    },

    async acceptJob(jobId) {
        return await this.fetch(`/accept-job/${jobId}`, {
            method: 'POST'
        });
    },

    // Profile update
    async updateProfile(profileData) {
        return await this.fetch('/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
    },

    // Upcoming schedules
    async getUpcomingSchedules() {
        return await this.fetch('/upcoming-schedules');
    },

    // Payment history
    async getPaymentHistory() {
        return await this.fetch('/payment-history');
    },

    // Categories
    async getCategories() {
        return await this.fetch('/categories');
    }
};

// Auth helper functions
function isAuthenticated() {
    return localStorage.getItem('user') !== null;
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function requireAuth(requiredRole = null) {
    const user = getCurrentUser();
    
    if (!user) {
        window.location.href = 'login.html';
        return false;
    }
    
    if (requiredRole && user.role !== requiredRole) {
        alert('Access denied');
        window.location.href = 'index.html';
        return false;
    }
    
    return true;
}

// Date formatting
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Price formatting
function formatPrice(price) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(price);
}

// Toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#e74c3c';
            isValid = false;
        } else {
            input.style.borderColor = '#ddd';
        }
    });
    
    return isValid;
}

// Email validation
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API, isAuthenticated, getCurrentUser, requireAuth, formatDate, formatPrice, showToast };
}
