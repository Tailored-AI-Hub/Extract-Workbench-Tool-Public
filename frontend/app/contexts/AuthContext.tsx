'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { apiService, UserProfile } from '../services/api';

// SECURITY NOTE: Storing JWT tokens in sessionStorage is still vulnerable to XSS attacks.
// The ideal solution is to use httpOnly cookies set by the backend, which prevents
// JavaScript access entirely. This requires backend changes to set cookies with httpOnly flag.
// sessionStorage is used here as an improvement over localStorage (clears on tab close),
// but httpOnly cookies should be implemented for production security.
const TOKEN_STORAGE_KEY = 'auth_token';

// Helper functions for token storage
const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
};

const setStoredToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
};

const removeStoredToken = (): void => {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
};

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  retryAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUserProfile = async (authToken: string) => {
    try {
      const userProfile = await apiService.getUserProfile(authToken);
      setUser(userProfile);
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      // Only clear token if it's a 401 Unauthorized error (invalid/expired token)
      // Don't clear token for network errors or other temporary issues
      if (error instanceof Error && (
        error.message.includes('401') || 
        error.message.includes('Unauthorized') ||
        error.message.includes('Not authenticated')
      )) {
        setToken(null);
        removeStoredToken();
      }
      // For other errors, keep the token but don't set user
      setUser(null);
      // Re-throw the error so the calling code knows it failed
      throw error;
    }
  };

  useEffect(() => {
    // Check for stored token on mount
    const storedToken = getStoredToken();
    if (storedToken) {
      setToken(storedToken);
      // Fetch user profile and only set loading to false after completion
      fetchUserProfile(storedToken).finally(() => {
        setLoading(false);
      });
    } else {
      // No token found, set loading to false immediately
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const data = await apiService.login(email, password);
      setToken(data.access_token);
      setStoredToken(data.access_token);
      
      // Fetch user profile after successful login
      await fetchUserProfile(data.access_token);
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const signup = async (email: string, password: string, name: string) => {
    try {
      // Backend now returns a message and requires admin approval before login
      // We do not log the user in automatically after signup.
      await apiService.signup(email, password, name);
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    removeStoredToken();
    // Navigate to the home page (which will show the login form due to ProtectedRoute)
    router.push('/');
  };

  const retryAuth = async () => {
    const storedToken = getStoredToken();
    if (storedToken) {
      setToken(storedToken);
      await fetchUserProfile(storedToken);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, signup, logout, loading, retryAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
