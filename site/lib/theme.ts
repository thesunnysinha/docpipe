import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0a0a0b",
      paper: "#141416",
    },
    divider: "#2a2a2e",
    text: {
      primary: "#e4e4e7",
      secondary: "#a1a1aa",
    },
    primary: {
      main: "#6366f1",
      light: "#818cf8",
    },
    success: {
      main: "#22c55e",
    },
    info: {
      main: "#3b82f6",
    },
    warning: {
      main: "#f59e0b",
    },
    secondary: {
      main: "#ec4899",
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontWeightBold: 700,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          minHeight: 48,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
  },
});
