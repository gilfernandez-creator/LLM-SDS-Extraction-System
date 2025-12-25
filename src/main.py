from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from format_guardrails import apply_format_guardrails

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from eval import evaluate
from prompts import SYSTEM, user_prompt
from datetime import datetime, timezone
import uuid
import argparse

import sys

# Force UTF-8 output on Windows so characters like "≥" don't crash printing
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_CHARS =50_000

REQUEST_VERSION = "sds-extractor-v0.1"  # bump when you change schema/prompt
MODEL_NAME = "gpt-4o-mini"

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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

    parser = argparse.ArgumentParser(
        description="SDS PDF extractor (LLM + deterministic guardrails)"
    )
    parser.add_argument(
        "input_path",
        help="Path to SDS PDF or text file"
    )
    parser.add_argument(
        "--out",
        default="output.json",
        help="Where to write the extracted JSON (default: output.json)"
    )
    parser.add_argument(
    "--eval",
    dest="truth_path",
    type=Path,
    default=None,
    help="Path to ground-truth JSON file for evaluation"
    )

    args = parser.parse_args()
    truth_path: Path | None = args.truth_path
    if truth_path is not None and not truth_path.exists():
        raise FileNotFoundError(f"Truth file not found: {truth_path}")

    file_path = Path(args.input_path)
    out_path = Path(args.out)
    


    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}")
        return 1
    run_id = new_run_id()
    run_ts = utc_now_iso()
    input_filename = file_path.name
    text = read_input(file_path)
    clipped = text[:MAX_CHARS] if len(text) > MAX_CHARS else text
    total_chars = len(text)
    sent_chars = len(clipped)
    was_truncated = total_chars > MAX_CHARS
    print(f"[SDS STATS] total_chars={total_chars:,} sent_chars={sent_chars:,} truncated={was_truncated}", file=sys.stderr)


    client = OpenAI()

    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt(clipped)},
        ],
    )

    out = resp.output_text or ""
    parsed = None
    try:
        parsed = json.loads(out)
        warnings = apply_format_guardrails(parsed, normalize=True)
        
        # Ensure meta exists
        parsed.setdefault("meta", {})

        # 1. ALWAYS populate standard metadata
        parsed["meta"]["run_id"] = run_id
        parsed["meta"]["run_timestamp_utc"] = run_ts
        parsed["meta"]["input_filename"] = input_filename
        parsed["meta"]["model"] = MODEL_NAME
        parsed["meta"]["request_version"] = REQUEST_VERSION
        parsed["meta"]["max_chars"] = MAX_CHARS
        parsed["meta"]["input_char_count"] = total_chars
        parsed["meta"]["chars_sent_to_model"] = sent_chars
        parsed["meta"]["input_truncated"] = was_truncated
        parsed["meta"].setdefault("validation_warnings", [])
        parsed["meta"]["validation_warnings"].extend(warnings)

        # 2. ONLY populate eval results if a truth file was provided
        if truth_path:
            truth = json.loads(truth_path.read_text(encoding="utf-8"))
            eval_result = evaluate(parsed, truth)

            print(
                f"\n[EVAL] accuracy={eval_result['accuracy']}% "
                f"correct={eval_result['correct']}/{eval_result['fields_compared']} "
                f"missing={len(eval_result['missing'])} "
                f"hallucinated={len(eval_result['hallucinated'])}",
                file=sys.stderr
            )
            parsed["meta"]["eval"] = eval_result

        # 3. Print and save
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        print(pretty)
        out_path.write_text(pretty, encoding="utf-8")
    except Exception:
        print(out)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
