import json
import re
from pathlib import Path


BASE = Path(__file__).parent.parent
POLICY_FILE = BASE / "policy" / "policy.json"
OUTPUT_FILE = BASE / "opa" / "generated_policy.rego"


def load_policy():
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_rules(policy):
    rules = {}

    def walk(value):
        if isinstance(value, dict):
            rule_id = (
                value.get("Rule ID")
                or value.get("rule_id")
                or value.get("ID")
            )

            if rule_id and not str(rule_id).startswith("DP-"):
                rules[str(rule_id)] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)
    return rules


def extract_outcome(rule):
    text = str(
        rule.get("Required policy outcome")
        or rule.get("Required outcome")
        or rule.get("outcome")
        or ""
    ).upper()

    if "BLOCK" in text:
        return "BLOCK"

    if "FLAG" in text:
        return "FLAG"

    if "EXCEPTION APPROVED" in text:
        return "EXCEPTION APPROVED"

    if "PASS" in text:
        return "PASS"

    return "FLAG"


def quote(value):
    return json.dumps(str(value))


def generate_condition(rule):
    execution = rule.get("execution", {})
    execution_type = execution.get("type")

    if execution_type == "field":
        fields = execution.get("fields", [])

        if not fields:
            return "false"

        return f"has_any({json.dumps(fields)})"

    if execution_type == "combination":
        fields = execution.get("fields", [])

        if not fields:
            return "false"

        groups = []

        for group in fields:
            if isinstance(group, str):
                group = [group]

            groups.append(group)

        return f"all_groups_present({json.dumps(groups)})"

    if execution_type == "text":
        fields = execution.get("fields", [])
        patterns = execution.get("patterns", [])

        flat_fields = []

        for group in fields:
            if isinstance(group, str):
                flat_fields.append(group)
            else:
                flat_fields.extend(group)

        return (
            f"text_matches("
            f"{json.dumps(flat_fields)}, "
            f"{json.dumps(patterns)}"
            f")"
        )

    return "false"


def generate(policy):
    rules = extract_rules(policy)

    lines = [
        "package generated_policy",
        "",
        "default decision := \"PASS\"",
        "",
        "# ================================================",
        "# Generic helpers",
        "# ================================================",
        "",
        "has_value(field) if {",
        '    value := object.get(input.record, field, "")',
        "    value != null",
        '    value != ""',
        "}",
        "",
        "has_any(groups) if {",
        "    some i",
        "    some j",
        "    has_value(groups[i][j])",
        "}",
        "",
        "all_groups_present(groups) if {",
        "    every group in groups {",
        "        some i",
        "        has_value(group[i])",
        "    }",
        "}",
        "",
        "text_matches(fields, patterns) if {",
        "    some i",
        "    some j",
        "    field := fields[i]",
        "    pattern := patterns[j]",
        '    value := object.get(input.record, field, "")',
        "    value != null",
        '    value != ""',
        "    regex.match(pattern, value)",
        "}",
        "",
        "# ================================================",
        "# Rule triggers",
        "# ================================================",
        "",
    ]

    generated_rules = []
    for rule_id, rule in rules.items():

        safe_id = re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            rule_id
        )

        execution = rule.get("execution")

        if execution:
            condition = generate_condition(rule)

        else:
            examples = (
                rule.get("Examples")
                or rule.get("examples")
                or []
            )

            if isinstance(examples, str):
                examples = [
                    x.strip()
                    for x in examples.split(",")
                    if x.strip()
                ]

            if not isinstance(examples, list):
                continue

            examples = [
                str(x).strip()
                for x in examples
                if str(x).strip()
            ]

            if not examples:
                continue

            condition = f"has_any({json.dumps(examples)})"

        outcome = extract_outcome(rule)

        generated_rules.append({
            "id": rule_id,
            "safe_id": safe_id,
            "outcome": outcome,
        })

        lines.extend([
            f"trigger_{safe_id} if {{",
            f"    {condition}",
            "}",
            "",
        ])

    # ================================================
    # Triggered rules
    # ================================================

    lines.append("# Triggered rules")
    lines.append("")

    for rule in generated_rules:
        lines.extend([
            f'triggered_rules contains {quote(rule["id"])} if {{',
            f'    trigger_{rule["safe_id"]}',
            "}",
            "",
        ])

    # ================================================
    # Outcome detection
    # ================================================

    lines.extend([
        "# ================================================",
        "# Outcome detection",
        "# ================================================",
        "",
        "default has_block := false",
        "default has_flag := false",
        "default has_exception := false",
        "",
    ])

    block_rules = []
    flag_rules = []
    exception_rules = []

    for rule in generated_rules:

        if rule["outcome"] == "BLOCK":
            block_rules.append(rule)

        elif rule["outcome"] == "FLAG":
            flag_rules.append(rule)

        elif rule["outcome"] == "EXCEPTION APPROVED":
            exception_rules.append(rule)

    for rule in block_rules:
        lines.extend([
            "has_block if {",
            f"    trigger_{rule['safe_id']}",
            "}",
            "",
        ])

    for rule in flag_rules:
        lines.extend([
            "has_flag if {",
            f"    trigger_{rule['safe_id']}",
            "}",
            "",
        ])

    for rule in exception_rules:
        lines.extend([
            "has_exception if {",
            f"    trigger_{rule['safe_id']}",
            "}",
            "",
        ])

    # ================================================
    # Final decision
    # ================================================

    lines.extend([
        "# ================================================",
        "# Final decision",
        "# ================================================",
        "",
        'decision := "BLOCK" if {',
        "    has_block",
        "}",
        "",
        'decision := "FLAG" if {',
        "    not has_block",
        "    has_flag",
        "}",
        "",
        'decision := "EXCEPTION APPROVED" if {',
        "    not has_block",
        "    not has_flag",
        "    has_exception",
        "}",
        "",
        "# ================================================",
        "# Final result",
        "# ================================================",
        "",
        "result := {",
        '    "decision": decision,',
        '    "triggered_rules": [rule | triggered_rules[rule]]',
        "}",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    policy = load_policy()

    rego = generate(policy)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(rego)

    print(f"Generated: {OUTPUT_FILE}")