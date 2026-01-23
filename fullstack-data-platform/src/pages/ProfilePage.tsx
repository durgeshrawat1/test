import React from 'react';
import { Container, Paper, Typography, Box, Avatar, Chip, Divider, Stack, CircularProgress } from '@mui/material';
import { useAuth } from '../context/AuthContext';

export const ProfilePage: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  if (!user) return null;

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, mt: 4, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Avatar sx={{ width: 80, height: 80, bgcolor: 'primary.main', fontSize: '2rem', mr: 3 }}>
            {user.name.charAt(0)}
          </Avatar>
          <Box>
            <Typography variant="h4">{user.name}</Typography>
            <Typography variant="body1" color="text.secondary">{user.email}</Typography>
          </Box>
        </Box>
        <Divider sx={{ my: 3 }} />
        <Typography variant="h6" gutterBottom>Access Groups</Typography>
        <Stack direction="row" spacing={1}>
          {user.groups.length > 0 ? (
            user.groups.map((group: string) => (
              <Chip key={group} label={group} color="primary" variant="outlined" />
            ))
          ) : (
            <Typography variant="body2" color="text.disabled">No groups assigned</Typography>
          )}
        </Stack>
      </Paper>
    </Container>
  );
};
