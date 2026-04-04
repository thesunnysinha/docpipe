"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import CodeBlock from "./CodeBlock";

const sectionFadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

const strategies = [
  {
    name: "naive",
    title: "Vector Similarity",
    desc: "Standard cosine similarity search. Fast, reliable baseline for well-formed queries.",
    bestFor: "well-formed queries, fast responses",
    borderColor: "#3b82f6",
  },
  {
    name: "hyde",
    title: "Hypothetical Document Embeddings",
    desc: "LLM generates a hypothetical answer first, embeds it, then retrieves real matching docs. Highest accuracy in benchmarks.",
    bestFor: "complex / technical queries",
    borderColor: "#a855f7",
  },
  {
    name: "multi_query",
    title: "Multi-Query Expansion",
    desc: "Expands your query into N variants via LLM, retrieves for each, then deduplicates and ranks results.",
    bestFor: "vague or short queries",
    borderColor: "#f59e0b",
  },
  {
    name: "parent_document",
    title: "Context Window Expansion",
    desc: "Retrieves seed chunks, then expands context by fetching additional chunks from the same source documents.",
    bestFor: "long documents, context coherence",
    borderColor: "#22c55e",
  },
  {
    name: "hybrid",
    title: "Vector + BM25 Keyword",
    desc: "Combines dense vector search with sparse BM25 keyword retrieval via EnsembleRetriever. Best of both worlds.",
    bestFor: "exact terms, proper nouns, IDs",
    borderColor: "#06b6d4",
  },
];

const rerankCode = `rag_cfg = docpipe.RAGConfig(
    ...,
    strategy="naive",
    reranker="flashrank",  # local, no API key
    rerank_top_n=5,
)
# Retrieve top-50, rerank, keep top-5`;

const structuredCode = `class Invoice(BaseModel):
    total: float
    currency: str

result = docpipe.rag(
    "What is the total?",
    config=docpipe.RAGConfig(
        ..., output_model=Invoice
    ),
)
invoice = result.structured
# Invoice(total=4250.0, currency='USD')`;

export default function RAGSection() {
  return (
    <Box component="section" id="rag" sx={{ py: 10 }}>
      <Container maxWidth="lg">
        {/* Title */}
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
            5 Retrieval Strategies — Pick What Fits
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
            Switch strategy with one config field. Mix with reranking and structured output.
          </Typography>
        </motion.div>

        {/* Strategy cards */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {strategies.map((s, i) => (
            <Grid item xs={12} md={6} lg={4} key={s.name}>
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
                    p: 2.5,
                    height: "100%",
                    bgcolor: "#141416",
                    border: "1px solid #2a2a2e",
                    borderLeft: `3px solid ${s.borderColor}`,
                    transition: "border-color 0.2s",
                    "&:hover": { borderColor: "primary.light" },
                  }}
                >
                  <Chip
                    label={s.name}
                    size="small"
                    sx={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: "0.8125rem",
                      fontWeight: 500,
                      bgcolor: "rgba(99,102,241,0.15)",
                      color: "primary.light",
                      mb: 1.5,
                      height: "auto",
                      py: 0.25,
                    }}
                  />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1, fontSize: "0.9375rem" }}>
                    {s.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: "0.8125rem" }}>
                    {s.desc}
                  </Typography>
                  <Typography variant="caption" sx={{ fontSize: "0.75rem" }}>
                    <Box component="span" sx={{ color: "text.secondary", fontWeight: 400 }}>
                      Best for:{" "}
                    </Box>
                    <Box component="span" sx={{ color: "success.main", fontWeight: 500 }}>
                      {s.bestFor}
                    </Box>
                  </Typography>
                </Paper>
              </motion.div>
            </Grid>
          ))}
        </Grid>

        {/* Reranking + Structured output */}
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.4, delay: 0, ease: "easeOut" as const }}
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
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                    📈 Optional Reranking
                  </Typography>
                </Box>
                <Box sx={{ p: 2 }}>
                  <CodeBlock code={rerankCode} language="python" />
                </Box>
              </Paper>
            </motion.div>
          </Grid>
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" as const }}
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
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                    🎯 Structured RAG Output
                  </Typography>
                </Box>
                <Box sx={{ p: 2 }}>
                  <CodeBlock code={structuredCode} language="python" />
                </Box>
              </Paper>
            </motion.div>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
