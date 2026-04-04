"use client";

import { motion, type Variants } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import ExtensionRoundedIcon from "@mui/icons-material/ExtensionRounded";
import RocketLaunchRoundedIcon from "@mui/icons-material/RocketLaunchRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import LinkRoundedIcon from "@mui/icons-material/LinkRounded";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import AssessmentRoundedIcon from "@mui/icons-material/AssessmentRounded";
import LockOpenRoundedIcon from "@mui/icons-material/LockOpenRounded";

const sectionFadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

const features = [
  {
    Icon: ExtensionRoundedIcon,
    title: "Plugin Architecture",
    desc: "Add custom parsers and extractors via Python entry points. Third-party packages auto-discovered on install.",
    iconBg: "rgba(99,102,241,0.15)",
    iconColor: "#818cf8",
    iconGlow: "rgba(99,102,241,0.25)",
  },
  {
    Icon: RocketLaunchRoundedIcon,
    title: "CLI + API Server",
    desc: "Full CLI for scripting, FastAPI server for microservices, Docker image for deployment.",
    iconBg: "rgba(34,197,94,0.15)",
    iconColor: "#22c55e",
    iconGlow: "rgba(34,197,94,0.25)",
  },
  {
    Icon: SettingsRoundedIcon,
    title: "Fully Configurable",
    desc: "No magic defaults. Explicit LLM provider, embedding model, and DB connection. YAML + env vars.",
    iconBg: "rgba(245,158,11,0.15)",
    iconColor: "#f59e0b",
    iconGlow: "rgba(245,158,11,0.25)",
  },
  {
    Icon: LinkRoundedIcon,
    title: "LangChain Backbone",
    desc: "Built on LangChain for embeddings, text splitting, and vector stores. Supports OpenAI, Gemini, Ollama, HuggingFace.",
    iconBg: "rgba(236,72,153,0.15)",
    iconColor: "#ec4899",
    iconGlow: "rgba(236,72,153,0.25)",
  },
  {
    Icon: DescriptionRoundedIcon,
    title: "20+ Document Formats",
    desc: "PDF, DOCX, XLSX, PPTX, HTML, images, audio, video - powered by IBM Docling's advanced parsing.",
    iconBg: "rgba(6,182,212,0.15)",
    iconColor: "#06b6d4",
    iconGlow: "rgba(6,182,212,0.25)",
  },
  {
    Icon: SmartToyRoundedIcon,
    title: "5 RAG Strategies",
    desc: "naive, HyDE, multi-query, parent-document, hybrid — swap with one config field. Add reranking optionally.",
    iconBg: "rgba(168,85,247,0.15)",
    iconColor: "#a855f7",
    iconGlow: "rgba(168,85,247,0.25)",
  },
  {
    Icon: AssessmentRoundedIcon,
    title: "Built-in Evaluation",
    desc: "Measure hit rate, MRR, faithfulness, and answer similarity. Know if your RAG is actually working.",
    iconBg: "rgba(34,197,94,0.15)",
    iconColor: "#22c55e",
    iconGlow: "rgba(34,197,94,0.25)",
  },
  {
    Icon: LockOpenRoundedIcon,
    title: "Zero Vendor Lock-in",
    desc: "docpipe never stores your data. It connects to your DB, calls your LLM API, then gets out of the way.",
    iconBg: "rgba(59,130,246,0.15)",
    iconColor: "#3b82f6",
    iconGlow: "rgba(59,130,246,0.25)",
  },
];

export default function FeaturesSection() {
  return (
    <Box
      component="section"
      id="features"
      sx={{
        py: 12,
        background: "linear-gradient(180deg, rgba(99,102,241,0.03) 0%, transparent 100%)",
      }}
    >
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
            Built for Production
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
            Everything you need to go from raw documents to grounded answers at scale.
          </Typography>
        </motion.div>

        <Grid container spacing={2}>
          {features.map((f, i) => (
            <Grid item xs={12} sm={6} lg={3} key={i}>
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
                    p: 0,
                    height: "100%",
                    bgcolor: "rgba(20, 20, 22, 0.8)",
                    backdropFilter: "blur(12px)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 3,
                    transition: "transform 0.2s, border-color 0.2s, box-shadow 0.2s",
                    "&:hover": {
                      transform: "translateY(-4px)",
                      borderColor: "rgba(99,102,241,0.3)",
                      boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                    },
                  }}
                >
                  <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        bgcolor: f.iconBg,
                        boxShadow: `0 0 20px ${f.iconGlow}`,
                        mb: 2,
                      }}
                    >
                      <f.Icon sx={{ fontSize: 22, color: f.iconColor }} />
                    </Box>
                    <Typography
                      variant="subtitle1"
                      sx={{ fontWeight: 700, mb: 1, fontSize: "0.9375rem" }}
                    >
                      {f.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ fontSize: "0.8125rem", lineHeight: 1.65 }}
                    >
                      {f.desc}
                    </Typography>
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
