"use client";

import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";

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
        backgroundColor: scrolled ? "rgba(10,10,11,0.9)" : "transparent",
        backdropFilter: scrolled ? "blur(12px)" : "none",
        borderBottom: scrolled ? "1px solid #2a2a2e" : "none",
        transition: "all 0.3s",
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ justifyContent: "space-between" }}>
          <Typography
            component="a"
            href="/"
            variant="h6"
            sx={{
              fontWeight: 700,
              color: "text.primary",
              textDecoration: "none",
              fontSize: "1.125rem",
            }}
          >
            doc
            <Box component="span" sx={{ color: "primary.light" }}>
              pipe
            </Box>
          </Typography>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {["#pipelines", "#rag", "#features", "#usage"].map((href) => (
              <Button
                key={href}
                component="a"
                href={href}
                variant="text"
                color="inherit"
                sx={{ color: "text.secondary", fontSize: "0.875rem" }}
              >
                {href.replace("#", "").charAt(0).toUpperCase() +
                  href.replace("#", "").slice(1)}
              </Button>
            ))}
            <Button
              component="a"
              href="https://github.com/thesunnysinha/docpipe"
              target="_blank"
              rel="noopener noreferrer"
              variant="text"
              color="inherit"
              sx={{ color: "text.secondary", fontSize: "0.875rem" }}
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
              size="small"
              clickable
              sx={{ fontWeight: 600, fontSize: "0.75rem" }}
            />
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
