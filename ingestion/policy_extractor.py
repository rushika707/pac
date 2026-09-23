import json
import os
from pathlib import Path

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


PROMPT = r"""
You are a policy-to-machine-readable-JSON extraction engine.

Convert the supplied POLICY DOCUMENT into a faithful JSON representation.

The POLICY DOCUMENT is the ONLY source of truth.

============================================================
CORE RULES
============================================================

1. Extract EVERY rule from the policy.

2. Extract EVERY requirement from the policy.

3. Extract EVERY decision from the policy.

4. Extract EVERY remediation requirement from the policy.

5. Extract EVERY evidence requirement from the policy.

6. Extract ALL definitions, metadata, purpose and scope.

7. NEVER omit a rule because it is difficult to evaluate automatically.

8. NEVER omit a rule because some dataset may not contain its fields.

9. NEVER modify a rule based on any dataset.

10. NEVER introduce dataset-specific information.

11. NEVER write:
    - "not present in dataset"
    - "not evaluable"
    - "manual because dataset lacks field"
    - "generated dataset"
    - "not applicable to dataset"

12. Preserve rule IDs exactly as written in the policy.

13. Preserve rule descriptions exactly as written.

14. Preserve examples exactly as written.

15. Preserve combinations exactly as written.

16. Preserve the distinction between:
    - direct identifiers
    - sensitive personal data
    - combination identifiers
    - requirements
    - decisions
    - remediation
    - evidence

17. ALL sensitive personal data rules must be extracted.

18. ALL combination rules must be extracted.

19. Do not invent rules.

20. Do not merge different rules.

21. Do not split one policy rule into multiple artificial rules.

22. Do not use external knowledge to add fields or rules.

============================================================
IMPORTANT FIELD PRESERVATION RULE
============================================================

If the policy says:

Phone or mobile number

and gives examples:

mobile
telephone
phone_number

preserve those policy terms.

DO NOT change them to:

phone

because a dataset might contain a column called "phone".

Similarly, if the policy says:

Date of birth + postcode + gender

preserve:

date of birth
postcode
gender

DO NOT replace "postcode" with "address".

The dataset will be mapped separately after extraction.


EXECUTION
=========

Preserve execution information only when it is explicitly supported by
the policy document.

The policy JSON must represent the policy, not a dataset.

Do not infer dataset columns.

Do not map policy fields to dataset fields.

Do not replace policy terms.

For example:

Policy:
Phone or mobile number

Examples:
mobile, telephone, phone_number

Preserve those policy terms.

Policy:
Date of birth + postcode + gender

Preserve:
date of birth
postcode
gender

Do not replace postcode with address.

If execution information cannot be reliably extracted from the document,
omit the execution property rather than inventing information.

Dataset applicability will be handled by the policy engine later.
============================================================
POLICY STRUCTURE
============================================================

Return:

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

Every item inside "rules" MUST be an object.

Every rule object MUST contain:

"rule_id"
"description"

If the policy provides examples, preserve them.

If the policy provides an outcome, preserve it.

============================================================
SENSITIVE PERSONAL DATA
============================================================

Do NOT forget sensitive personal data rules.

Extract ALL rules concerning:

- health / medical information
- ethnicity / racial origin
- religion / belief
- political opinion
- trade union membership
- biometric information
- genetic information

============================================================
COMBINATION RULES
============================================================

Extract ALL combination rules exactly as stated.

Do not replace one component with another component because a dataset
contains a similar field.

============================================================
REQUIREMENTS
============================================================

Requirements such as:

- pre-use scanning
- record-level flagging
- direct identifier handling
- sensitive data handling
- combination rule handling
- free-text scanning
- remediation evidence
- approved dataset output
- exception handling
- audit trail

must remain requirements.

Do not turn them into dataset-specific rules.

============================================================
DECISIONS
============================================================

Preserve all decisions exactly as defined in the policy.

============================================================
REMEDIATION
============================================================

Preserve all remediation methods and their policy expectations.

============================================================
EVIDENCE
============================================================

Preserve all evidence requirements.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

No Markdown.

No code fences.

No explanation.

No text before or after the JSON.

Before returning the JSON, internally verify:

- all policy rules are present
- no policy rule was omitted
- no policy rule was invented
- all SPII rules are present
- all combination rules are present
- all requirements are present
- all decisions are present
- all remediation items are present
- all evidence items are present
- rule IDs are preserved
- policy wording is preserved
- no dataset information was introduced
- the JSON is syntactically valid
"""


