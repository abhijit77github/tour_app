"""Smoke test for AWS Bedrock Converse API.

Run from the project root:

    python -m backend.scripts.test_bedrock_converse

This script loads the same app settings used by the backend, creates a Bedrock
Runtime client, and sends a tiny prompt through the Converse API. It prints the
returned text so you can verify that the credentials, region, and model ID are
all working.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Ensure the repository root is importable when the script is executed directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings  # noqa: E402


DEFAULT_PROMPT = "Reply with exactly: Bedrock converse test successful."


def build_client():
    """Create a Bedrock Runtime client using the app's configured credentials."""
    region = settings.aws_region
    access_key = settings.aws_access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = settings.aws_secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = settings.aws_session_token or os.environ.get("AWS_SESSION_TOKEN")

    if not access_key or not secret_key:
        raise RuntimeError(
            "Missing AWS credentials. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env or your shell."
        )

    client_kwargs = {
        "service_name": "bedrock-runtime",
        "region_name": region,
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if session_token:
        client_kwargs["aws_session_token"] = session_token

    return boto3.client(**client_kwargs)


def extract_text(response: dict) -> str:
    """Extract text from a Converse response payload."""
    output = response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])

    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    return "".join(parts).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test AWS Bedrock Converse API access")
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt to send to the model",
    )
    parser.add_argument(
        "--model-id",
        default=settings.bedrock_model_id,
        help="Bedrock model ID to test",
    )
    args = parser.parse_args()

    print("Bedrock converse smoke test")
    print(f"Region: {settings.aws_region}")
    print(f"Model:  {args.model_id}")
    print(f"Prompt: {args.prompt}")
    print("-")

    try:
        client = build_client()
        response = client.converse(
            modelId=args.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": args.prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": 64,
                "temperature": 0.0,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        print("Bedrock request failed:")
        print(exc)
        return 1
    except Exception as exc:
        print("Failed to run smoke test:")
        print(exc)
        return 1

    text = extract_text(response)
    stop_reason = response.get("stopReason", "unknown")

    print("Success")
    print(f"Stop reason: {stop_reason}")
    print("Response:")
    print(text or json.dumps(response, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
