import React, { useEffect } from 'react';
import { Container, Box, Typography, Button, Paper } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const LoginPage: React.FC = () => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/');
    }
  }, [user, loading, navigate]);

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 10, textAlign: 'center' }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom>Bank UDD Platform</Typography>
          <Typography variant="body1" sx={{ mb: 3 }}>
            Sign in with your corporate SSO to manage datasets and feeds securely.
          </Typography>
          <Button variant="contained" fullWidth size="large" onClick={() => window.location.href = '/'}>
            Sign In with SSO
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};

