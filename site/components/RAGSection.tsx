"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
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
    color: "#3b82f6",
  },
  {
    name: "hyde",
    title: "Hypothetical Document Embeddings",
    desc: "LLM generates a hypothetical answer first, embeds it, then retrieves real matching docs. Highest accuracy in benchmarks.",
    bestFor: "complex / technical queries",
    color: "#a855f7",
  },
  {
    name: "multi_query",
    title: "Multi-Query Expansion",
    desc: "Expands your query into N variants via LLM, retrieves for each, then deduplicates and ranks results.",
    bestFor: "vague or short queries",
    color: "#f59e0b",
  },
  {
    name: "parent_document",
    title: "Context Window Expansion",
    desc: "Retrieves seed chunks, then expands context by fetching additional chunks from the same source documents.",
    bestFor: "long documents, context coherence",
    color: "#22c55e",
  },
  {
    name: "hybrid",
    title: "Vector + BM25 Keyword",
    desc: "Combines dense vector search with sparse BM25 keyword retrieval via EnsembleRetriever. Best of both worlds.",
    bestFor: "exact terms, proper nouns, IDs",
    color: "#06b6d4",
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
    <Box component="section" id="rag" sx={{ py: 12, background: "linear-gradient(180deg, rgba(99,102,241,0.02) 0%, transparent 100%)" }}>
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
            sx={{ fontWeight: 800, textAlign: "center", mb: 1.5, fontSize: { xs: "1.75rem", md: "2.25rem" }, letterSpacing: "-0.02em" }}
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
            sx={{ textAlign: "center", mb: 8, maxWidth: 540, mx: "auto" }}
          >
            Switch strategy with one config field. Mix with reranking and structured output.
          </Typography>
        </motion.div>

        {/* Strategy accordion */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" as const }}
        >
          <Box sx={{ mb: 4 }}>
            {strategies.map((s, i) => (
              <Accordion
                key={s.name}
                defaultExpanded={i === 1}
                disableGutters
                sx={{
                  bgcolor: "#141416",
                  border: "1px solid #2a2a2e",
                  borderLeft: `4px solid ${s.color}`,
                  mb: 1,
                  borderRadius: "8px !important",
                  overflow: "hidden",
                  "&:before": { display: "none" },
                  "&.Mui-expanded": {
                    boxShadow: `0 0 0 1px ${s.color}33, 0 4px 20px rgba(0,0,0,0.3)`,
                  },
                  transition: "box-shadow 0.2s",
                }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon sx={{ color: "text.secondary" }} />}
                  sx={{ py: 0.5 }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", width: "100%" }}>
                    <Chip
                      label={s.name}
                      size="small"
                      sx={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: "0.8125rem",
                        bgcolor: `${s.color}22`,
                        color: s.color,
                        border: "none",
                        height: "auto",
                        py: 0.25,
                      }}
                    />
                    <Typography fontWeight={600} sx={{ fontSize: "0.9375rem" }}>
                      {s.title}
                    </Typography>
                    <Chip
                      label={`Best for: ${s.bestFor}`}
                      size="small"
                      variant="outlined"
                      sx={{
                        color: "success.main",
                        borderColor: "success.main",
                        ml: { xs: 0, sm: "auto" },
                        fontSize: "0.75rem",
                        height: "auto",
                        py: 0.25,
                        display: { xs: "none", sm: "flex" },
                      }}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ pt: 0, pb: 2, borderTop: "1px solid #2a2a2e" }}>
                  <Typography color="text.secondary" sx={{ fontSize: "0.875rem", pt: 1.5 }}>
                    {s.desc}
                  </Typography>
                  <Typography variant="caption" sx={{ display: "block", mt: 1 }}>
                    <Box component="span" sx={{ color: "text.secondary" }}>Best for: </Box>
                    <Box component="span" sx={{ color: "success.main", fontWeight: 500 }}>{s.bestFor}</Box>
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        </motion.div>

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
