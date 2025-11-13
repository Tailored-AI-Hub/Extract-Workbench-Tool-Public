import { enhancedFetch, createApiError, RequestConfig } from '../lib/api-utils';

// Use environment variable if available, otherwise fallback to localhost
// Note: Backend uses root_path="/api", so all endpoints are prefixed with /api
export const API_BASE_URL: string = 
  process.env.NEXT_PUBLIC_API_URL || 'https://pdf-extraction.thetailoredai.co/api';
  // process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';  

// Note: PDF-related types have been moved to pdfApi.ts
// This file now only contains auth and admin-related types

export interface UserProfile {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_approved?: boolean;
  role?: string;
}

class ApiService {
  private getAuthHeaders(token: string) {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  /**
   * Enhanced fetch wrapper with retry logic and error handling
   */
  private async fetchWithRetry(url: string, config: RequestConfig = {}): Promise<Response> {
    const response = await enhancedFetch(url, {
      ...config,
      timeout: 30000,
      retry: {
        maxRetries: 2,
        retryDelay: 1000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });

    if (!response.ok) {
      throw await createApiError(response);
    }

    return response;
  }
  // Admin API (JWT-based)
  async adminListUsers(token: string): Promise<Array<{ id: number; email: string; name: string; is_active: boolean; is_approved: boolean; role: string; last_login: string | null }>> {
    const response = await this.fetchWithRetry(`${API_BASE_URL}/auth/admin/users`, {
      headers: this.getAuthHeaders(token),
    });
    return response.json();
  }

  async adminApproveUser(userId: number, token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/admin/approve/${userId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({} as any));
      throw new Error(err.detail || 'Failed to approve user');
    }
    return response.json();
  }

  async adminActivateUser(userId: number, token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/admin/activate/${userId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({} as any));
      throw new Error(err.detail || 'Failed to activate user');
    }
    return response.json();
  }

  async adminDeactivateUser(userId: number, token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/admin/deactivate/${userId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({} as any));
      throw new Error(err.detail || 'Failed to deactivate user');
    }
    return response.json();
  }

  async adminResetPassword(userId: number, newPassword: string, token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/admin/reset-password/${userId}?new_password=${encodeURIComponent(newPassword)}`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({} as any));
      throw new Error(err.detail || 'Failed to reset password');
    }
    return response.json();
  }

  // Note: PDF-related methods (Projects, Documents, Extraction Jobs, etc.) have been moved to pdfApi.ts

  // Auth API
  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  async signup(email: string, password: string, name: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, name }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }

    return response.json();
  }

  // User Profile API
  async getUserProfile(token: string): Promise<UserProfile> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.getAuthHeaders(token),
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = 'Failed to fetch user profile';
      
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // If response is not JSON, use the text or status
        errorMessage = errorText || `HTTP ${response.status}`;
      }
      
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async changePassword(currentPassword: string, newPassword: string, token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to change password');
    }

    return response.json();
  }

  // Note: PDF-related methods (retryExtractionJob, getRatingBreakdown, getAnnotationsList) have been moved to pdfApi.ts
}

export const apiService = new ApiService();
