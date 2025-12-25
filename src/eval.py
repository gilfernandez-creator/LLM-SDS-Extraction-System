from __future__ import annotations
from typing import Dict, Any, Tuple

def flatten_values(obj: Any, prefix=""):
    """
    Yields (path, value) for every leaf .value field.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if k == "value":
                yield prefix, v
            else:
                yield from flatten_values(v, new_prefix)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from flatten_values(item, f"{prefix}[{i}]")

def evaluate(extracted: dict, truth: dict) -> dict:
    correct = 0
    fields_compared = 0
    missing = []
    hallucinated = []  # will stay empty unless you explicitly track it

    def normalize(v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip().lower()
        return v

    def walk(truth_node, extracted_node, path=""):
        nonlocal correct, fields_compared, missing

        # Only evaluate fields that exist in truth
        if isinstance(truth_node, dict):
            for key, truth_val in truth_node.items():
                new_path = f"{path}.{key}" if path else key
                extracted_val = extracted_node.get(key) if isinstance(extracted_node, dict) else None
                walk(truth_val, extracted_val, new_path)

        elif isinstance(truth_node, list):
            for i, truth_item in enumerate(truth_node):
                try:
                    extracted_item = extracted_node[i]
                except Exception:
                    extracted_item = None
                walk(truth_item, extracted_item, f"{path}[{i}]")

        else:
            # Leaf comparison (value objects)
            fields_compared += 1

            truth_value = normalize(truth_node)
            extracted_value = normalize(extracted_node)

            if extracted_value == truth_value:
                correct += 1
            else:
                missing.append(path)

    walk(truth, extracted)

    accuracy = round((correct / fields_compared) * 100, 2) if fields_compared else 100.0

    return {
        "fields_compared": fields_compared,
        "correct": correct,
        "missing": missing,
        "hallucinated": hallucinated,
        "accuracy": accuracy,
    }
