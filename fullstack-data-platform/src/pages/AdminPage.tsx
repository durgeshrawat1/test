import React, { useState, useEffect, useCallback } from 'react';
import { 
  Container, Paper, Typography, Box, TextField, Button, 
  MenuItem, Alert, Stack, Divider, List, ListItem, 
  ListItemText, IconButton, CircularProgress 
} from '@mui/material';
import { AddCircle, Storage, Delete, Refresh } from '@mui/icons-material';
import { CONFIG } from '../config';

export const AdminPage: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    accessGroup: 'Finance', 
    tableName: ''
  });
  const [schemas, setSchemas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{type: 'success'|'error', text: string} | null>(null);

  // 1. Single, robust fetch function
  const fetchSchemas = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${CONFIG.API_BASE_URL}/schemas`);
      if (res.ok) {
        const data = await res.json();
        setSchemas(data);
      } else {
        const errorData = await res.json();
        console.error("Backend Error:", errorData.detail);
        setMessage({ type: 'error', text: `Failed to load datasets: ${errorData.detail || 'Unknown error'}` });
      }
    } catch (e) {
      console.error("Failed to fetch schemas", e);
      setMessage({ type: 'error', text: "Connection error to API server." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchemas();
  }, [fetchSchemas]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setMessage(null);
    if (!formData.name || !formData.tableName) {
        setMessage({ type: 'error', text: "Name and Table ID are required" });
        return;
    }

    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/admin/create-dataset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Creation failed");
      }
      
      setMessage({ type: 'success', text: "Dataset Created!" });
      setFormData({ name: '', description: '', accessGroup: 'Finance', tableName: '' });
      fetchSchemas(); 
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || "Error creating dataset. Ensure you are Admin." });
    }
  };

  const handleDelete = async (schemaId: number, tableName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${tableName}"? This will drop the physical table and delete all data.`)) {
      return;
    }

    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/admin/schema/${schemaId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setMessage({ type: 'success', text: `Dataset ${tableName} deleted.` });
        fetchSchemas(); 
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Delete failed");
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || "Failed to delete dataset." });
    }
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>Platform Administration</Typography>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Stack spacing={4}>
        <Paper sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Storage color="primary" sx={{ mr: 2 }} />
              <Typography variant="h6">Create New Dataset</Typography>
          </Box>
          
          <Stack spacing={3}>
              <TextField fullWidth label="Dataset Name" name="name" value={formData.name} onChange={handleChange} />
              <TextField fullWidth label="Description" name="description" value={formData.description} onChange={handleChange} />
              
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
                  <TextField select fullWidth label="Access Group" name="accessGroup" value={formData.accessGroup} onChange={handleChange}>
                      <MenuItem value="Finance">Finance</MenuItem>
                      <MenuItem value="Market">Market</MenuItem>
                      <MenuItem value="HR">HR</MenuItem>
                      <MenuItem value="Admin">Admin</MenuItem>
                  </TextField>
                  <TextField 
                      fullWidth 
                      label="Physical Table ID" 
                      name="tableName" 
                      value={formData.tableName} 
                      onChange={handleChange} 
                      helperText="Lowercase, no spaces"
                  />
              </Stack>

              <Button variant="contained" size="large" startIcon={<AddCircle />} onClick={handleSubmit} fullWidth disabled={loading}>
                  {loading ? <CircularProgress size={24} /> : "Create Dataset"}
              </Button>
          </Stack>
        </Paper>

        <Paper sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Refresh color="primary" sx={{ mr: 2 }} />
              <Typography variant="h6">Existing Datasets</Typography>
            </Box>
            <IconButton onClick={fetchSchemas} disabled={loading}>
                <Refresh />
            </IconButton>
          </Box>
          <Divider sx={{ mb: 2 }} />
          
          <List>
            {schemas.length === 0 && !loading && (
              <Typography variant="body2" color="text.secondary">No datasets found.</Typography>
            )}
            {schemas.map((s) => (
              <ListItem 
                key={s.id}
                secondaryAction={
                  <IconButton edge="end" color="error" onClick={() => handleDelete(s.id, s.name)}>
                    <Delete />
                  </IconButton>
                }
              >
                <ListItemText 
                  primary={s.name} 
                  secondary={`Group: ${s.accessGroup} | Table: ${s.physical_table_name || 'N/A'}`} 
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      </Stack>
    </Container>
  );
};
