"use client";

import { useMemo, useState } from "react";
import ScienceIcon from "@mui/icons-material/Science";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Slider from "@mui/material/Slider";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import CodeBlock from "./CodeBlock";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Pipeline = "parse" | "extract" | "ingest" | "rag" | "full";
type LLMProvider = "openai" | "google" | "ollama" | "anthropic";
type EmbProvider = "openai" | "google" | "ollama" | "huggingface";
type Strategy = "naive" | "hyde" | "multi_query" | "parent_document" | "hybrid";
type Reranker = "none" | "flashrank" | "cohere";

interface PlaygroundState {
  pipeline: Pipeline;
  llmProvider: LLMProvider;
  llmModel: string;
  embProvider: EmbProvider;
  embModel: string;
  strategy: Strategy;
  reranker: Reranker;
  topK: number;
  incremental: boolean;
  structuredOutput: boolean;
}

// ---------------------------------------------------------------------------
// Provider / model maps
// ---------------------------------------------------------------------------

const LLM_MODELS: Record<LLMProvider, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
  google: ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
  ollama: ["llama3.2", "llama3.1", "mistral", "phi3"],
  anthropic: ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
};

const EMB_MODELS: Record<EmbProvider, string[]> = {
  openai: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
  google: ["models/text-embedding-004", "models/embedding-001"],
  ollama: ["nomic-embed-text", "mxbai-embed-large", "all-minilm"],
  huggingface: ["BAAI/bge-small-en-v1.5", "BAAI/bge-large-en-v1.5", "sentence-transformers/all-MiniLM-L6-v2"],
};

const LLM_PROVIDER_LABELS: Record<LLMProvider, string> = {
  openai: "OpenAI",
  google: "Google Gemini",
  ollama: "Ollama (local)",
  anthropic: "Anthropic",
};

const EMB_PROVIDER_LABELS: Record<EmbProvider, string> = {
  openai: "OpenAI",
  google: "Google Gemini",
  ollama: "Ollama (local)",
  huggingface: "HuggingFace",
};

const STRATEGY_LABELS: Record<Strategy, string> = {
  naive: "naive — Vector similarity",
  hyde: "hyde — Hypothetical Document Embeddings",
  multi_query: "multi_query — Multi-query expansion",
  parent_document: "parent_document — Context window expansion",
  hybrid: "hybrid — Vector + BM25 keyword",
};

const STRATEGY_TIPS: Record<Strategy, string> = {
  naive: "Fast baseline. Best for well-formed queries.",
  hyde: "LLM generates a hypothetical answer, embeds it, retrieves real docs. Highest accuracy.",
  multi_query: "Expands query into N variants, unions results. Best for vague/short queries.",
  parent_document: "Expands context around seed chunks by source. Best for long documents.",
  hybrid: "Combines dense vector + BM25 keyword search. Best for exact terms, IDs, proper nouns.",
};

// ---------------------------------------------------------------------------
// Code generators (pure functions)
// ---------------------------------------------------------------------------

