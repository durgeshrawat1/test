import React from 'react';
import { Box, Typography, Button } from '@mui/material';

interface State { error: Error | null }

interface Props { children?: React.ReactNode }

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: any) {
    // eslint-disable-next-line no-console
    console.error('Unhandled error caught by ErrorBoundary', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <Box sx={{ p: 4 }}>
          <Typography variant="h5" color="error" gutterBottom>Something went wrong</Typography>
          <Typography sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>{this.state.error.toString()}</Typography>
          <Button variant="contained" onClick={() => window.location.reload()}>Reload</Button>
        </Box>
      );
    }
    return this.props.children as React.ReactNode;
  }
}
