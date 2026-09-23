from pathlib import Path
import json


def load_policy(policy_path):
    policy_path = Path(policy_path)

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Policy file not found: {policy_path}"
        )

    try:
        with open(
            policy_path,
            "r",
            encoding="utf-8"
        ) as f:
            policy = json.load(f)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid policy JSON: {error}"
        ) from error

    validate_policy(policy)

    return policy


def validate_policy(policy):

    if not isinstance(policy, dict):
        raise ValueError(
            "Policy JSON must be a JSON object."
        )

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

    for policy_index, policy_item in enumerate(
        policy["policies"]
    ):

        if not isinstance(policy_item, dict):
            raise ValueError(
                f"Policy {policy_index} must be an object."
            )

        if "policy_metadata" not in policy_item:
            raise ValueError(
                f"Policy {policy_index} missing policy_metadata."
            )

        if "rules" not in policy_item:
            raise ValueError(
                f"Policy {policy_index} missing rules."
            )

        if not isinstance(
            policy_item["rules"],
            list
        ):
            raise ValueError(
                f"Policy {policy_index} rules must be a list."
            )

        rule_ids = set()

        for rule in policy_item["rules"]:

            if not isinstance(rule, dict):
                raise ValueError(
                    "Every rule must be an object."
                )

            rule_id = rule.get("rule_id")

            if not rule_id:
                raise ValueError(
                    "Every rule must have a rule_id."
                )

            if rule_id in rule_ids:
                raise ValueError(
                    f"Duplicate rule ID: {rule_id}"
                )

            rule_ids.add(rule_id)

    print("Policy JSON validation passed.")

    return True