function generateCode(s: PlaygroundState): string {
  const lines: string[] = ["import docpipe", ""];

  if (s.pipeline === "parse") {
    lines.push(
      "doc = docpipe.parse(",
      '    "invoice.pdf",',
      '    parser="docling",',
      ")",
      "",
      "print(doc.markdown)  # full markdown",
      "print(doc.text)      # plain text",
    );
  } else if (s.pipeline === "extract") {
    lines.push(
      "schema = docpipe.ExtractionSchema(",
      '    description="Extract invoice line items with amounts",',
      `    model_id="${s.llmModel}",`,
      ")",
      "",
      'results = docpipe.extract(doc.text, schema)',
      "for r in results:",
      "    print(r.entity_class, r.text, r.attributes)",
    );
  } else if (s.pipeline === "ingest") {
    lines.push(
      "config = docpipe.IngestionConfig(",
      '    connection_string="postgresql://user:pass@localhost:5432/mydb",',
      '    table_name="docs",',
      `    embedding_provider="${s.embProvider}",`,
      `    embedding_model="${s.embModel}",`,
    );
    if (s.incremental) {
      lines.push("    incremental=True,  # skip unchanged files via SHA-256 hash");
    }
    lines.push(")", "");
    lines.push(
      'result = docpipe.ingest("invoice.pdf", config=config)',
      "print(f\"Ingested {result.chunks_ingested} chunks\")",
    );
    if (s.incremental) {
      lines.push('print(f"Skipped {result.skipped} unchanged files")');
    }
  } else if (s.pipeline === "rag") {
    lines.push(
      "rag_config = docpipe.RAGConfig(",
      '    connection_string="postgresql://user:pass@localhost:5432/mydb",',
      '    table_name="docs",',
      `    embedding_provider="${s.embProvider}",`,
      `    embedding_model="${s.embModel}",`,
      `    llm_provider="${s.llmProvider}",`,
      `    llm_model="${s.llmModel}",`,
      `    strategy="${s.strategy}",`,
    );
    if (s.topK !== 5) {
      lines.push(`    top_k=${s.topK},`);
    }
    if (s.reranker !== "none") {
      lines.push(`    reranker="${s.reranker}",`);
      if (s.topK !== 5) {
        lines.push(`    rerank_top_n=${s.topK},`);
      }
    }
    if (s.structuredOutput) {
      lines.push("    output_model=InvoiceSummary,  # see below");
    }
    lines.push(")", "");
    if (s.structuredOutput) {
      lines.push(
        "from pydantic import BaseModel",
        "",
        "class InvoiceSummary(BaseModel):",
        "    total: float",
        "    currency: str",
        "    vendor: str",
        "",
      );
    }
    lines.push(
      'result = docpipe.rag(',
      '    "What is the total amount on the invoice?",',
      "    config=rag_config,",
      ")",
      "",
      "print(result.answer)   # grounded answer with inline citations",
      'print(result.sources)  # ["invoice.pdf"]',
    );
    if (s.structuredOutput) {
      lines.push(
        "",
        "summary = result.structured",
        "# InvoiceSummary(total=4250.0, currency='USD', vendor='Acme')",
      );
    }
  } else {
    // full pipeline
    lines.push(
      "# Step 1: Parse",
      'doc = docpipe.parse("invoice.pdf")',
      "",
      "# Step 2: Extract structured entities",
      "schema = docpipe.ExtractionSchema(",
      '    description="Extract invoice line items",',
      `    model_id="${s.llmModel}",`,
      ")",
      "",
      "# Step 3: Ingest into vector DB",
      "ingest_config = docpipe.IngestionConfig(",
      '    connection_string="postgresql://user:pass@localhost:5432/mydb",',
      '    table_name="docs",',
      `    embedding_provider="${s.embProvider}",`,
      `    embedding_model="${s.embModel}",`,
    );
    if (s.incremental) {
      lines.push("    incremental=True,");
    }
    lines.push(
      ")",
      "docpipe.ingest(doc, config=ingest_config)",
      "",
      "# Step 4: RAG query",
      "rag_config = docpipe.RAGConfig(",
      '    connection_string="postgresql://user:pass@localhost:5432/mydb",',
      '    table_name="docs",',
      `    embedding_provider="${s.embProvider}",`,
      `    embedding_model="${s.embModel}",`,
      `    llm_provider="${s.llmProvider}",`,
      `    llm_model="${s.llmModel}",`,
      `    strategy="${s.strategy}",`,
      ")",
      'result = docpipe.rag("What is the total?", config=rag_config)',
      "print(result.answer)",
    );
  }

  return lines.join("\n");
}

function generateInstallCmd(s: PlaygroundState): string {
  const extras = new Set<string>();

  if (s.pipeline === "parse" || s.pipeline === "full") {
    extras.add("docling");
  }
  if (s.pipeline === "extract" || s.pipeline === "full") {
    if (s.llmProvider === "openai") extras.add("openai");
    else if (s.llmProvider === "google") extras.add("google");
    else if (s.llmProvider === "ollama") extras.add("ollama");
  }
  if (s.pipeline === "ingest" || s.pipeline === "rag" || s.pipeline === "full") {
    extras.add("pgvector");
    if (s.embProvider === "openai") extras.add("openai");
    else if (s.embProvider === "google") extras.add("google");
    else if (s.embProvider === "ollama") extras.add("ollama");
    else if (s.embProvider === "huggingface") extras.add("huggingface");
  }
  if (s.pipeline === "rag" || s.pipeline === "full") {
    if (s.llmProvider === "openai") extras.add("openai");
    else if (s.llmProvider === "google") extras.add("google");
    else if (s.llmProvider === "ollama") extras.add("ollama");
    else if (s.llmProvider === "anthropic") {
      // anthropic not in official extras yet — just add note
    }
    if (s.strategy === "hybrid") extras.add("rag");
    if (s.reranker === "flashrank") extras.add("rerank");
  }

  if (extras.size === 0) return "pip install docpipe-sdk";
  const sorted = [...extras].sort();
  return `pip install "docpipe-sdk[${sorted.join(",")}]"`;
}

