"""
Interactive AI assistant that generates PDF documents via React-PDF.

The model uses a `run_tsx` tool to execute TypeScript/JSX code with
`npx tsx`, letting it write and run @react-pdf/renderer scripts on
demand.  A `run_command` tool is also provided for shell operations
(installing packages, inspecting files, converting PDFs to images, etc.)

Usage
-----
Set the two environment variables shown below, then run:

    python react_pdf_tool.py

Required environment variables
-------------------------------
ANTHROPIC_API_KEY   – Your AnthropicFoundry API key
ANTHROPIC_BASE_URL  – Your AnthropicFoundry endpoint URL
ANTHROPIC_MODEL     – Deployment / model name (e.g. "claude-3-5-sonnet")
"""

import asyncio
import os
import shlex
import subprocess
import tempfile

from anthropic import AnthropicFoundry

# ---------------------------------------------------------------------------
# Client setup
# ---------------------------------------------------------------------------

api_key = os.environ["ANTHROPIC_API_KEY"]
base_url = os.environ["ANTHROPIC_BASE_URL"]
model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

client = AnthropicFoundry(api_key=api_key, base_url=base_url)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def run_tsx(code: str) -> str:
    """Write *code* to a temp .tsx file and execute it with `npx tsx`."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tsx", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["npx", "tsx", tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return output if output.strip() else "(no output)"
    except Exception as exc:
        return str(exc)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def run_command(command: str) -> str:
    """Run a shell command and return combined stdout + stderr."""
    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return output if output.strip() else "(no output)"
    except Exception as exc:
        return str(exc)


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool-use schema)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "run_tsx",
        "description": (
            "Execute TypeScript/JSX code using `npx tsx` and return the output. "
            "Use this to generate PDF files with @react-pdf/renderer. "
            "Always wrap async rendering in an IIFE: `(async () => { ... })();`. "
            "Write output files to the current working directory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "TypeScript/JSX source code to execute",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command (parsed safely without a shell) and return combined "
            "stdout + stderr. "
            "Use for installing npm packages, listing files, converting PDFs to "
            "preview images with pdftoppm or PyMuPDF, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                }
            },
            "required": ["command"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt — embeds react-pdf best practices
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert PDF generation assistant powered by the @react-pdf/renderer library.

When the user asks you to create or modify a PDF:
1. Use the `run_command` tool to install required npm packages if needed:
   `npm install react @react-pdf/renderer` and `npm install -D tsx @types/react`
2. Write a TypeScript/JSX script and execute it with the `run_tsx` tool.
3. Always wrap async rendering in an IIFE:
   `(async () => { await renderToFile(<MyDocument />, "./output.pdf"); })()`
4. Remote font URLs do NOT work — download fonts to local files first.
5. After registering custom fonts, always disable hyphenation:
   `Font.registerHyphenationCallback((word) => [word]);`
6. To preview the PDF, run `pdftoppm -png -r 150 output.pdf preview` with `run_command`.
7. Confirm success and report the output file path to the user.

Core components: Document, Page, View, Text, Image, Link, Svg, StyleSheet.
Built-in fonts: Courier, Helvetica, Times-Roman (with Bold/Italic variants).
"""

# ---------------------------------------------------------------------------
# Interactive chat loop
# ---------------------------------------------------------------------------

async def chat() -> None:
    messages: list[dict] = []
    print("React-PDF AI assistant  (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Inner loop: keep going until the model returns a text response
        while True:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOLS,
            )

            content_block = response.content[0]

            # ---- Tool call ----
            if content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input

                print(f"\n[Tool] {tool_name} → {tool_input}\n")

                if tool_name == "run_tsx":
                    output = run_tsx(tool_input["code"])
                elif tool_name == "run_command":
                    output = run_command(tool_input["command"])
                else:
                    output = f"Unknown tool: {tool_name}"

                print(f"[Tool output]\n{output}\n")

                # Append assistant turn with the tool call
                messages.append(
                    {"role": "assistant", "content": [content_block]}
                )
                # Append tool result as a user turn
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": output,
                            }
                        ],
                    }
                )
                continue  # send result back to model

            # ---- Normal text response ----
            elif content_block.type == "text":
                print(f"AI: {content_block.text}\n")
                messages.append(
                    {"role": "assistant", "content": content_block.text}
                )
                break


if __name__ == "__main__":
    asyncio.run(chat())
