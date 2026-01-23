// src/pages/Home.tsx
import React from 'react';
import { Typography, Paper, Button, Box, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 8, textAlign: 'center' }}>
        <Typography variant="h2" gutterBottom>
          Bank Data Hub
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Centralized management for bank datasets, transaction feeds, and schema governance.
        </Typography>

        <Paper sx={{ p: 4, mt: 4 }}>
          <Typography paragraph>
            Use the sidebar to select a dataset or feed. Import transaction CSVs, review schema versions, and export data for reporting.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
            <Button variant="contained" size="large" onClick={() => navigate('/data/import')}>Import CSV</Button>
            <Button variant="outlined" size="large" onClick={() => navigate('/admin')}>Admin Console</Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};
