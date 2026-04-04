"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";

interface CodeBlockProps {
  code: string;
  language?: string;
  showCopy?: boolean;
}

export default function CodeBlock({
  code,
  language = "python",
  showCopy = true,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box
      sx={{
        position: "relative",
        "&:hover .copy-btn": { opacity: 1 },
      }}
    >
      {showCopy && (
        <IconButton
          className="copy-btn"
          onClick={handleCopy}
          size="small"
          title={copied ? "Copied!" : "Copy code"}
          sx={{
            position: "absolute",
            top: 6,
            right: 6,
            zIndex: 10,
            opacity: 0,
            transition: "opacity 0.2s",
            bgcolor: "#1c1c1f",
            border: "1px solid #2a2a2e",
            color: copied ? "success.main" : "text.secondary",
            "&:hover": {
              bgcolor: "#2a2a2e",
              borderColor: "primary.main",
            },
            width: 28,
            height: 28,
          }}
        >
          {copied ? (
            <CheckIcon sx={{ fontSize: 14 }} />
          ) : (
            <ContentCopyIcon sx={{ fontSize: 14 }} />
          )}
        </IconButton>
      )}
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          borderRadius: "6px",
          background: "#0a0a0b",
          fontSize: "12px",
          lineHeight: "1.7",
          padding: "12px",
        }}
        codeTagProps={{
          style: { fontFamily: "'JetBrains Mono', monospace" },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </Box>
  );
}
