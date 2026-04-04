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
      sx={{ pt: { xs: 14, md: 18 }, pb: { xs: 6, md: 10 }, textAlign: "center" }}
    >
      <Container maxWidth="md">
        {/* Badge */}
        <motion.div custom={0} initial="hidden" animate="visible" variants={fadeUp}>
          <Chip
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
              bgcolor: "#1c1c1f",
              borderColor: "#2a2a2e",
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
              fontSize: { xs: "2.25rem", md: "3.5rem" },
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
              mb: 2.5,
            }}
          >
            Unstructured docs to
            <br />
            <Box
              component="span"
              sx={{
                background: "linear-gradient(135deg, #818cf8, #06b6d4)",
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
              sx={{ px: 3 }}
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
                "&:hover": { borderColor: "text.secondary", bgcolor: "#141416" },
              }}
            >
              PyPI Package
            </Button>
          </Box>
        </motion.div>

        {/* Install bar */}
        <motion.div custom={4} initial="hidden" animate="visible" variants={fadeUp}>
          <Paper
            onClick={handleCopy}
            elevation={0}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              bgcolor: "#141416",
              border: "1px solid #2a2a2e",
              borderRadius: 2,
              px: 2.5,
              py: 1.75,
              maxWidth: 480,
              mx: "auto",
              mb: 4,
              cursor: "pointer",
              transition: "border-color 0.2s",
              "&:hover": { borderColor: "primary.main" },
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
