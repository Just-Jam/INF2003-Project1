// auth.js - SIMPLIFIED VERSION
const API_BASE = '/api';

async function apiCall(endpoint, method = 'GET', body = null) {
  const url = `${API_BASE}${endpoint}`;
  const csrftoken = document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];

  const config = {
    method,
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json',
      'Authorization': localStorage.getItem('token') ? `Token ${localStorage.getItem('token')}` : ''
    }
  };

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  const resp = await fetch(url, config);
  const data = await resp.json();

  if (!resp.ok) throw data;
  return data;
}

// Auth functions - now much simpler
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
    await apiCall('/auth/logout/', 'POST');
    this.clearUserData();
  },

  async getProfile() {
    return await apiCall('/users/profile/', 'GET');
  },

  async updateProfile(profileData) {
    const response = await apiCall('/users/profile/', 'PATCH', profileData);
    this.storeUserData(response);
    return response;
  },

  async changePassword(passwordData) {
    const response = await apiCall('/users/change_password/', 'POST', passwordData);
    if (response.token) {
      localStorage.setItem('token', response.token);
    }
    return response;
  },

  async deactivateAccount(password) {
    await apiCall('/users/deactivate/', 'POST', { password });
    this.clearUserData();
  },

  storeUserData(userData) {
    localStorage.setItem('token', userData.token);
    localStorage.setItem('user_id', userData.user_id);
    localStorage.setItem('email', userData.email);
    localStorage.setItem('first_name', userData.first_name);
    localStorage.setItem('last_name', userData.last_name);
  },

  clearUserData() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    localStorage.removeItem('first_name');
    localStorage.removeItem('last_name');
  },

  isAuthenticated() {
    return !!localStorage.getItem('token');
  },

  getCurrentUser() {
    if (!this.isAuthenticated()) return null;
    return {
      user_id: localStorage.getItem('user_id'),
      email: localStorage.getItem('email'),
      first_name: localStorage.getItem('first_name'),
      last_name: localStorage.getItem('last_name')
    };
  }
};

// Make available globally
window.auth = auth;

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
  if (auth.isAuthenticated()) {
    // Verify token is still valid
    auth.getProfile().catch(() => auth.clearUserData());
  }
});