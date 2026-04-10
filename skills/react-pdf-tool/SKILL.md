---
name: react-pdf-tool
description:
  "Interactive AI assistant that generates PDF documents using @react-pdf/renderer via
  Anthropic tool use. Provides run_tsx and run_command tools so the model can write,
  execute, and preview React-PDF scripts on demand. Use when you need an autonomous
  PDF-generation agent driven by the AnthropicFoundry client."
---

# React-PDF Tool — Interactive AI PDF Generator

This skill packages the [`react-pdf`](../react-pdf) skill as an **Anthropic tool-use
agent**.  Instead of the model writing code for a human to run, the model itself calls
`run_tsx` and `run_command` tools to install packages, execute TypeScript/JSX, and
preview the generated PDF — all in a single interactive session.

## How It Works

```
User prompt
   │
   ▼
AnthropicFoundry client
   │  system prompt = react-pdf best practices
   │  tools = [run_tsx, run_command]
   ▼
Model decides to call tool
   │
   ├─ run_tsx(code)      → writes .tsx to /tmp, runs `npx tsx`, returns output
   └─ run_command(cmd)   → runs shell command, returns stdout + stderr
   │
   ▼
Tool result sent back to model
   │
   ▼
Model returns final text response to user
```

## Files

- `assets/react_pdf_tool.py` — Ready-to-run Python script implementing the tool loop.

## Prerequisites

**Python packages**

```bash
pip install anthropic
```

**Node / npm** — must be available on `PATH` so `npx tsx` works.

```bash
node --version   # v18+ recommended
npm --version
```

The script auto-installs `@react-pdf/renderer` and `tsx` on first use via
`run_command`.

## Quick Start

```bash
# 1. Set credentials
export ANTHROPIC_API_KEY="<your-key>"
export ANTHROPIC_BASE_URL="<your-foundry-endpoint>"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"   # optional, this is the default

# 2. Run
python skills/react-pdf-tool/assets/react_pdf_tool.py
```

### Example session

```
React-PDF AI assistant  (type 'exit' to quit)

You: Create a one-page invoice PDF for Acme Corp, $1,200 for consulting

[Tool] run_command → {"command": "npm install react @react-pdf/renderer"}
[Tool output]
added 42 packages …

[Tool] run_tsx → {"code": "import React from 'react'; …"}
[Tool output]
PDF saved!

AI: Your invoice has been saved to ./output.pdf.
    It includes the Acme Corp header, line item, and total.
```

## Tool Definitions

### `run_tsx`

Writes the supplied TypeScript/JSX source to a temporary file and executes it with
`npx tsx`.  Returns combined stdout + stderr.

| Field | Value |
|-------|-------|
| Input | `code: string` — full TSX source |
| Timeout | 60 s |

### `run_command`

Runs an arbitrary shell command (via `shell=True`) and returns combined stdout +
stderr.  Used for package installation, file inspection, PDF-to-image conversion, etc.

| Field | Value |
|-------|-------|
| Input | `command: string` — shell command |
| Timeout | 60 s |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | AnthropicFoundry API key |
| `ANTHROPIC_BASE_URL` | ✅ | AnthropicFoundry endpoint URL |
| `ANTHROPIC_MODEL` | ❌ | Model/deployment name (default: `claude-3-5-sonnet-20241022`) |

## Security Note

`run_command` uses `shlex.split()` to tokenize commands safely (no shell expansion).
Run this script only in trusted, isolated environments (containers, VMs, sandboxes).
