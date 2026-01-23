import React, { useState } from 'react';
import {
  Typography, Paper, Alert, TextField, Stack, Button, MenuItem, Checkbox, FormControlLabel
} from '@mui/material';
import { CONFIG } from '../config';

const columnTypes = [
  { value: 'string', label: 'String' },
  { value: 'text', label: 'Text' },
  { value: 'int', label: 'Integer' },
  { value: 'float', label: 'Float' },
  { value: 'bool', label: 'Boolean' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'Datetime' }
];

export const AdminPanel: React.FC = () => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [accessGroup, setAccessGroup] = useState('');
  const [tableName, setTableName] = useState('');
  const [columns, setColumns] = useState<Array<any>>([]);
  const [status, setStatus] = useState<string | null>(null);

  const addColumn = () => setColumns([...columns, { name: '', type: 'string', required: false, validation: '' }]);
  const updateColumn = (idx: number, patch: any) => setColumns(columns.map((c, i) => i === idx ? { ...c, ...patch } : c));
  const removeColumn = (idx: number) => setColumns(columns.filter((_, i) => i !== idx));

  const handleCreate = async () => {
    try {
      const payload = { name, description, accessGroup, tableName, columns };
      const res = await fetch(`${CONFIG.API_BASE_URL}/admin/create-dataset`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setStatus('Created schema id: ' + data.schema_id);
        setName(''); setDescription(''); setAccessGroup(''); setTableName(''); setColumns([]);
      } else {
        setStatus('Failed: ' + await res.text());
      }
    } catch (e) {
      setStatus('Error: ' + String(e));
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ color: 'red' }}>Admin Control Center</Typography>
      <Alert severity="warning" sx={{ mb: 2 }}>
        Restricted Area: Only users in the 'Admin' group can perform actions here.
      </Alert>

      <Stack spacing={2} sx={{ maxWidth: 800 }}>
        <TextField label="Display Name" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
        <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} fullWidth />
        <TextField label="Access Group" value={accessGroup} onChange={(e) => setAccessGroup(e.target.value)} fullWidth />
        <TextField label="Table Name (no spaces)" value={tableName} onChange={(e) => setTableName(e.target.value)} fullWidth />

        <Typography variant="h6">Columns</Typography>
        {columns.map((c, i) => (
          <Stack key={i} direction="row" spacing={1} alignItems="center">
            <TextField label="Column Name" value={c.name} onChange={(e) => updateColumn(i, { name: e.target.value })} />
            <TextField select label="Type" value={c.type} onChange={(e) => updateColumn(i, { type: e.target.value })}>
              {columnTypes.map(t => <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>)}
            </TextField>
            <FormControlLabel control={<Checkbox checked={c.required} onChange={(e) => updateColumn(i, { required: e.target.checked })} />} label="Required" />
            <TextField label="Validation (optional)" value={c.validation || ''} onChange={(e) => updateColumn(i, { validation: e.target.value })} placeholder="e.g., full_name or email" />
            <Button color="error" onClick={() => removeColumn(i)}>Remove</Button>
          </Stack>
        ))}

        <Stack direction="row" spacing={2}>
          <Button onClick={addColumn}>Add Column</Button>
          <Button variant="contained" onClick={handleCreate}>Create Dataset</Button>
        </Stack>

        {status && <Typography>{status}</Typography>}
      </Stack>
    </Paper>
  );
};
