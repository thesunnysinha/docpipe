"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import GitHubIcon from "@mui/icons-material/GitHub";
import InventoryIcon from "@mui/icons-material/Inventory";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.1, ease: "easeOut" as const },
  }),
};

const pillVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.4,
      delay: 0.5 + i * 0.08,
      ease: "easeOut" as const,
    },
  }),
};

const pills = [
  "MIT License",
  <>Python <strong style={{ color: "#e4e4e7" }}>3.10+</strong></>,
  <><strong style={{ color: "#e4e4e7" }}>4</strong> Pipelines</>,
  <><strong style={{ color: "#e4e4e7" }}>5</strong> RAG Strategies</>,
  "Zero Vendor Lock-in",
];

export default function Hero() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText("pip install docpipe-sdk[all]");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box
      component="section"
      sx={{ pt: { xs: 14, md: 18 }, pb: { xs: 6, md: 10 }, textAlign: "center", position: "relative", overflow: "hidden" }}
    >
      {/* Background orbs */}
      <Box sx={{
        position: "absolute", inset: 0, overflow: "hidden", zIndex: 0,
        "&::before": {
          content: '""',
          position: "absolute",
          top: "20%", left: "10%",
          width: 600, height: 600,
          background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
          borderRadius: "50%",
        },
        "&::after": {
          content: '""',
          position: "absolute",
          top: "30%", right: "10%",
          width: 400, height: 400,
          background: "radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)",
          borderRadius: "50%",
        },
      }} />

      <Container maxWidth="md" sx={{ position: "relative", zIndex: 1 }}>
        {/* Badge */}
        <motion.div custom={0} initial="hidden" animate="visible" variants={fadeUp}>
          <Chip
            icon={<AutoAwesomeIcon sx={{ fontSize: "0.875rem !important", color: "#818cf8 !important" }} />}
            variant="outlined"
            label={
              <span>
                Powered by{" "}
                <strong style={{ color: "#818cf8" }}>Docling</strong> ·{" "}
                <strong style={{ color: "#818cf8" }}>LangExtract</strong> ·{" "}
                <strong style={{ color: "#818cf8" }}>LangChain</strong> ·{" "}
                <strong style={{ color: "#818cf8" }}>RAGPipeline</strong>
              </span>
            }
            sx={{
              mb: 3,
              bgcolor: "rgba(99,102,241,0.06)",
              borderColor: "rgba(99,102,241,0.25)",
              color: "text.secondary",
              fontSize: "0.8125rem",
              height: "auto",
              py: 0.75,
              "& .MuiChip-label": { px: 2 },
            }}
          />
        </motion.div>

        {/* H1 */}
        <motion.div custom={1} initial="hidden" animate="visible" variants={fadeUp}>
          <Typography
            variant="h1"
            sx={{
              fontSize: { xs: "2.75rem", md: "4rem", lg: "5rem" },
              fontWeight: 900,
              lineHeight: 1.05,
              letterSpacing: "-0.03em",
              mb: 2.5,
            }}
          >
            Unstructured docs to
            <br />
            <Box
              component="span"
              sx={{
                background: "linear-gradient(135deg, #818cf8 0%, #06b6d4 50%, #22c55e 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              answers
            </Box>
            <br />
            in one pipeline
          </Typography>
        </motion.div>

        {/* Subtitle */}
        <motion.div custom={2} initial="hidden" animate="visible" variants={fadeUp}>
          <Typography
            variant="h6"
            color="text.secondary"
            sx={{
              fontSize: "1.125rem",
              fontWeight: 400,
              maxWidth: 640,
              mx: "auto",
              mb: 4.5,
              lineHeight: 1.7,
            }}
          >
            Parse documents, extract structured data with LLMs, ingest into your
            vector DB, and ask questions with 5 RAG strategies. Composable
            pipelines, no vendor lock-in.
          </Typography>
        </motion.div>

        {/* Buttons */}
        <motion.div custom={3} initial="hidden" animate="visible" variants={fadeUp}>
          <Box sx={{ display: "flex", gap: 1.5, justifyContent: "center", flexWrap: "wrap", mb: 4 }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              startIcon={<GitHubIcon />}
              component="a"
              href="https://github.com/thesunnysinha/docpipe"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                px: 3,
                background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                boxShadow: "0 0 20px rgba(99,102,241,0.35)",
                "&:hover": { boxShadow: "0 0 28px rgba(99,102,241,0.5)" },
              }}
            >
              View on GitHub
            </Button>
            <Button
              variant="outlined"
              size="large"
              startIcon={<InventoryIcon />}
              component="a"
              href="https://pypi.org/project/docpipe-sdk/"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                px: 3,
                borderColor: "#2a2a2e",
                color: "text.primary",
                bgcolor: "#1c1c1f",
                "&:hover": { borderColor: "primary.light", bgcolor: "#141416" },
              }}
            >
              PyPI Package
            </Button>
          </Box>
        </motion.div>

        {/* Install bar with gradient border */}
        <motion.div custom={4} initial="hidden" animate="visible" variants={fadeUp}>
          <Box sx={{
            background: "linear-gradient(135deg, #6366f1, #06b6d4)",
            borderRadius: "10px",
            p: "1px",
            maxWidth: 500,
            mx: "auto",
            mb: 4,
          }}>
            <Paper
              onClick={handleCopy}
              elevation={0}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                bgcolor: "#0d0d0f",
                borderRadius: "9px",
                px: 2.5,
                py: 1.75,
                cursor: "pointer",
                transition: "background-color 0.2s",
                "&:hover": { bgcolor: "#111113" },
              }}
            >
              <Typography
                component="code"
                sx={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "0.875rem",
                  flex: 1,
                  textAlign: "left",
                  color: "text.primary",
                }}
              >
                <Box component="span" sx={{ color: "text.secondary" }}>
                  $
                </Box>{" "}
                pip install docpipe-sdk[all]
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 0.75,
                  color: copied ? "success.main" : "text.secondary",
                  fontSize: "0.75rem",
                  flexShrink: 0,
                  ml: "auto",
                }}
              >
                {copied ? (
                  <>
                    <CheckIcon sx={{ fontSize: 14 }} />
                    <Typography variant="caption" color="success.main">
                      copied!
                    </Typography>
                  </>
                ) : (
                  <>
                    <ContentCopyIcon sx={{ fontSize: 14 }} />
                    <Typography variant="caption" color="text.secondary">
                      click to copy
                    </Typography>
                  </>
                )}
              </Box>
            </Paper>
          </Box>
        </motion.div>

        {/* Stats pills */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            gap: 1.5,
            flexWrap: "wrap",
          }}
        >
          {pills.map((pill, i) => (
            <motion.div
              key={i}
              custom={i}
              initial="hidden"
              animate="visible"
              variants={pillVariants}
            >
              <Chip
                label={pill}
                variant="outlined"
                size="small"
                sx={{
                  bgcolor: "#141416",
                  borderColor: "#2a2a2e",
                  color: "text.secondary",
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  height: "auto",
                  py: 0.5,
                  "& .MuiChip-label": { px: 1.75 },
                }}
              />
            </motion.div>
          ))}
        </Box>
      </Container>
    </Box>
  );
}
