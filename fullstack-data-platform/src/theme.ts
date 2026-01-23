import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#165a9c',
    },
    secondary: {
      main: '#2b8cc4',
    },
    background: {
      default: '#f4f6f8',
      paper: '#ffffff'
    }
  },
  typography: {
    fontFamily: 'Inter, Roboto, Arial, sans-serif'
  }
});

export default theme;
