"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
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

const tabs = [
  { icon: "▶", label: "CLI", code: cliCode },
  { icon: "🤖", label: "RAG CLI", code: ragCliCode },
  { icon: "🐋", label: "Docker", code: dockerCode },
];

export default function UsageSection() {
  return (
    <Box component="section" id="usage" sx={{ py: 10 }}>
      <Container maxWidth="lg">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={sectionFadeUp}
        >
          <Typography
            variant="h3"
            sx={{ fontWeight: 700, textAlign: "center", mb: 1.5, fontSize: "2rem" }}
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
            sx={{ textAlign: "center", mb: 8 }}
          >
            CLI for quick tasks, Python API for integration, Docker for deployment.
          </Typography>
        </motion.div>

        {/* 3-col code blocks */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {tabs.map((tab, i) => (
            <Grid item xs={12} lg={4} key={tab.label}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.4, delay: i * 0.08, ease: "easeOut" as const }}
                style={{ height: "100%" }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    height: "100%",
                    bgcolor: "#141416",
                    border: "1px solid #2a2a2e",
                    overflow: "hidden",
                  }}
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
                    <span>{tab.icon}</span>
                    <Typography variant="caption" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                      {tab.label}
                    </Typography>
                  </Box>
                  <Box sx={{ p: 2 }}>
                    <CodeBlock code={tab.code} language="bash" />
                  </Box>
                </Paper>
              </motion.div>
            </Grid>
          ))}
        </Grid>

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
