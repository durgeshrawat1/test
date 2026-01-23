import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Box, CircularProgress } from '@mui/material';

interface ProtectedRouteProps {
  allowedGroups?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedGroups }) => {
  const { user, loading } = useAuth();

  // 1. Show a loader while the backend checks the ALB headers
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // 2. If no user is found in the ALB headers, redirect to login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // 3. If specific groups are required (e.g., Marketing), check the user's groups
  if (allowedGroups && allowedGroups.length > 0) {
    const hasAccess = user.groups.some((group: string) => 
      allowedGroups.includes(group) || group.toLowerCase() === 'admin'
    );

    if (!hasAccess) {
      return <Navigate to="/" replace />;
    }
  }

  return <Outlet />;
};
