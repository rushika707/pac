from pathlib import Path
import json


def load_policy(policy_path):
    policy_path = Path(policy_path)

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Policy file not found: {policy_path}"
        )

    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            policy = json.load(f)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid policy JSON: {error}"
        ) from error

    validate_policy(policy)

    return policy


def validate_policy(policy):
    if not isinstance(policy, dict):
        raise ValueError("Policy JSON must be a JSON object.")

    if "policies" not in policy:
        raise ValueError(
            "Policy JSON must contain a 'policies' section."
        )

    if not isinstance(policy["policies"], list):
        raise ValueError(
            "'policies' must be a list."
        )

    if not policy["policies"]:
        raise ValueError(
            "'policies' cannot be empty."
        )

    print("Policy JSON validation passed.")

    return True