def _extract_json(response_text: str):
    text = response_text.strip()

    # Remove Markdown code fences if Qwen adds them.
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "No JSON object found in Qwen response."
        )

    text = text[start:end + 1]

    return json.loads(text)


def _validate_policy_structure(policy):

    if not isinstance(policy, dict):
        raise ValueError(
            "Policy output must be a JSON object."
        )

    if "policies" not in policy:
        raise ValueError(
            "Policy JSON must contain 'policies'."
        )

    if not isinstance(policy["policies"], list):
        raise ValueError(
            "'policies' must be a list."
        )

    if not policy["policies"]:
        raise ValueError(
            "'policies' cannot be empty."
        )

    for policy_index, policy_item in enumerate(
        policy["policies"]
    ):

        if not isinstance(policy_item, dict):
            raise ValueError(
                f"Policy {policy_index} must be an object."
            )

        if "policy_metadata" not in policy_item:
            raise ValueError(
                f"Policy {policy_index} missing "
                "'policy_metadata'."
            )

        if "rules" not in policy_item:
            raise ValueError(
                f"Policy {policy_index} missing 'rules'."
            )

        rules = policy_item["rules"]

        if not isinstance(rules, list):
            raise ValueError(
                f"Policy {policy_index} 'rules' "
                "must be a list."
            )

        if not rules:
            raise ValueError(
                f"Policy {policy_index} contains no rules."
            )

        rule_ids = set()

        for rule_index, rule in enumerate(rules):

            if not isinstance(rule, dict):
                raise ValueError(
                    "\n"
                    "Invalid rule structure:\n"
                    f"  Policy index : {policy_index}\n"
                    f"  Rule index   : {rule_index}\n"
                    f"  Type         : {type(rule).__name__}\n"
                    f"  Value        : {repr(rule)}\n"
                )

            rule_id = rule.get("rule_id")

            if not rule_id:
                raise ValueError(
                    f"Rule at index {rule_index} "
                    "is missing 'rule_id'.\n"
                    f"Rule: {rule}"
                )

            if rule_id in rule_ids:
                raise ValueError(
                    f"Duplicate rule ID found: {rule_id}"
                )

            rule_ids.add(rule_id)

    return True


def _call_qwen(prompt):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,

            "format": {
                "type": "object",
                "properties": {
                    "policies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "policy_metadata": {
                                    "type": "object"
                                },
                                "purpose": {
                                    "type": "string"
                                },
                                "scope": {
                                    "type": "string"
                                },
                                "definitions": {
                                    "type": "array"
                                },
                                "rules": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "rule_id": {
                                                "type": "string"
                                            },
                                            "description": {
                                                "type": "string"
                                            },
                                            "examples": {
                                                "type": "array"
                                            },
                                            "execution": {
                                                "type": "object"
                                            },
                                            "outcome": {
                                                "type": "string"
                                            }
                                        },
                                        "required": [
                                            "rule_id",
                                            "description"
                                        ]
                                    }
                                },
                                "requirements": {
                                    "type": "array"
                                },
                                "decisions": {
                                    "type": "array"
                                },
                                "remediation": {
                                    "type": "array"
                                },
                                "evidence": {
                                    "type": "array"
                                }
                            },
                            "required": [
                                "policy_metadata",
                                "purpose",
                                "scope",
                                "definitions",
                                "rules",
                                "requirements",
                                "decisions",
                                "remediation",
                                "evidence"
                            ]
                        }
                    }
                },
                "required": [
                    "policies"
                ]
            },

            "options": {
                "temperature": 0,
                "num_ctx": 32768,
                "num_predict": 12000
            }
        },
        timeout=900,
    )

    response.raise_for_status()

    data = response.json()

    if "response" not in data:
        raise ValueError(
            "Ollama response does not contain 'response'."
        )

    return data["response"]

