#!/usr/bin/env python3
"""
Generate image via OpenAI gpt-image-1 / DALL-E 3 API.

Requires OPENAI_API_KEY in tokens.json under "openai.api_key".

Usage:
  python3 gen-image-openai.py "prompt text" --size 1024x1024 --quality medium --output out.png

Pricing (gpt-image-1):
  - 1024x1024 low:    $0.04
  - 1024x1024 medium: $0.07
  - 1024x1024 high:   $0.17
  - 1024x1536/1536x1024 same tier
"""
import argparse, base64, json, pathlib, sys
try:
    import requests
except ImportError:
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)

TOKENS = pathlib.Path.home() / "artvision-data" / "tokens.json"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--size", default="1024x1024", choices=["1024x1024", "1024x1536", "1536x1024"])
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--output", default="output.png")
    ap.add_argument("--model", default="gpt-image-1")
    args = ap.parse_args()

    t = json.load(TOKENS.open())
    if "openai" not in t or "api_key" not in t.get("openai", {}):
        print("ERROR: tokens.json missing openai.api_key", file=sys.stderr)
        print("Get key: https://platform.openai.com/api-keys", file=sys.stderr)
        sys.exit(1)
    api_key = t["openai"]["api_key"]

    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
            "quality": args.quality,
            "n": 1,
        },
        timeout=120
    )
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:500]}", file=sys.stderr)
        sys.exit(1)
    data = r.json()["data"][0]
    img_b64 = data.get("b64_json") or data.get("url")
    if data.get("b64_json"):
        pathlib.Path(args.output).write_bytes(base64.b64decode(img_b64))
    else:
        import urllib.request
        urllib.request.urlretrieve(img_b64, args.output)
    print(f"✅ {args.output}")
    print(f"   size: {args.size}, quality: {args.quality}, cost: ~${{low:.04, medium:.07, high:.17}}[args.quality]")

if __name__ == "__main__":
    main()