// ---------------------------------------------------------------------------
// Playground Dialog component
// ---------------------------------------------------------------------------

interface PlaygroundProps {
  open: boolean;
  onClose: () => void;
}

const SURFACE = "#141416";
const SURFACE2 = "#1c1c1f";
const BORDER = "#2a2a2e";

export default function Playground({ open, onClose }: PlaygroundProps) {
  const [pipeline, setPipeline] = useState<Pipeline>("rag");
  const [llmProvider, setLlmProvider] = useState<LLMProvider>("openai");
  const [llmModel, setLlmModel] = useState("gpt-4o");
  const [embProvider, setEmbProvider] = useState<EmbProvider>("openai");
  const [embModel, setEmbModel] = useState("text-embedding-3-small");
  const [strategy, setStrategy] = useState<Strategy>("hyde");
  const [reranker, setReranker] = useState<Reranker>("none");
  const [topK, setTopK] = useState(5);
  const [incremental, setIncremental] = useState(false);
  const [structuredOutput, setStructuredOutput] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);
  const [installCopied, setInstallCopied] = useState(false);

  const state: PlaygroundState = {
    pipeline, llmProvider, llmModel, embProvider, embModel,
    strategy, reranker, topK, incremental, structuredOutput,
  };

  const generatedCode = useMemo(() => generateCode(state), [
    pipeline, llmProvider, llmModel, embProvider, embModel,
    strategy, reranker, topK, incremental, structuredOutput,
  ]);

  const installCmd = useMemo(() => generateInstallCmd(state), [
    pipeline, llmProvider, embProvider, strategy, reranker, incremental,
  ]);

  const showLLM = pipeline === "extract" || pipeline === "rag" || pipeline === "full";
  const showEmb = pipeline === "ingest" || pipeline === "rag" || pipeline === "full";
  const showStrategy = pipeline === "rag" || pipeline === "full";
  const showIncremental = pipeline === "ingest" || pipeline === "full";
  const showStructured = pipeline === "rag";

  function handleLLMProviderChange(p: LLMProvider) {
    setLlmProvider(p);
    setLlmModel(LLM_MODELS[p][0]);
  }

  function handleEmbProviderChange(p: EmbProvider) {
    setEmbProvider(p);
    setEmbModel(EMB_MODELS[p][0]);
  }

  async function handleCopyCode() {
    await navigator.clipboard.writeText(generatedCode);
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 2000);
  }

  async function handleCopyInstall() {
    await navigator.clipboard.writeText(installCmd);
    setInstallCopied(true);
    setTimeout(() => setInstallCopied(false), 2000);
  }

  const selectSx = {
    bgcolor: SURFACE2,
    "& .MuiOutlinedInput-notchedOutline": { borderColor: BORDER },
    "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#818cf8" },
    "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: "#6366f1" },
    color: "text.primary",
    fontSize: "0.875rem",
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      PaperProps={{
        sx: {
          bgcolor: SURFACE,
          border: `1px solid ${BORDER}`,
          borderRadius: 3,
          backgroundImage: "none",
          minHeight: "70vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          bgcolor: SURFACE2,
          borderBottom: `1px solid ${BORDER}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          py: 1.5,
          px: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography fontWeight={700} fontSize="1rem">
            doc<Box component="span" sx={{ color: "primary.light" }}>pipe</Box> Playground
          </Typography>
          <Chip
            label="zero backend"
            size="small"
            sx={{ bgcolor: "rgba(34,197,94,0.12)", color: "success.main", fontSize: "0.7rem", height: 20 }}
          />
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0, display: "flex", flexDirection: { xs: "column", md: "row" } }}>
        {/* ─── Left panel: controls ─── */}
        <Box
          sx={{
            width: { xs: "100%", md: 300 },
            flexShrink: 0,
            borderRight: { md: `1px solid ${BORDER}` },
            borderBottom: { xs: `1px solid ${BORDER}`, md: "none" },
            p: 2.5,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 2.5,
          }}
        >
          {/* Pipeline type */}
          <FormControl fullWidth size="small">
            <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>Pipeline Type</InputLabel>
            <Select
              value={pipeline}
              label="Pipeline Type"
              onChange={(e) => setPipeline(e.target.value as Pipeline)}
              sx={selectSx}
            >
              <MenuItem value="parse">Parse</MenuItem>
              <MenuItem value="extract">Extract</MenuItem>
              <MenuItem value="ingest">Ingest</MenuItem>
              <MenuItem value="rag">RAG Query</MenuItem>
              <MenuItem value="full">Full Pipeline</MenuItem>
            </Select>
          </FormControl>

          {/* LLM Provider */}
          {showLLM && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>LLM Provider</InputLabel>
              <Select
                value={llmProvider}
                label="LLM Provider"
                onChange={(e) => handleLLMProviderChange(e.target.value as LLMProvider)}
                sx={selectSx}
              >
                {(Object.keys(LLM_PROVIDER_LABELS) as LLMProvider[]).map((p) => (
                  <MenuItem key={p} value={p}>{LLM_PROVIDER_LABELS[p]}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* LLM Model */}
          {showLLM && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>LLM Model</InputLabel>
              <Select
                value={llmModel}
                label="LLM Model"
                onChange={(e) => setLlmModel(e.target.value)}
                sx={selectSx}
              >
                {LLM_MODELS[llmProvider].map((m) => (
                  <MenuItem key={m} value={m} sx={{ fontSize: "0.8rem" }}>{m}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Embedding Provider */}
          {showEmb && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>Embedding Provider</InputLabel>
              <Select
                value={embProvider}
                label="Embedding Provider"
                onChange={(e) => handleEmbProviderChange(e.target.value as EmbProvider)}
                sx={selectSx}
              >
                {(Object.keys(EMB_PROVIDER_LABELS) as EmbProvider[]).map((p) => (
                  <MenuItem key={p} value={p}>{EMB_PROVIDER_LABELS[p]}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Embedding Model */}
          {showEmb && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>Embedding Model</InputLabel>
              <Select
                value={embModel}
                label="Embedding Model"
                onChange={(e) => setEmbModel(e.target.value)}
                sx={selectSx}
              >
                {EMB_MODELS[embProvider].map((m) => (
                  <MenuItem key={m} value={m} sx={{ fontSize: "0.75rem" }}>{m}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Strategy */}
          {showStrategy && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>RAG Strategy</InputLabel>
              <Select
                value={strategy}
                label="RAG Strategy"
                onChange={(e) => setStrategy(e.target.value as Strategy)}
                sx={selectSx}
              >
                {(Object.keys(STRATEGY_LABELS) as Strategy[]).map((s) => (
                  <Tooltip key={s} title={STRATEGY_TIPS[s]} placement="right" arrow>
                    <MenuItem value={s} sx={{ fontSize: "0.8rem" }}>{STRATEGY_LABELS[s]}</MenuItem>
                  </Tooltip>
                ))}
              </Select>
            </FormControl>
          )}

          {/* Incremental toggle */}
          {showIncremental && (
            <FormControlLabel
              control={
                <Switch
                  checked={incremental}
                  onChange={(e) => setIncremental(e.target.checked)}
                  size="small"
                  sx={{ "& .MuiSwitch-track": { bgcolor: "#2a2a2e" } }}
                />
              }
              label={
                <Typography variant="caption" color="text.secondary">
                  Incremental ingestion (skip unchanged)
                </Typography>
              }
            />
          )}

          {/* Structured output toggle */}
          {showStructured && (
            <FormControlLabel
              control={
                <Switch
                  checked={structuredOutput}
                  onChange={(e) => setStructuredOutput(e.target.checked)}
                  size="small"
                  sx={{ "& .MuiSwitch-track": { bgcolor: "#2a2a2e" } }}
                />
              }
              label={
                <Typography variant="caption" color="text.secondary">
                  Structured output (Pydantic model)
                </Typography>
              }
            />
          )}

          {/* Advanced section */}
          <Accordion
            expanded={advancedOpen}
            onChange={() => setAdvancedOpen(!advancedOpen)}
            elevation={0}
            sx={{
              bgcolor: "transparent",
              border: `1px solid ${BORDER}`,
              borderRadius: "8px !important",
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem", color: "text.secondary" }} />} sx={{ minHeight: 40, py: 0 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={600}>
                Advanced Options
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0, display: "flex", flexDirection: "column", gap: 2 }}>
              {/* top_k slider */}
              <Box>
                <Typography variant="caption" color="text.secondary">
                  top_k: {topK}
                </Typography>
                <Slider
                  value={topK}
                  onChange={(_, v) => setTopK(v as number)}
                  min={1}
                  max={20}
                  step={1}
                  size="small"
                  sx={{ color: "primary.main", mt: 0.5 }}
                />
              </Box>

              {/* Reranker */}
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: "text.secondary", fontSize: "0.8rem" }}>Reranker</InputLabel>
                <Select
                  value={reranker}
                  label="Reranker"
                  onChange={(e) => setReranker(e.target.value as Reranker)}
                  sx={selectSx}
                >
                  <MenuItem value="none">None</MenuItem>
                  <MenuItem value="flashrank">FlashRank (local, no API key)</MenuItem>
                  <MenuItem value="cohere">Cohere (cloud API)</MenuItem>
                </Select>
              </FormControl>
            </AccordionDetails>
          </Accordion>
        </Box>

        {/* ─── Right panel: generated code ─── */}
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            overflow: "hidden",
          }}
        >
          {/* Code panel header */}
          <Box
            sx={{
              bgcolor: SURFACE2,
              borderBottom: `1px solid ${BORDER}`,
              px: 2.5,
              py: 1.25,
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Box sx={{ display: "flex", gap: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#ff5f56" }} />
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#ffbd2e" }} />
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#27c93f" }} />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5, fontFamily: "JetBrains Mono, monospace" }}>
              generated_code.py
            </Typography>
          </Box>

          {/* Code block */}
          <Box sx={{ flex: 1, overflowY: "auto", p: 0 }}>
            <CodeBlock code={generatedCode} language="python" showCopy={false} />
          </Box>

          {/* Bottom bar: install command + action buttons */}
          <Box
            sx={{
              borderTop: `1px solid ${BORDER}`,
              bgcolor: SURFACE2,
              px: 2.5,
              py: 1.5,
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              flexWrap: "wrap",
            }}
          >
            {/* Install command pill */}
            <Box
              sx={{
                flex: 1,
                minWidth: 0,
                bgcolor: "#0a0a0b",
                border: `1px solid ${BORDER}`,
                borderRadius: 1.5,
                px: 1.5,
                py: 0.75,
                display: "flex",
                alignItems: "center",
                gap: 1,
                overflow: "hidden",
              }}
            >
              <Typography
                component="code"
                sx={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: "0.75rem",
                  color: "#22c55e",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {installCmd}
              </Typography>
            </Box>

            <Button
              variant="outlined"
              size="small"
              startIcon={installCopied ? <CheckIcon /> : <ContentCopyIcon />}
              onClick={handleCopyInstall}
              sx={{
                borderColor: BORDER,
                color: installCopied ? "success.main" : "text.secondary",
                whiteSpace: "nowrap",
                fontSize: "0.75rem",
                "&:hover": { borderColor: "primary.light" },
              }}
            >
              {installCopied ? "Copied!" : "Copy Install"}
            </Button>

            <Button
              variant="contained"
              size="small"
              startIcon={codeCopied ? <CheckIcon /> : <ContentCopyIcon />}
              onClick={handleCopyCode}
              sx={{
                background: codeCopied ? "#22c55e" : "linear-gradient(135deg, #6366f1, #4f46e5)",
                boxShadow: "none",
                whiteSpace: "nowrap",
                fontSize: "0.75rem",
              }}
            >
              {codeCopied ? "Copied!" : "Copy Code"}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Self-contained trigger button (manages its own open state)
// ---------------------------------------------------------------------------

interface PlaygroundButtonProps {
  variant?: "nav" | "hero";
}

export function PlaygroundButton({ variant = "hero" }: PlaygroundButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        startIcon={<ScienceIcon />}
        variant={variant === "hero" ? "outlined" : "text"}
        size={variant === "hero" ? "large" : "medium"}
        sx={
          variant === "hero"
            ? {
                px: 3,
                borderColor: "#2a2a2e",
                color: "text.primary",
                bgcolor: "#1c1c1f",
                "&:hover": { borderColor: "primary.light", bgcolor: "#141416" },
              }
            : {
                color: "primary.light",
                fontSize: "0.875rem",
                px: 1.5,
                fontWeight: 600,
                "&:hover": { bgcolor: "rgba(99,102,241,0.08)" },
              }
        }
      >
        Playground
      </Button>
      <Playground open={open} onClose={() => setOpen(false)} />
    </>
  );
}
