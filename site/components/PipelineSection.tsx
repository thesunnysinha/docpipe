"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
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

const pipelineSteps = [
  { icon: "📄", label: "Documents", sub: "PDF, DOCX, images...", color: "#a1a1aa" },
  { icon: "🔍", label: "Parse", sub: "Docling", color: "#3b82f6" },
  { icon: "⚡", label: "Extract", sub: "LangExtract / LangChain", color: "#f59e0b" },
  { icon: "🗃", label: "Ingest", sub: "pgvector + your DB", color: "#22c55e" },
  { icon: "🤖", label: "RAG Query", sub: "5 strategies", color: "#818cf8" },
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
    <Box component="section" id="pipelines" sx={{ py: 12 }}>
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
            sx={{ textAlign: "center", mb: 8, maxWidth: 540, mx: "auto" }}
          >
            Use each independently or chain them together. Your data, your DB, your LLM.
          </Typography>
        </motion.div>

        {/* Pipeline Stepper flow */}
        <Box sx={{ mb: 8, overflowX: "auto", pb: 1 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "center",
              minWidth: 600,
            }}
          >
            {pipelineSteps.map((step, i) => (
              <Box key={i} sx={{ display: "flex", alignItems: "flex-start", flex: i < pipelineSteps.length - 1 ? "1 1 auto" : "0 0 auto" }}>
                {/* Step column */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.4, delay: i * 0.15, ease: "easeOut" as const }}
                >
                  <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 90 }}>
                    {/* Numbered circle */}
                    <Box sx={{
                      width: 44, height: 44, borderRadius: "50%",
                      border: "2px solid", borderColor: step.color,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      bgcolor: `${step.color}18`,
                      fontSize: "1.25rem",
                      mb: 1.5,
                      boxShadow: `0 0 16px ${step.color}33`,
                    }}>
                      {step.icon}
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 700, fontSize: "0.8125rem", textAlign: "center", color: "text.primary" }}>
                      {step.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6875rem", textAlign: "center", mt: 0.25 }}>
                      {step.sub}
                    </Typography>
                  </Box>
                </motion.div>

                {/* Connector line */}
                {i < pipelineSteps.length - 1 && (
                  <motion.div
                    style={{ flex: 1 }}
                    initial={{ opacity: 0, scaleX: 0 }}
                    whileInView={{ opacity: 1, scaleX: 1 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.4, delay: i * 0.15 + 0.2 }}
                  >
                    <Box sx={{
                      height: 2,
                      background: `linear-gradient(90deg, ${step.color}, ${pipelineSteps[i + 1].color})`,
                      mt: "21px",
                      mx: 1,
                      opacity: 0.5,
                      borderRadius: 1,
                    }} />
                  </motion.div>
                )}
              </Box>
            ))}
          </Box>
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
                <Card
                  elevation={0}
                  sx={{
                    height: "100%",
                    bgcolor: "#141416",
                    border: "1px solid #2a2a2e",
                    borderTop: `3px solid ${uc.dotColor}`,
                    transition: "transform 0.2s, box-shadow 0.2s",
                    "&:hover": {
                      transform: "translateY(-4px)",
                      boxShadow: `0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px ${uc.dotColor}33`,
                    },
                  }}
                >
                  <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, fontSize: "0.9375rem", mb: 1 }}>
                      {uc.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: "0.8125rem" }}>
                      {uc.desc}
                    </Typography>
                    <CodeBlock code={uc.code} language="python" />
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
