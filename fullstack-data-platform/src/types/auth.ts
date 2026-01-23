export type UserRole = 'Admin' | 'Finance' | 'Market';

export interface UserProfile {
  name: string;
  email: string;
  groups: UserRole[];
}

export interface AuthContextType {
  user: UserProfile | null;
  login: (role: UserRole) => void;
  logout: () => void;
}
