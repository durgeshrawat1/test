import { BrowserRouter as Router, Routes, Route, Outlet, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { AdminPage } from './pages/AdminPage';
import { DataGridPage } from './pages/DataGridPage';
import { ProfilePage } from './pages/ProfilePage';
import { Box, Typography, CircularProgress, Button } from '@mui/material';

const AdminRoute = () => {
  const { user, loading } = useAuth();
  
  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
      <CircularProgress />
    </Box>
  );
  
  // Robust check for Admin group
  const isAdmin = user?.groups?.some(g => g.toLowerCase() === 'admin');
  
  if (!isAdmin) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h4" color="error" gutterBottom>403 - Access Denied</Typography>
        <Typography>You do not have Administrative privileges.</Typography>
      </Box>
    );
  }
  
  return <Outlet />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route element={<Layout />}>
            {/* Landing Page */}
            <Route path="/" element={
              <Box sx={{ p: 4 }}>
                <Box sx={{ display: 'flex', gap: 4, alignItems: 'center', mb: 3, flexWrap: 'wrap' }}>
                  <Box sx={{ flex: 1, minWidth: 280 }}>
                    <Typography variant="h3" sx={{ fontWeight: 700 }}>Bank UDD Platform</Typography>
                    <Typography sx={{ mt: 1, color: 'text.secondary' }}>Securely manage bank datasets, transaction feeds, and reporting schemas.</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Box>
                      <Typography variant="subtitle2">Quick actions</Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <Button variant="contained" color="primary" onClick={() => window.location.href = '/data'}>Explore Datasets</Button>
                        <Button variant="outlined" onClick={() => window.location.reload()}>Refresh</Button>
                      </Box>
                    </Box>
                  </Box>
                </Box>

                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 2 }}>
                  <Box sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant="h6">Import Transactions</Typography>
                    <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>Upload CSV files of transactions or reference data. The platform validates and ingests records into the target dataset.</Typography>
                  </Box>

                  <Box sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant="h6">Explore Datasets</Typography>
                    <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>Browse feeds, view schema versions, and run ad-hoc exports for reporting.</Typography>
                  </Box>

                  <Box sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant="h6">Access Controls</Typography>
                    <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>Role-based access ensures teams only see datasets they are allowed to view.</Typography>
                  </Box>
                </Box>
              </Box>
            } />
            
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/data/:group" element={<DataGridPage />} />
            
            {/* Protected Admin Section */}
            <Route element={<AdminRoute />}>
              <Route path="/admin" element={<AdminPage />} />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
