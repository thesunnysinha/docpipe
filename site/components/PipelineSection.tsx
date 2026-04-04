"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import CodeBlock from "./CodeBlock";

const sectionFadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

const pipelineSteps = [
  { icon: "📄", label: "Documents", sub: "PDF, DOCX, images...", borderColor: "#2a2a2e" },
  { icon: "🔍", label: "Parse", sub: "Docling", borderColor: "#3b82f6" },
  { icon: "⚡", label: "Extract", sub: "LangExtract / LangChain", borderColor: "#f59e0b" },
  { icon: "🗃", label: "Ingest", sub: "pgvector + your DB", borderColor: "#22c55e" },
  { icon: "🤖", label: "RAG Query", sub: "5 strategies", borderColor: "#818cf8" },
];

const useCases = [
  {
    dotColor: "#3b82f6",
    title: "1. Parse Only (Docling)",
    desc: "Convert any document to clean text or markdown.",
    code: `import docpipe

doc = docpipe.parse("report.pdf")
print(doc.markdown)`,
  },
  {
    dotColor: "#f59e0b",
    title: "2. Extract Only (LangExtract)",
    desc: "Extract structured entities from any text with LLMs.",
    code: `schema = docpipe.ExtractionSchema(
    description="Extract people and ages",
    model_id="gemini-2.5-flash",
)
results = docpipe.extract(text, schema)`,
  },
  {
    dotColor: "#ec4899",
    title: "3. Parse + Extract",
    desc: "Full pipeline: document to structured data in one call.",
    code: `result = docpipe.run(
    "invoice.pdf", schema
)
print(result.extractions)`,
  },
  {
    dotColor: "#22c55e",
    title: "4. Parse + Ingest",
    desc: "Parse a document and ingest vectors into your DB.",
    code: `config = docpipe.IngestionConfig(
    connection_string="postgresql://...",
    table_name="docs",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
)
docpipe.ingest("report.pdf", config=config)`,
  },
  {
    dotColor: "#06b6d4",
    title: "5. Full Pipeline",
    desc: "Parse, extract, and ingest - all in one call.",
    code: `result = docpipe.run(
    "contract.pdf", schema,
    ingestion_config=config,
)`,
  },
  {
    dotColor: "#818cf8",
    title: "6. RAG Query",
    desc: "Ask questions against your ingested documents with grounded answers and source citations.",
    code: `rag_cfg = docpipe.RAGConfig(
    connection_string="postgresql://...",
    table_name="docs",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
    llm_provider="openai",
    llm_model="gpt-4o",
    strategy="hyde",
)
result = docpipe.rag(
    "What is the invoice total?",
    config=rag_cfg,
)
print(result.answer)   # grounded answer with citations
print(result.sources)  # ["invoice.pdf"]`,
  },
];

export default function PipelineSection() {
  return (
    <Box component="section" id="pipelines" sx={{ py: 10 }}>
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
            Four Pipelines, Fully Composable
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
            Use each independently or chain them together. Your data, your DB, your LLM.
          </Typography>
        </motion.div>

        {/* Pipeline flow */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 1.5,
            mb: 8,
          }}
        >
          {pipelineSteps.map((step, i) => (
            <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.4, delay: i * 0.12, ease: "easeOut" as const }}
                whileHover={{ scale: 1.05 }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    textAlign: "center",
                    minWidth: 120,
                    bgcolor: "#141416",
                    border: `1px solid ${step.borderColor}`,
                    transition: "transform 0.2s",
                    cursor: "default",
                  }}
                >
                  <Typography sx={{ fontSize: "1.375rem", mb: 0.5 }}>
                    {step.icon}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                    {step.label}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6875rem" }}>
                    {step.sub}
                  </Typography>
                </Paper>
              </motion.div>
              {i < pipelineSteps.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.3, delay: i * 0.12 + 0.2 }}
                >
                  <ArrowForwardIosIcon
                    sx={{
                      color: "text.secondary",
                      fontSize: 18,
                      display: { xs: "none", sm: "block" },
                    }}
                  />
                </motion.div>
              )}
            </Box>
          ))}
        </Box>

        {/* Use case cards */}
        <Grid container spacing={2}>
          {useCases.map((uc, i) => (
            <Grid item xs={12} md={6} lg={4} key={i}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.4, delay: i * 0.05, ease: "easeOut" as const }}
                style={{ height: "100%" }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    height: "100%",
                    bgcolor: "#141416",
                    border: "1px solid #2a2a2e",
                    transition: "border-color 0.2s",
                    "&:hover": { borderColor: "primary.main" },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, mb: 1.5 }}>
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        bgcolor: uc.dotColor,
                        flexShrink: 0,
                      }}
                    />
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, fontSize: "0.9375rem" }}>
                      {uc.title}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: "0.8125rem" }}>
                    {uc.desc}
                  </Typography>
                  <CodeBlock code={uc.code} language="python" />
                </Paper>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
