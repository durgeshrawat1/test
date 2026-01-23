import React, { createContext, useContext, useState, useEffect } from 'react';
import { CONFIG } from '../config';

interface User {
  id: string;
  email: string;
  name: string;
  groups: string[];
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const url = `${CONFIG.API_BASE_URL}/auth/me`;
        // include any ALB token the environment or a proxy might expose to the front-end
        const token = (window as any).__ALB_JWT__ || localStorage.getItem('ALB_JWT') || undefined;
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        // eslint-disable-next-line no-console
        console.debug('Auth check URL:', url, 'using token?', !!token);
        const res = await fetch(url, { headers, credentials: 'include' });
        // eslint-disable-next-line no-console
        console.debug('Auth fetch status:', res.status);
        if (res.ok) {
          const data = await res.json();
          // eslint-disable-next-line no-console
          console.debug('Auth fetch response:', data);
          setUser(data.user || null);
        } else {
          // eslint-disable-next-line no-console
          console.warn('Auth fetch non-ok response', await res.text());
          setUser(null);
        }
      } catch (e) {
        console.error("Auth check failed", e);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const logout = () => {
    const returnTo = window.location.origin + "/login";
    window.location.href = `${window.location.origin}/logout?continue=${encodeURIComponent(returnTo)}`;
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
