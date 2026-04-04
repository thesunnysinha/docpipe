"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import TerminalIcon from "@mui/icons-material/Terminal";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import StorageIcon from "@mui/icons-material/Storage";
import CodeBlock from "./CodeBlock";

const sectionFadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

const cliCode = `# Parse a document
$ docpipe parse invoice.pdf --format markdown

# Ingest into your vector DB
$ docpipe ingest report.pdf \\
    --db "postgresql://..." \\
    --table docs \\
    --embedding-provider openai \\
    --embedding-model text-embedding-3-small \\
    --incremental

# Start API server
$ docpipe serve --port 8000`;

const ragCliCode = `# Ask a question (HyDE strategy)
$ docpipe rag query \\
    "What is the total revenue?" \\
    --db "postgresql://..." \\
    --table docs \\
    --strategy hyde \\
    --llm-provider openai \\
    --llm-model gpt-4o \\
    --embedding-provider openai \\
    --embedding-model text-embedding-3-small \\
    --reranker flashrank

# Evaluate RAG quality
$ docpipe evaluate run \\
    --questions qa.json \\
    --db "postgresql://..." \\
    --table docs \\
    --metrics hit_rate,answer_similarity`;

const dockerCode = `# Run API server
$ docker run -p 8000:8000 \\
    --env-file .env \\
    docpipe

# Parse in container
$ docker run -v ./data:/data \\
    docpipe parse /data/invoice.pdf

# Ingest from container
$ docker run --env-file .env \\
    docpipe ingest /data/report.pdf \\
    --db "postgresql://..." \\
    --table docs \\
    --embedding-provider openai \\
    --embedding-model text-embedding-3-small`;

const installCode = `pip install docpipe-sdk                # Core only
pip install docpipe-sdk[docling]       # + Document parsing (20+ formats)
pip install docpipe-sdk[langextract]   # + Google LangExtract
pip install docpipe-sdk[openai]        # + OpenAI embeddings & LLM
pip install docpipe-sdk[google]        # + Google Gemini
pip install docpipe-sdk[pgvector]      # + PostgreSQL vector store
pip install docpipe-sdk[rag]           # + Hybrid search (BM25)
pip install docpipe-sdk[rerank]        # + Local reranking (FlashRank)
pip install docpipe-sdk[server]        # + FastAPI server
pip install docpipe-sdk[all]           # Everything`;

const tabDefs = [
  { label: "CLI", icon: <TerminalIcon />, code: cliCode },
  { label: "RAG CLI", icon: <SmartToyIcon />, code: ragCliCode },
  { label: "Docker", icon: <StorageIcon />, code: dockerCode },
];

export default function UsageSection() {
  const [tab, setTab] = useState(0);

  return (
    <Box component="section" id="usage" sx={{ py: 12 }}>
      <Container maxWidth="lg">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={sectionFadeUp}
        >
          <Typography
            variant="h3"
            sx={{ fontWeight: 800, textAlign: "center", mb: 1.5, fontSize: { xs: "1.75rem", md: "2.25rem" }, letterSpacing: "-0.02em" }}
          >
            Use It Your Way
          </Typography>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={sectionFadeUp}
        >
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ textAlign: "center", mb: 8, maxWidth: 540, mx: "auto" }}
          >
            CLI for quick tasks, Python API for integration, Docker for deployment.
          </Typography>
        </motion.div>

        {/* MUI Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.4, ease: "easeOut" as const }}
        >
          <Paper
            elevation={0}
            sx={{ bgcolor: "#141416", border: "1px solid #2a2a2e", overflow: "hidden", mb: 3 }}
          >
            <Box sx={{ borderBottom: "1px solid #2a2a2e" }}>
              <Tabs
                value={tab}
                onChange={(_, v: number) => setTab(v)}
                TabIndicatorProps={{
                  style: { background: "#6366f1", height: 3, borderRadius: "3px 3px 0 0" },
                }}
                sx={{
                  px: 1,
                  "& .MuiTab-root": {
                    color: "text.secondary",
                    fontWeight: 600,
                    minHeight: 48,
                    "&.Mui-selected": { color: "primary.light" },
                  },
                }}
              >
                {tabDefs.map((t) => (
                  <Tab
                    key={t.label}
                    label={t.label}
                    icon={t.icon}
                    iconPosition="start"
                  />
                ))}
              </Tabs>
            </Box>
            <Box sx={{ p: 2.5 }}>
              <CodeBlock code={tabDefs[tab].code} language="bash" />
            </Box>
          </Paper>
        </motion.div>

        {/* Install options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.4, ease: "easeOut" as const }}
        >
          <Paper
            elevation={0}
            sx={{ bgcolor: "#141416", border: "1px solid #2a2a2e", overflow: "hidden" }}
          >
            <Box
              sx={{
                bgcolor: "#1c1c1f",
                px: 2,
                py: 1.25,
                borderBottom: "1px solid #2a2a2e",
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <span>📦</span>
              <Typography variant="caption" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                Install Options
              </Typography>
            </Box>
            <Box sx={{ p: 2 }}>
              <CodeBlock code={installCode} language="bash" />
            </Box>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
}
