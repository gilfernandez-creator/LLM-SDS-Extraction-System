from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from format_guardrails import apply_format_guardrails

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

from prompts import SYSTEM, user_prompt

MAX_CHARS = 120_000

def read_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)

def read_input(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        return read_pdf_text(file_path)
    return file_path.read_text(encoding="utf-8", errors="replace")

def require_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set. Add it to .env")

def main() -> int:
    load_dotenv()
    require_key()

    if len(sys.argv) < 2:
        print("Usage: python src/main.py <path-to-sds.pdf-or-textfile>")
        return 1

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}")
        return 1

    text = read_input(file_path)
    clipped = text[:MAX_CHARS] if len(text) > MAX_CHARS else text

    client = OpenAI()

    resp = client.responses.create(
        model="gpt-3.5-turbo",
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt(clipped)},
        ],
    )

    out = resp.output_text or ""
    try:
        parsed = json.loads(out)
        warnings = apply_format_guardrails(parsed, normalize=True)
        parsed.setdefault("meta", {})
        parsed["meta"].setdefault("validation_warnings", [])
        parsed["meta"]["validation_warnings"].extend(warnings)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        print(pretty)
        Path("output.json").write_text(pretty, encoding="utf-8")
    except Exception:
        print(out)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