def _build_retry_prompt(pdf_text):

    return r"""
You are correcting a policy extraction.

Return ONLY one valid JSON object.

The POLICY DOCUMENT below is the only source of truth.

The previous model response was structurally invalid.

STRICT REQUIREMENTS:

1. "policies" MUST be a JSON array.

2. Each item in "policies" MUST be a JSON object.

3. "rules" MUST be a JSON array.

4. EVERY item inside "rules" MUST be a JSON object.

5. Every rule object MUST contain "rule_id".

6. Never place a string directly inside "rules".

7. Never place an array directly inside "rules".

8. Extract EVERY policy rule.

9. Do NOT omit SPII rules.

10. Do NOT omit combination rules.

11. Do NOT omit requirements.

12. Do NOT omit decisions.

13. Do NOT omit remediation.

14. Do NOT omit evidence.

15. Preserve rule IDs exactly.

16. Preserve policy wording.

17. Do NOT use dataset information.

18. Do NOT add:
    - dataset fields
    - dataset availability
    - manual reasons
    - not-evaluable statements
    - generated-dataset statements

19. Do not change "postcode" to "address".

20. Do not change "phone_number" to "phone".

21. The output must describe the policy only.

22. Return valid JSON only.

Required structure:

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

POLICY DOCUMENT:
""" + "\n\n" + pdf_text


def extract_policy(pdf_text: str, output_file: str):

    if not pdf_text or not pdf_text.strip():
        raise ValueError(
            "PDF text is empty."
        )

    full_prompt = (
        PROMPT
        + "\n\n"
        + "=" * 80
        + "\nPOLICY DOCUMENT\n"
        + "=" * 80
        + "\n\n"
        + pdf_text
    )

    print(f"Using Ollama model: {MODEL}")
    print("Extracting policy from PDF...")

    raw_response = _call_qwen(full_prompt)

    raw_debug_file = Path(
        "/tmp/qwen_raw_response.txt"
    )

    try:
        raw_debug_file.write_text(
            raw_response,
            encoding="utf-8"
        )
    except Exception:
        pass

    # ---------------------------------------------------------
    # STEP 1: Parse JSON
    # ---------------------------------------------------------

    try:

        policy = _extract_json(raw_response)

    except Exception as first_error:

        print()
        print("Initial JSON parsing failed.")
        print("Retrying JSON extraction...")

        correction_prompt = r"""
The previous response was invalid JSON.

Fix ONLY the JSON syntax.

Do not change the policy content.

Do not remove rules.

Do not add rules.

Do not introduce dataset information.

Return ONLY valid JSON.

Previous response:

""" + raw_response

        corrected_response = _call_qwen(
            correction_prompt
        )

        try:

            policy = _extract_json(
                corrected_response
            )

        except Exception as second_error:

            raise ValueError(
                "Qwen produced invalid JSON "
                "after syntax retry.\n"
                f"First error: {first_error}\n"
                f"Second error: {second_error}\n"
                f"Raw response: {raw_debug_file}"
            ) from second_error

    # ---------------------------------------------------------
    # STEP 2: Validate structure
    # ---------------------------------------------------------

    try:

        _validate_policy_structure(policy)

    except ValueError as validation_error:

        print()
        print(
            "Qwen JSON structure is invalid:"
        )
        print(validation_error)
        print()
        print(
            "Retrying complete policy extraction..."
        )

        retry_prompt = _build_retry_prompt(
            pdf_text
        )

        corrected_response = _call_qwen(
            retry_prompt
        )

        try:

            policy = _extract_json(
                corrected_response
            )

            _validate_policy_structure(
                policy
            )

        except Exception as retry_error:

            raise ValueError(
                "Qwen produced an invalid policy "
                "structure after structural retry.\n"
                f"Validation error: {retry_error}\n"
                f"Raw response saved to: "
                f"{raw_debug_file}"
            ) from retry_error

    # ---------------------------------------------------------
    # STEP 3: Save
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # STEP 4: Statistics
    # ---------------------------------------------------------

    policy_count = len(
        policy["policies"]
    )

    rule_count = sum(
        len(p.get("rules", []))
        for p in policy["policies"]
    )

    requirement_count = sum(
        len(p.get("requirements", []))
        for p in policy["policies"]
    )

    decision_count = sum(
        len(p.get("decisions", []))
        for p in policy["policies"]
    )

    remediation_count = sum(
        len(p.get("remediation", []))
        for p in policy["policies"]
    )

    evidence_count = sum(
        len(p.get("evidence", []))
        for p in policy["policies"]
    )

    print()
    print("Policy extraction successful.")
    print(f"Policies:      {policy_count}")
    print(f"Rules:         {rule_count}")
    print(f"Requirements:  {requirement_count}")
    print(f"Decisions:     {decision_count}")
    print(f"Remediation:   {remediation_count}")
    print(f"Evidence:      {evidence_count}")
    print(f"Output:        {output_path}")

    return policy