import json
import os
import sys
from anthropic import Anthropic

DIFF_PATH = "pr.diff"

def load_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    policy_path = os.getenv("REVIEW_POLICY_PATH", "").strip()
    service_name = os.getenv("SERVICE_NAME", "unknown-service").strip()

    if not api_key:
        print("ANTHROPIC_API_KEY not provided.")
        sys.exit(1)

    if not os.path.exists(DIFF_PATH):
        print("pr.diff not found.")
        sys.exit(1)

    if not policy_path or not os.path.exists(policy_path):
        print("Review policy file not found.")
        sys.exit(1)

    diff = load_file(DIFF_PATH)
    policy = load_file(policy_path)

    if not diff.strip():
        print("Empty diff.")
        sys.exit(0)

    client = Anthropic(api_key=api_key)

    system_prompt = f"""
You are a strict pull request reviewer.

Project/service name: {service_name}

Use the following review policy:
{policy}

Return ONLY valid JSON in the following format:
{{
  "score": 0,
  "decision": "approve|human_review|reject",
  "summary": "short summary",
  "issues": [
    {{
      "severity": "high|medium|low",
      "title": "issue title",
      "details": "issue details"
    }}
  ]
}}
"""

    user_prompt = f"""
Review the following pull request diff.

Be conservative.
Reduce score when tests are missing in risky areas.
Reject severe security or architecture issues.

PR DIFF:
{diff[:120000]}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2500,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text
    print(raw_text)

    result = json.loads(raw_text)
    score = int(result.get("score", 0))
    decision = result.get("decision", "reject")

    if decision == "reject" or score < 6:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
