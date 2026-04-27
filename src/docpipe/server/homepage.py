"""Homepage HTML for the docpipe web UI."""

from __future__ import annotations


def render_homepage(version: str, parsers: list[str], extractors: list[str]) -> str:
    parser_items = "".join(
        f'<div class="chip">{p}</div>' for p in parsers
    )
    extractor_items = "".join(
        f'<div class="chip">{e}</div>' for e in extractors
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>docpipe</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #0a0914;
      --surface:   rgba(255,255,255,0.06);
      --surfaceHi: rgba(255,255,255,0.10);
      --border:    rgba(255,255,255,0.10);
      --borderHi:  rgba(255,255,255,0.20);
      --primary:   #6366f1;
      --glow:      rgba(99,102,241,0.25);
      --accent:    #22d3ee;
      --text:      #f1f5f9;
      --textSub:   #94a3b8;
      --textMuted: #475569;
      --success:   #10b981;
      --radius:    14px;
      --font:      system-ui, -apple-system, "Segoe UI", sans-serif;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Ambient blobs */
    .bg-blobs {{
      position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden;
    }}
    .blob {{
      position: absolute;
      border-radius: 50%;
      filter: blur(120px);
      opacity: 0.15;
    }}
    .blob-1 {{ width: 600px; height: 600px; top: -200px; left: -150px; background: var(--primary); }}
    .blob-2 {{ width: 500px; height: 500px; bottom: -150px; right: -100px; background: #8b5cf6; }}
    .blob-3 {{ width: 400px; height: 400px; top: 40%; left: 55%; background: var(--accent); opacity: 0.08; }}

    /* Layout */
    .page {{ position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 40px 24px 80px; width: 100%; }}

    /* Header */
    .header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 48px; }}
    .logo {{
      width: 48px; height: 48px; border-radius: 12px;
      background: linear-gradient(135deg, var(--primary), #8b5cf6);
      display: flex; align-items: center; justify-content: center;
      font-size: 22px; font-weight: 700; color: #fff;
      box-shadow: 0 0 24px var(--glow);
    }}
    .brand {{ display: flex; flex-direction: column; }}
    .brand-name {{ font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
    .brand-version {{ font-size: 12px; color: var(--textMuted); margin-top: 2px; }}

    .status-dot {{
      margin-left: auto; display: flex; align-items: center; gap: 8px;
      font-size: 13px; color: var(--success);
    }}
    .dot {{
      width: 8px; height: 8px; border-radius: 50%; background: var(--success);
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:0.4 }} }}

    /* Cards */
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
    .grid-1 {{ grid-template-columns: 1fr; }}
    @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}

    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      backdrop-filter: blur(20px);
      transition: border-color .2s, box-shadow .2s;
    }}
    .card:hover {{ border-color: var(--borderHi); box-shadow: 0 8px 32px rgba(0,0,0,.3); }}
    .card-title {{
      font-size: 11px; font-weight: 600; letter-spacing: 1px;
      text-transform: uppercase; color: var(--textMuted); margin-bottom: 16px;
    }}

    /* Chips */
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{
      background: rgba(99,102,241,0.12);
      border: 1px solid rgba(99,102,241,0.25);
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 13px; color: var(--primary);
      font-weight: 500;
    }}

    /* Links */
    .link-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
    .link-card {{
      display: flex; align-items: center; gap: 12px;
      background: var(--surfaceHi);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      text-decoration: none; color: var(--text);
      transition: background .2s, border-color .2s, transform .15s;
    }}
    .link-card:hover {{
      background: rgba(99,102,241,0.12);
      border-color: rgba(99,102,241,0.35);
      transform: translateY(-1px);
    }}
    .link-icon {{ font-size: 20px; }}
    .link-text {{ display: flex; flex-direction: column; }}
    .link-label {{ font-size: 14px; font-weight: 600; }}
    .link-desc {{ font-size: 12px; color: var(--textSub); margin-top: 2px; }}

    /* Code block */
    .code-block {{
      background: rgba(0,0,0,0.4);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 12px;
      color: var(--accent);
      overflow-x: auto;
      line-height: 1.7;
    }}
    .code-comment {{ color: var(--textMuted); }}

    /* Footer */
    .footer {{ margin-top: 64px; text-align: center; font-size: 12px; color: var(--textMuted); }}
    .footer a {{ color: var(--textSub); }}
  </style>
</head>
<body>
  <div class="bg-blobs">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
  </div>

  <div class="page">

    <header class="header">
      <div class="logo">D</div>
      <div class="brand">
        <div class="brand-name">docpipe</div>
        <div class="brand-version">v{version}</div>
      </div>
      <div class="status-dot">
        <div class="dot"></div>
        running
      </div>
    </header>

    <!-- Plugins -->
    <div class="grid" style="margin-bottom:16px">
      <div class="card">
        <div class="card-title">Parsers</div>
        <div class="chips">{parser_items}</div>
      </div>
      <div class="card">
        <div class="card-title">Extractors</div>
        <div class="chips">{extractor_items}</div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-title">Quick Access</div>
      <div class="link-grid">
        <a class="link-card" href="/docs">
          <span class="link-icon">📖</span>
          <div class="link-text">
            <span class="link-label">Swagger UI</span>
            <span class="link-desc">Interactive API explorer</span>
          </div>
        </a>
        <a class="link-card" href="/redoc">
          <span class="link-icon">📋</span>
          <div class="link-text">
            <span class="link-label">ReDoc</span>
            <span class="link-desc">Full API reference</span>
          </div>
        </a>
        <a class="link-card" href="/health">
          <span class="link-icon">🩺</span>
          <div class="link-text">
            <span class="link-label">Health</span>
            <span class="link-desc">Server health JSON</span>
          </div>
        </a>
        <a class="link-card" href="/openapi.json">
          <span class="link-icon">⚙️</span>
          <div class="link-text">
            <span class="link-label">OpenAPI JSON</span>
            <span class="link-desc">Machine-readable spec</span>
          </div>
        </a>
      </div>
    </div>

    <!-- Example -->
    <div class="card">
      <div class="card-title">Quick Start</div>
      <pre class="code-block"><span class="code-comment"># Ingest a document</span>
curl -u admin:docpipe -X POST http://localhost:8000/ingest \\
  -H "Content-Type: application/json" \\
  -d '{{
    "source": "https://example.com/document.pdf",
    "connection_string": "postgresql://user:pass@db:5432/mydb",
    "table_name": "my_docs",
    "embedding_provider": "google",
    "embedding_model": "models/embedding-001",
    "api_key": "YOUR_API_KEY"
  }}'

<span class="code-comment"># RAG query</span>
curl -u admin:docpipe -X POST http://localhost:8000/rag/query \\
  -H "Content-Type: application/json" \\
  -d '{{
    "question": "What is this document about?",
    "connection_string": "postgresql://user:pass@db:5432/mydb",
    "table_name": "my_docs",
    "embedding_provider": "google",
    "embedding_model": "models/embedding-001",
    "llm_provider": "google",
    "llm_model": "gemini-2.0-flash",
    "api_key": "YOUR_API_KEY"
  }}'</pre>
    </div>

    <div class="footer">
      docpipe &mdash; open-source document processing &amp; RAG &mdash;
      <a href="https://github.com/thesunnysinha/docpipe" target="_blank">GitHub</a>
    </div>

  </div>
</body>
</html>"""
