import json
import os
from pathlib import Path

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


PROMPT = r"""
You are a policy-to-machine-readable-JSON extraction engine.

Read the supplied policy text and return ONLY valid JSON.

IMPORTANT:
- Preserve the policy faithfully.
- Do not invent policy rules.
- Do not omit rules.
- Do not hardcode a particular policy domain.
- The output must work for arbitrary policy documents.
- Preserve policy terminology and wording.
- Extract executable rules separately from general policy requirements.
- Every executable rule must contain an "execution" object.
- The execution object must describe HOW the rule can be evaluated against structured data.
- Do not use Python code.
- Do not use Markdown.
- Do not explain your answer.

For executable field-based rules:

"execution": {
  "type": "field",
  "fields": [
    ["possible_field_name_1", "possible_field_name_2"]
  ]
}

For rules requiring multiple attributes:

"execution": {
  "type": "combination",
  "fields": [
    ["possible_field_name_1", "possible_alias"],
    ["possible_field_name_2", "possible_alias"]
  ]
}

For free-text rules:

"execution": {
  "type": "text",
  "fields": [
    ["possible_text_field"]
  ],
  "patterns": [
    "pattern derived from the policy"
  ]
}

For rules that cannot be automatically evaluated against a dataset:

"execution": {
  "type": "manual",
  "reason": "Why automatic record-level evaluation is not possible"
}

The "execution" metadata must be derived from the policy itself.
Rule IDs must be copied exactly from the source policy.
Never modify, abbreviate, reinterpret, or invent a rule ID.
CRITICAL EXTRACTION RULES:

1. Preserve ALL policy rules, requirements, decisions, remediation actions,
   evidence requirements, classifications, and exceptions found in the source.

2. Do NOT place policy requirements inside "rules".
   "rules" must contain only rules that define a condition on dataset records
   or data fields.

3. Rules that are procedural, organizational, approval-based, audit-related,
   documentation-related, or otherwise cannot evaluate an individual dataset
   record must go into "requirements", not "rules".

4. Every executable rule must contain:
   - rule_id
   - description
   - execution

5. For every executable rule, extract the policy's required outcome if one
   is explicitly associated with that rule. Preserve it as:
   "outcome": "EXACT POLICY OUTCOME"

6. Extract the policy's decision catalogue into "decisions".
   Do not invent decision names.

7. Extract remediation actions into "remediation".
   Preserve the policy's terminology.

8. Extract evidence requirements into "evidence".

9. Do not invent field names from general knowledge.
   If the policy describes a data attribute using natural language, preserve
   that wording as the field candidate.

10. For combination rules, each inner array represents fields that must
    simultaneously exist. Do not convert one policy concept into unrelated
    aliases unless the policy explicitly provides those alternatives.

11. For text rules, extract patterns only when the policy explicitly gives
    patterns, examples, keywords, or recognizable text indicators.
    Do not invent regex patterns.

12. A manual rule must not be placed in executable "rules".
    Place it under "requirements" with its execution metadata.

13. Do not duplicate the same rule in both "rules" and "requirements".

14. Preserve the complete source policy. Do not summarize away policy
    requirements, decisions, remediation, exceptions, or evidence.

15. Return ONLY valid JSON.

Return exactly this JSON structure:

{
  "policies": [
    {
      "policy_metadata": {},
      "purpose": "",
      "scope": "",
      "definitions": [],
      "rules": [],
      "requirements": [],
      "decisions": [],
      "remediation": [],
      "evidence": []
    }
  ]
}

IMPORTANT JSON STRUCTURE RULE:

"rules", "requirements", "decisions", "remediation", and "evidence"
are ALL separate sibling fields inside the policy object.

NEVER place "decisions", "remediation", or "evidence" inside a rule
or requirement object.

Example:

{
  "rules": [
    {
      "rule_id": "RULE-01",
      "description": "...",
      "execution": {},
      "outcome": "..."
    }
  ],
  "requirements": [
    {
      "rule_id": "REQ-01",
      "description": "...",
      "execution": {}
    }
  ],
  "decisions": [
    {
      "decision": "PASS",
      "meaning": "...",
      "required_action": "..."
    }
  ],
  "remediation": [],
  "evidence": []
}

Finish the JSON only after all sibling sections have been closed.

Return ONLY valid JSON.
"""


def extract_policy(pdf_text: str, output_file: str):
    prompt = PROMPT + "\n" + pdf_text

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                  "temperature": 0
              },
        },
        timeout=600,
    )

    response.raise_for_status()

    result = response.json()

    content = result.get("response", "").strip()
    with open("/tmp/qwen_raw_response.txt", "w", encoding="utf-8") as f:
      f.write(content)

    if not content:
        raise ValueError("Ollama returned an empty response.")

    try:
        policy = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Qwen returned invalid JSON: {error}"
        ) from error

    output_path = Path(output_file)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            policy,
            f,
            indent=2,
            ensure_ascii=False
        )

    return policy


if __name__ == "__main__":

    print(f"Using Ollama model: {MODEL}")