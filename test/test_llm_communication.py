#!/usr/bin/env python3
"""Test script for Claude Sonnet API communication."""

import argparse
import os
import sys

import anthropic


def main():
    parser = argparse.ArgumentParser(description="Send a prompt to Claude Sonnet and print the response.")
    parser.add_argument("prompt", nargs="?", default="Hello! Please briefly introduce yourself.", help="The prompt to send")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Maximum tokens in response")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Sending prompt: {args.prompt}\n")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=args.max_tokens,
        messages=[{"role": "user", "content": args.prompt}],
    )

    print(f"Model: {message.model}")
    print(f"Usage: {message.usage.input_tokens} input, {message.usage.output_tokens} output tokens")
    print(f"Stop reason: {message.stop_reason}\n")
    print("Response:")
    print(message.content[0].text)


if __name__ == "__main__":
    main()
