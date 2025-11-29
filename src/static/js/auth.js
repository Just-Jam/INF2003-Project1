// static/js/auth.js
const API_BASE = '/api';

// Get CSRF token from cookies
function getCSRFToken() {
  const csrftoken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return csrftoken;
}

// Get authentication token
function getAuthToken() {
  return localStorage.getItem('token');
}

// Main API call function
async function apiCall(endpoint, method = 'GET', body = null) {
  const url = `${API_BASE}${endpoint}`;
  const token = getAuthToken();

  const config = {
    method,
    headers: {
      'X-CSRFToken': getCSRFToken(),
      'Content-Type': 'application/json',
    }
  };

  // ✅ Add Authorization header if token exists
  if (token) {
    config.headers['Authorization'] = `Token ${token}`;
  }

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  const resp = await fetch(url, config);
  const data = await resp.json();

  if (!resp.ok) {
    throw data;
  }
  return data;
}

// User data management
function storeUserData(userData) {
  if (userData) {
    localStorage.setItem('token', userData.token);
    localStorage.setItem('user_id', userData.user_id);
    localStorage.setItem('email', userData.email);
    localStorage.setItem('first_name', userData.first_name);
    localStorage.setItem('last_name', userData.last_name);
  }
}

function clearUserData() {
  localStorage.removeItem('token');
  localStorage.removeItem('user_id');
  localStorage.removeItem('email');
  localStorage.removeItem('first_name');
  localStorage.removeItem('last_name');
}

function getCurrentUser() {
  if (!isAuthenticated()) return null;

  return {
    user_id: localStorage.getItem('user_id'),
    email: localStorage.getItem('email'),
    first_name: localStorage.getItem('first_name'),
    last_name: localStorage.getItem('last_name'),
    token: localStorage.getItem('token')
  };
}

function isAuthenticated() {
  return !!localStorage.getItem('token');
}

// Authentication functions
const auth = {
  async register(userData) {
    const response = await apiCall('/auth/register/', 'POST', userData);
    this.storeUserData(response);
    return response;
  },

  async login(email, password) {
    const response = await apiCall('/auth/login/', 'POST', { email, password });
    this.storeUserData(response);
    return response;
  },

  async logout() {
    try {
      // ✅ Make sure token is included in logout request
      await apiCall('/auth/logout/', 'POST');
    } catch (error) {
      console.warn('API logout failed:', error);
      // Even if API call fails, clear local data
    } finally {
      this.clearUserData();
      // Redirect to login page
      if (window.URLS && window.URLS.LOGIN) {
        window.location.href = window.URLS.LOGIN;
      } else {
        window.location.href = '/login/';
      }
    }
  },

  async getProfile() {
    const response = await apiCall('/users/profile/', 'GET');
    this.storeUserData(response);
    return response;
  },

  async updateProfile(profileData) {
    const response = await apiCall('/users/profile/', 'PATCH', profileData);
    this.storeUserData(response);
    return response;
  },

  async changePassword(passwordData) {
    const response = await apiCall('/users/change-password/', 'POST', passwordData);
    if (response.token) {
      localStorage.setItem('token', response.token);
    }
    return response;
  },

  async deactivateAccount(password) {
    await apiCall('/users/deactivate/', 'POST', { password });
    this.clearUserData();
  },

  // Test function to verify token is working
  async testAuth() {
    try {
      const response = await apiCall('/users/profile/', 'GET');
      console.log('Token is valid:', response);
      return true;
    } catch (error) {
      console.log('Token is invalid:', error);
      return false;
    }
  },

  storeUserData,
  clearUserData,
  getCurrentUser,
  isAuthenticated
};

// Initialize auth when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Set up logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function(e) {
      e.preventDefault();
      auth.logout();
    });
  }

  // Verify token on page load if authenticated
  if (auth.isAuthenticated()) {
    console.log('User is authenticated, verifying token...');
    auth.testAuth().then(isValid => {
      if (!isValid) {
        console.warn('Token validation failed, clearing auth data');
        auth.clearUserData();
      }
    });
  }

  // Update UI based on auth state
  updateAuthUI();
});

// Update UI elements based on authentication state
function updateAuthUI() {
  const user = auth.getCurrentUser();

  if (user) {
    console.log('User is authenticated:', user.email);
    // Update any UI elements that show user info
    const userWelcomeEl = document.getElementById('userWelcome');
    if (userWelcomeEl) {
      userWelcomeEl.textContent = `Welcome, ${user.first_name} ${user.last_name}`;
    }
  } else {
    console.log('User is not authenticated');
  }
}

// Make auth globally available
window.auth = auth;
window.apiCall = apiCall;

// Debug helper
window.debugAuth = function() {
  console.log('Auth Debug Info:');
  console.log('Token:', localStorage.getItem('token'));
  console.log('User ID:', localStorage.getItem('user_id'));
  console.log('Email:', localStorage.getItem('email'));
};
