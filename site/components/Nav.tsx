"use client";

import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import GitHubIcon from "@mui/icons-material/GitHub";

const navLinks = ["#pipelines", "#rag", "#features", "#usage"];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        backgroundColor: scrolled ? "rgba(10,10,11,0.92)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid #2a2a2e" : "none",
        boxShadow: scrolled ? "0 1px 0 rgba(99,102,241,0.2)" : "none",
        transition: "all 0.3s",
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ justifyContent: "space-between" }}>
          {/* Logo */}
          <Typography
            component="a"
            href="/"
            variant="h6"
            sx={{
              fontWeight: 700,
              color: "text.primary",
              textDecoration: "none",
              fontSize: "1.125rem",
              display: "flex",
              alignItems: "center",
              gap: 0.75,
            }}
          >
            <Box
              component="span"
              sx={{
                color: "primary.light",
                fontSize: "1rem",
                lineHeight: 1,
              }}
            >
              ◆
            </Box>
            doc
            <Box component="span" sx={{ color: "primary.light" }}>
              pipe
            </Box>
          </Typography>

          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            {navLinks.map((href) => (
              <Button
                key={href}
                component="a"
                href={href}
                variant="text"
                color="inherit"
                sx={{
                  color: "text.secondary",
                  fontSize: "0.875rem",
                  px: 1.5,
                  position: "relative",
                  "&:hover": { color: "text.primary", bgcolor: "transparent" },
                  "& .nav-underline": {
                    content: '""',
                    position: "absolute",
                    bottom: 6,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: 0,
                    height: 2,
                    bgcolor: "primary.light",
                    borderRadius: 1,
                    transition: "width 0.2s ease",
                  },
                  "&:hover .nav-underline": {
                    width: "60%",
                  },
                }}
              >
                {href.replace("#", "").charAt(0).toUpperCase() +
                  href.replace("#", "").slice(1)}
                <Box component="span" className="nav-underline" />
              </Button>
            ))}
            <Button
              component="a"
              href="https://github.com/thesunnysinha/docpipe"
              target="_blank"
              rel="noopener noreferrer"
              variant="text"
              startIcon={<GitHubIcon sx={{ fontSize: "1rem !important" }} />}
              sx={{
                color: "text.secondary",
                fontSize: "0.875rem",
                px: 1.5,
                "&:hover": { color: "text.primary", bgcolor: "transparent" },
              }}
            >
              GitHub
            </Button>
            <Chip
              component="a"
              href="https://pypi.org/project/docpipe-sdk/"
              target="_blank"
              rel="noopener noreferrer"
              label="PyPI"
              color="primary"
              variant="filled"
              size="small"
              clickable
              sx={{
                fontWeight: 600,
                fontSize: "0.75rem",
                ml: 0.5,
                background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                "&:hover": { opacity: 0.9 },
              }}
            />
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
