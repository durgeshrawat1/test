import React, { useState } from 'react';
import { 
  Box, Drawer, AppBar, Toolbar, List, Typography, 
  Divider, ListItem, ListItemButton, ListItemIcon, ListItemText, Avatar, Menu, MenuItem
} from '@mui/material';
import { 
  Dashboard, Storage, AdminPanelSettings, Person, ExitToApp 
} from '@mui/icons-material';
import { useNavigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CONFIG } from '../config';

const drawerWidth = 240;

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation(); // Now used below to highlight active links
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  // Robust check for Admin status (Case-insensitive)
  const isAdmin = user?.groups?.some(g => g.toLowerCase() === 'admin');

  const menuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  ];

  // Dynamic groups fetched from backend
  const [groups, setGroups] = React.useState<Array<{group: string, count: number}>>([]);
  const [backendHealthy, setBackendHealthy] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    let mounted = true;
    const fetchGroups = async () => {
      try {
        // include ALB token if frontend environment exposes it
        const token = (window as any).__ALB_JWT__ || localStorage.getItem('ALB_JWT') || undefined;
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`${CONFIG.API_BASE_URL}/metadata/groups?limit=1000`, { headers, credentials: 'include' });
        if (!mounted) return;
        if (!res.ok) {
          setGroups([]);
          setBackendHealthy(false);
          return;
        }
        const data = await res.json();
        setGroups(data.items || []);
        setBackendHealthy(true);
      } catch (e) {
        console.error('Failed to fetch groups', e);
        setGroups([]);
        setBackendHealthy(false);
      }
    };
    fetchGroups();
    return () => { mounted = false; };
  }, []);

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <img src="/logo-bank.svg" className="logo" alt="Bank Data Hub" style={{ height: 32, marginRight: 8 }} />
            <Typography variant="h6" noWrap component="div">
              Bank Data Hub
            </Typography>
          </Box>
          
          {/* USER IDENTITY SECTION - Hover avatar opens Profile/Logout menu */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* header: backend status indicator removed per request */}
            {user && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {/* Show only the avatar; hide email and ADMIN chip for a cleaner header */}
                <Avatar
                  sx={{ width: 36, height: 36, bgcolor: 'secondary.main', ml: 1, cursor: 'pointer' }}
                  onMouseEnter={(e) => setAnchorEl(e.currentTarget as HTMLElement)}
                >
                  {user.email ? user.email[0].toUpperCase() : 'U'}
                </Avatar>
              </Box>
            )}

            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={() => setAnchorEl(null)}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
              MenuListProps={{ onMouseLeave: () => setAnchorEl(null) }}
            >
              <MenuItem onClick={() => { setAnchorEl(null); navigate('/profile'); }}>
                <ListItemIcon><Person fontSize="small" /></ListItemIcon>
                <ListItemText>Profile</ListItemText>
              </MenuItem>
              <MenuItem onClick={() => { setAnchorEl(null); logout(); }}>
                <ListItemIcon><ExitToApp fontSize="small" /></ListItemIcon>
                <ListItemText>Logout</ListItemText>
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton 
                  selected={location.pathname === item.path} // USE OF LOCATION VARIABLE
                  onClick={() => navigate(item.path)}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}

            <Divider sx={{ my: 1 }} />
              <Typography variant="caption" sx={{ px: 3, py: 1, display: 'block', color: 'text.secondary', fontWeight: 'bold' }}>
                DATASETS & FEEDS
              </Typography>
            
            {/* Dynamic Business Units (access groups) — rendered from backend `groups`. */}
            {groups.length > 0 ? groups.map((g) => {
              const hasAccess = Boolean(isAdmin || user?.groups?.some(ug => String(ug) === String(g.group)));
              return (
                <ListItem key={g.group} disablePadding>
                  <ListItemButton 
                    selected={location.pathname === `/data/${g.group}`}
                    onClick={() => { if (hasAccess) navigate(`/data/${g.group}`); }}
                    disabled={!hasAccess}
                    sx={{ opacity: hasAccess ? 1 : 0.5 }}
                  >
                    <ListItemIcon><Storage /></ListItemIcon>
                    <ListItemText primary={g.group} />
                    <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>{g.count}</Typography>
                  </ListItemButton>
                </ListItem>
              );
            }) : (
              <ListItem>
                <ListItemText
                  primary={backendHealthy === false ? 'No datasets — backend unavailable' : 'No datasets available'}
                  secondary={backendHealthy === false ? 'Backend API unreachable. Confirm network, check service, or contact platform admin.' : 'No datasets have been created yet. Import or register a dataset to begin.'}
                />
                <ListItemButton onClick={() => { window.location.reload(); }}>
                  <ListItemText primary="Retry Connection" />
                </ListItemButton>
              </ListItem>
            )}

            {/* Admin Console - always visible but disabled unless user is admin */}
            <Divider sx={{ my: 1 }} />
            <ListItem disablePadding>
              <ListItemButton
                selected={location.pathname === '/admin'}
                onClick={() => { if (isAdmin) navigate('/admin'); }}
                disabled={!isAdmin}
                sx={{ opacity: isAdmin ? 1 : 0.5 }}
              >
                <ListItemIcon><AdminPanelSettings color="primary" /></ListItemIcon>
                <ListItemText primary="Admin Console" sx={{ color: isAdmin ? 'primary.main' : 'text.disabled', fontWeight: 'bold' }} />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Outlet />
      </Box>
    </Box>
  );
};
