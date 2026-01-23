import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Paper, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Button, Toolbar, IconButton, Dialog, DialogTitle, DialogContent, TextField, DialogActions,
  Stack, MenuItem, Select, FormControl, InputLabel, CircularProgress, Autocomplete
} from '@mui/material';
import { Add, Refresh, UploadFile, FilterList, Edit, Save, Cancel } from '@mui/icons-material';
import { FixedSizeList as VirtualList } from 'react-window';
import type { ListChildComponentProps } from 'react-window';
// Note: papaparse not required now; CSV handled by backend endpoints
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CONFIG } from '../config';
import TablePagination from '@mui/material/TablePagination';

export const DataGridPage: React.FC = () => {
  // `group` (Business Unit) comes from the URL (e.g., /data/finance)
  const { group } = useParams<{ group: string }>();
  const { user } = useAuth();

  const [selectedGroup, setSelectedGroup] = useState<string>(group || '');
  const [selectedSchemaId, setSelectedSchemaId] = useState<number | null>(null);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [availableSchemas, setAvailableSchemas] = useState<any[]>([]);
  const [groupOptions, setGroupOptions] = useState<string[]>([]);
  const [groupQuery, setGroupQuery] = useState<string>('');
  const [data, setData] = useState<any[]>([]);
  const [columnsMeta, setColumnsMeta] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(25);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [open, setOpen] = useState<boolean>(false);
  const [newRecord, setNewRecord] = useState<Record<string, any>>({});

  // EDIT State
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<Record<string, any>>({});

  // --- 1. ADMIN & GROUP LOGIC (COMPREHENSIVE) ---
  const relevantGroups = useMemo(() => {
    if (!user?.groups) return [];

    // Robust check for Admin group
    const isAdmin = user.groups.some(g => g.toLowerCase() === 'admin');

    if (isAdmin) {
      // If Admin, inject the current BU from the URL into the list
      // This allows the Admin to view groups even if not in those groups
      const adminGroups = [group || ''];
      // Keep other non-admin groups the user might have
      const otherGroups = user.groups.filter(g => g.toLowerCase() !== 'admin');
      return Array.from(new Set([...adminGroups, ...otherGroups]));
    }

    // Regular users: Case-sensitive filter based on the URL prefix
    return user.groups.filter(g => g.startsWith(group || ''));

  }, [user, group]);

  // Debounced group search for scalability (typeahead)
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const q = groupQuery || '';
        const res = await fetch(`${CONFIG.API_BASE_URL}/metadata/groups?q=${encodeURIComponent(q)}&limit=20&offset=0`);
        if (res.ok) {
          const payload = await res.json();
          setGroupOptions((payload.items || []).map((i: any) => i.group));
        }
      } catch (err) {
        console.error('Group search failed', err);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [groupQuery]);

  // --- 3. FETCH DATA ROWS ---
  const fetchData = async (pageParam = page, size = rowsPerPage) => {
    if (!selectedSchemaId) return;
    setLoading(true);
    try {
      const res = await fetch(`${CONFIG.API_BASE_URL}/data/${selectedSchemaId}?limit=${size}&offset=${pageParam * size}`);
      if (res.ok) {
        const payload = await res.json();
        setData(payload.rows || []);
        setTotalRows(payload.total || 0);
      }
    } catch (e) {
      console.error("Data fetch failed", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // When schema/table selection changes, reset pagination and fetch page 0
    setPage(0);
    fetchData(0, rowsPerPage);
  }, [selectedSchemaId]);

  // --- 3b. FETCH COLUMNS METADATA FOR SELECTED TABLE ---
  useEffect(() => {
    const fetchColumns = async () => {
      if (!selectedSchemaId) return;
      try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/schemas/${selectedSchemaId}/columns`);
        if (res.ok) {
          const cols = await res.json();
          setColumnsMeta(cols);
        } else {
          setColumnsMeta([]);
        }
      } catch (e) {
        console.error('Failed to fetch columns meta', e);
        setColumnsMeta([]);
      }
    };
    fetchColumns();
  }, [selectedSchemaId]);

  // --- 4. DATA MODIFICATION ---
  const handleManualAdd = async () => {
    try {
      // Client-side validation using columnsMeta
      if (columnsMeta.length > 0) {
        for (const col of columnsMeta) {
          const key = col.column_name;
          const val = newRecord[key];
          if (col.required && (val === undefined || val === null || String(val).trim() === '')) {
            alert(`${key} is required`);
            return;
          }
          if (val !== undefined && val !== null && String(val).trim() !== '') {
            if (col.data_type === 'int' && isNaN(parseInt(String(val), 10))) {
              alert(`${key} must be an integer`);
              return;
            }
            if (col.data_type === 'float' && isNaN(parseFloat(String(val)))) {
              alert(`${key} must be a number`);
              return;
            }
            if (col.validation === 'full_name') {
              // disallow digits in a name
              if (/[0-9]/.test(String(val))) { alert(`${key} appears to be invalid (no digits allowed)`); return; }
            }
            if (col.validation === 'email') {
              const re = /^\S+@\S+\.\S+$/;
              if (!re.test(String(val))) { alert(`${key} must be a valid email`); return; }
            }
          }
        }
      }

      const res = await fetch(`${CONFIG.API_BASE_URL}/data/${selectedSchemaId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: newRecord })
      });
      if (res.ok) {
        setOpen(false);
        setNewRecord({});
        fetchData();
      } else {
        const txt = await res.text();
        alert('Failed to add record: ' + txt);
      }
    } catch (e) {
      console.error("Failed to add record", e);
      alert('Error adding record: ' + String(e));
    }
  };

  // --- 5. EDIT HANDLERS ---
  const handleEditClick = (row: any) => {
    setEditingId(row.id);
    setEditValues(row);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSaveEdit = async () => {
    if (!editingId || !selectedSchemaId) return;
    try {
      const res = await fetch(`${CONFIG.API_BASE_URL}/data/${selectedSchemaId}/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: editValues })
      });

      if (res.ok) {
        setEditingId(null);
        setEditValues({});
        fetchData(); // Refresh to see confirmed backend data
      } else {
        alert("Failed to update record");
      }
    } catch (e) {
      console.error("Update failed", e);
      alert("Error connecting to server");
    }
  };


  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
    fetchData(newPage, rowsPerPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newSize = parseInt(event.target.value, 10);
    setRowsPerPage(newSize);
    setPage(0);
    fetchData(0, newSize);
  };

  return (
    <Box>
      {/* SELECTION HEADER */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
          <Typography variant="h5" sx={{ mb: 3, textTransform: 'capitalize', fontWeight: 'bold' }}>
          {group} Business Unit
        </Typography>

        <Stack direction="row" spacing={3} alignItems="center">
          <Autocomplete
            freeSolo={false}
            options={Array.from(new Set([...relevantGroups, ...groupOptions]))}
            value={selectedGroup}
            onChange={(_e, v) => {
              const val = v || '';
              setSelectedGroup(val as string);
              setSelectedSchemaId(null);
              setSelectedTable('');
              setAvailableSchemas([]);
              setData([]);
            }}
            inputValue={groupQuery}
            onInputChange={(_e, v) => setGroupQuery(v)}
            sx={{ minWidth: 320 }}
            renderInput={(params) => <TextField {...params} label="Business Unit" />}
          />

          <FormControl sx={{ minWidth: 280 }} disabled={!selectedGroup}>
            <InputLabel id="schema-select-label">Schema (Dataset)</InputLabel>
            <Select
              labelId="schema-select-label"
              value={selectedSchemaId ?? ''}
              label="Schema (Dataset)"
              onChange={(e) => {
                const sid = Number(e.target.value) || null;
                setSelectedSchemaId(sid);
                const sel = availableSchemas.find((s: any) => s.id === sid);
                setSelectedTable(sel ? sel.physical_table_name : '');
              }}
            >
              <MenuItem value=""><em>None</em></MenuItem>
              {availableSchemas.map((t) => (
                <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 280 }} disabled={!selectedSchemaId}>
            <InputLabel id="table-select-label">Table</InputLabel>
            <Select
              labelId="table-select-label"
              value={selectedTable}
              label="Table"
              onChange={(e) => setSelectedTable(e.target.value)}
            >
              <MenuItem value=""><em>None</em></MenuItem>
              {selectedTable && <MenuItem value={selectedTable}>{selectedTable}</MenuItem>}
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {/* DATA VIEW */}
      {selectedSchemaId && (
        <>
          <Paper sx={{ mb: 3, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: '#fcfcfc' }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
              <FilterList sx={{ mr: 1 }} />
              {availableSchemas.find((t: any) => t.id === selectedSchemaId)?.name || 'Data View'}
            </Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="outlined" component="label" startIcon={<UploadFile />}>
                Import CSV
                <input type="file" hidden accept=".csv" onChange={async (e) => {
                  const file = e.target.files && e.target.files[0];
                  if (!file || !selectedSchemaId) return;
                  try {
                    const form = new FormData();
                    form.append('file', file);
                    const res = await fetch(`${CONFIG.API_BASE_URL}/data/${selectedSchemaId}/import-csv`, {
                      method: 'POST', body: form
                    });
                    if (res.ok) {
                      const out = await res.json();
                      alert(`Import completed. Inserted: ${out.inserted}`);
                      fetchData();
                    } else {
                      const txt = await res.text();
                      alert('Import failed: ' + txt);
                    }
                  } catch (err) {
                    console.error('CSV import failed', err);
                    alert('CSV import error: ' + String(err));
                  }
                  // clear file input
                  (e.target as HTMLInputElement).value = '';
                }} />
              </Button>
              <Button variant="outlined" startIcon={<FilterList />} onClick={async () => {
                if (!selectedSchemaId) return; try {
                  const res = await fetch(`${CONFIG.API_BASE_URL}/data/${selectedSchemaId}/export-csv`, { method: 'GET' });
                  if (!res.ok) { alert('Export failed: ' + (await res.text())); return; }
                  const blob = await res.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `schema_${selectedSchemaId}.csv`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  window.URL.revokeObjectURL(url);
                } catch (err) { console.error('Export failed', err); alert('Export failed: ' + String(err)); }
              }}>Export CSV</Button>
              <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>Add Record</Button>
            </Stack>
          </Paper>

          <TableContainer component={Paper} sx={{ boxShadow: 3, position: 'relative' }}>
            {loading && (
              <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', bgcolor: 'rgba(255,255,255,0.7)', zIndex: 2 }}>
                <CircularProgress />
              </Box>
            )}
            <Toolbar sx={{ justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" color="text.secondary">{data.length} Records Found</Typography>
              <IconButton onClick={() => fetchData(page, rowsPerPage)}><Refresh /></IconButton>
            </Toolbar>
            <Table stickyHeader>
              <TableHead>
                  <TableRow>
                    { (data.length > 0 || columnsMeta.length > 0) ? (
                      <>
                        <TableCell sx={{ bgcolor: '#f5f5f5', fontWeight: 'bold' }}>ACTIONS</TableCell>
                        {(columnsMeta.length > 0 ? columnsMeta.map(c => c.column_name) : (data.length>0 ? Object.keys(data[0]) : [])).map(k => (
                          <TableCell key={k} sx={{ bgcolor: '#f5f5f5', fontWeight: 'bold' }}>{k.toUpperCase()}</TableCell>
                        ))}
                      </>
                    ) : <TableCell>No data available in this table.</TableCell>}
                  </TableRow>
                </TableHead>
              <TableBody>
                {data.length > 0 && (
                  <VirtualList
                    height={400}
                    itemCount={data.length}
                    itemSize={52}
                    width="100%"
                  >
                    {({ index, style }: ListChildComponentProps) => {
                      const row = data[index];
                      const columns = data.length > 0 ? Object.keys(data[0]) : [];
                      return (
                        <TableRow key={index} hover selected={editingId === row.id} style={style}>
                          <TableCell>
                            {editingId === row.id ? (
                              <Stack direction="row" spacing={1}>
                                <IconButton size="small" color="primary" onClick={handleSaveEdit}><Save /></IconButton>
                                <IconButton size="small" color="error" onClick={handleCancelEdit}><Cancel /></IconButton>
                              </Stack>
                            ) : (
                              <IconButton size="small" onClick={() => handleEditClick(row)}><Edit /></IconButton>
                            )}
                          </TableCell>

                          {columns.map((key, j) => {
                            const val = row[key];
                            const isId = key === 'id';
                            const isEditing = editingId === row.id && !isId;
                            return (
                              <TableCell key={j}>
                                {isEditing ? (
                                  <TextField
                                    size="small"
                                    value={editValues[key] || ''}
                                    onChange={(e) => setEditValues({ ...editValues, [key]: e.target.value })}
                                    sx={{ '& .MuiInputBase-input': { py: 0.5, px: 1, fontSize: '0.875rem' } }}
                                  />
                                ) : (
                                  val !== null ? String(val) : '-'
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      );
                    }}
                  </VirtualList>
                )}
              </TableBody>
            </Table>
            </TableContainer>

            <TablePagination
              component="div"
              count={totalRows}
              page={page}
              onPageChange={handleChangePage}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
        </>
      )}

      {/* ADD RECORD DIALOG */}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add New Record</DialogTitle>
        <DialogContent dividers>
            <Stack spacing={2} sx={{ mt: 1 }}>
            {columnsMeta.length > 0 ? columnsMeta.filter(c => c.column_name !== 'id' && c.column_name !== 'created_at').map(col => {
              const key = col.column_name;
              return (
                <TextField
                  key={key}
                  fullWidth
                  label={key.toUpperCase()}
                  onChange={e => setNewRecord({ ...newRecord, [key]: e.target.value })}
                />
              );
            }) : (data.length > 0 && Object.keys(data[0]).filter(k => k !== 'id' && k !== 'created_at').map(key => (
              <TextField
                key={key}
                fullWidth
                label={key.toUpperCase()}
                onChange={e => setNewRecord({ ...newRecord, [key]: e.target.value })}
              />
            )))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleManualAdd} variant="contained">Save Record</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
