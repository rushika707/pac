import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment

from policy.policy_loader import load_policy


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).parent

INPUT = BASE / "generated_data" / "synthetic_data.xlsx"
OUTPUT = BASE / "policy-dashboard" / "public" / "policy_results.xlsx"
POLICY_FILE = BASE / "policy" / "policy.json"


# ============================================================
# LOAD POLICY
# ============================================================

policy = load_policy(POLICY_FILE)


# ============================================================
# EXTRACT RULES GENERICALLY
# ============================================================

def extract_rules(policy):
    rules = {}

    def walk(value):
        if isinstance(value, dict):

            rule_id = (
                value.get("Rule ID")
                or value.get("rule_id")
                or value.get("ID")
            )

            # DP-* are policy/process requirements,
            # not record-level executable rules.
            if rule_id and not str(rule_id).startswith("DP-"):
                rules[str(rule_id)] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)

    return rules


RULES = extract_rules(policy)

print(f"Loaded executable rules: {len(RULES)}")


# ============================================================
# EXTRACT DECISIONS FROM POLICY JSON
# ============================================================

def extract_decisions(policy):
    decisions = {}

    def walk(value):
        if isinstance(value, dict):

            if "Decision" in value:
                decision = str(value["Decision"]).strip()
                decisions[decision] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)

    return decisions


DECISIONS = extract_decisions(policy)

print("Loaded decisions:")
for decision in DECISIONS:
    print(f"  {decision}")


# ============================================================
# NORMALIZE RULES
# ============================================================

def normalize_rule(rule_id, rule):

    normalized = {
        "rule_id": rule_id,
        "description": "",
        "fields": [],
        "examples": [],
        "outcome": "",
        "type": "unknown",

        # IMPORTANT:
        # Keep execution information from policy.json.
        "execution": rule.get("execution", {}),

        # Preserve original rule.
        "raw": rule,
    }

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    description_keys = [
        "PII type",
        "Sensitive data type",
        "Combination rule",
        "Policy requirement",
        "Policy statement",
        "description",
        "Description",
    ]

    for key in description_keys:
        if key in rule:
            normalized["description"] = str(rule[key])
            break

    # --------------------------------------------------------
    # Outcome
    # --------------------------------------------------------

    outcome_keys = [
        "Required policy outcome",
        "Required outcome",
        "outcome",
        "Outcome",
    ]

    for key in outcome_keys:
        if key in rule:
            normalized["outcome"] = str(rule[key])
            break

    # --------------------------------------------------------
    # Examples
    # --------------------------------------------------------

    examples = rule.get("Examples")

    if examples:

        if isinstance(examples, str):
            normalized["examples"] = [
                x.strip()
                for x in examples.split(",")
                if x.strip()
            ]

        elif isinstance(examples, list):
            normalized["examples"] = [
                str(x).strip()
                for x in examples
                if str(x).strip()
            ]

    # --------------------------------------------------------
    # Field rules
    # --------------------------------------------------------

    if normalized["examples"]:
        normalized["type"] = "field"
        normalized["fields"] = normalized["examples"]

    # --------------------------------------------------------
    # Combination rules
    # --------------------------------------------------------

    combination = rule.get("Combination rule")

    if combination:
        normalized["type"] = "combination"
        normalized["description"] = str(combination)
        normalized["combination_text"] = str(combination)

    # --------------------------------------------------------
    # Text rules
    # --------------------------------------------------------

    description = normalized["description"].lower()

    if (
        "free-text" in description
        or "comments" in description
    ):
        normalized["type"] = "text"

    # --------------------------------------------------------
    # Policy requirements
    # --------------------------------------------------------

    if "Policy requirement" in rule:
        normalized["type"] = "requirement"

    return normalized


NORMALIZED_RULES = {
    rule_id: normalize_rule(rule_id, rule)
    for rule_id, rule in RULES.items()
}


# ============================================================
# VALUE CHECK
# ============================================================

def has_value(row, field):

    if field not in row.index:
        return False

    value = row[field]

    if pd.isna(value):
        return False

    return bool(str(value).strip())


# ============================================================
# GENERIC RULE EVALUATION
# ============================================================

def evaluate_rule(row, rule_id, rule):

    execution = rule.get("execution")

    # ========================================================
    # JSON-DEFINED EXECUTION
    # ========================================================

    if execution:

        execution_type = execution.get("type")

        # ----------------------------------------------------
        # FIELD RULE
        # ----------------------------------------------------

        if execution_type == "field":

            field_groups = execution.get("fields", [])

            for group in field_groups:

                if isinstance(group, str):
                    group = [group]

                if any(
                    has_value(row, field)
                    for field in group
                ):
                    return True

            return False

        # ----------------------------------------------------
        # COMBINATION RULE
        # ----------------------------------------------------

        if execution_type == "combination":

            field_groups = execution.get("fields", [])

            if not field_groups:
                return False

            # Every group represents one required concept.
            #
            # Example:
            #
            # [
            #   ["customer_name", "full_name"],
            #   ["dob", "date_of_birth"]
            # ]
            #
            # At least one field from EACH group
            # must contain a value.

            for group in field_groups:

                if isinstance(group, str):
                    group = [group]

                group_matched = False

                for field in group:

                    if has_value(row, field):
                        group_matched = True
                        break

                if not group_matched:
                    return False

            return True

        # ----------------------------------------------------
        # TEXT RULE
        # ----------------------------------------------------

        if execution_type == "text":

            field_groups = execution.get("fields", [])
            patterns = execution.get("patterns", [])

            text_fields = []

            for group in field_groups:

                if isinstance(group, str):
                    group = [group]

                text_fields.extend(group)

            for field in text_fields:

                if field not in row.index:
                    continue

                if not has_value(row, field):
                    continue

                value = str(row[field])

                for pattern in patterns:

                    try:
                        if re.search(pattern, value):
                            return True

                    except re.error as error:
                        print(
                            f"Invalid regex in {rule_id}: {error}"
                        )

            return False

    # ========================================================
    # GENERIC FALLBACK FOR EXAMPLES
    # ========================================================

    if rule.get("type") == "field":

        fields = rule.get("fields", [])

        for field in fields:

            if has_value(row, field):
                return True

        return False

    return False


# ============================================================
# EXTRACT DECISION
# ============================================================

def extract_outcome(outcome_text):

    if not outcome_text:
        return None

    text = str(outcome_text).upper().strip()

    if "EXCEPTION APPROVED" in text:
        return "EXCEPTION APPROVED"

    if "BLOCK" in text:
        return "BLOCK"

    if "FLAG" in text:
        return "FLAG"

    if "PASS" in text:
        return "PASS"

    return None


# ============================================================
# CHECK ONE RECORD
# ============================================================

def check_record(row):

    triggered = []

    # --------------------------------------------------------
    # Evaluate every executable rule
    # --------------------------------------------------------

    for rule_id, rule in NORMALIZED_RULES.items():

        if rule.get("type") == "requirement":
            continue

        if evaluate_rule(row, rule_id, rule):
            triggered.append(rule_id)

    # --------------------------------------------------------
    # No rule triggered
    # --------------------------------------------------------

    if not triggered:

        return [
            "PASS",
            "",
            "No policy rules triggered",
            "No action required",
        ]

    # --------------------------------------------------------
    # Collect outcomes
    # --------------------------------------------------------

    outcomes = []

    for rule_id in triggered:

        outcome = extract_outcome(
            NORMALIZED_RULES[rule_id]["outcome"]
        )

        if outcome:
            outcomes.append(outcome)

    # --------------------------------------------------------
    # Overall decision
    # --------------------------------------------------------

    if "BLOCK" in outcomes:
        overall_outcome = "BLOCK"

    elif "FLAG" in outcomes:
        overall_outcome = "FLAG"

    elif "EXCEPTION APPROVED" in outcomes:
        overall_outcome = "EXCEPTION APPROVED"

    else:
        overall_outcome = "FLAG"

    # --------------------------------------------------------
    # Reasons
    # --------------------------------------------------------

    reasons = []

    for rule_id in triggered:

        description = NORMALIZED_RULES[
            rule_id
        ].get("description", "")

        if description:
            reasons.append(
                f"{rule_id}: {description}"
            )
        else:
            reasons.append(rule_id)

    reason = "; ".join(
        dict.fromkeys(reasons)
    )

    # --------------------------------------------------------
    # Remediation
    # --------------------------------------------------------

    remediation = []

    for rule_id in triggered:

        raw_rule = NORMALIZED_RULES[
            rule_id
        ]["raw"]

        value = (
            raw_rule.get("Remediation")
            or raw_rule.get("remediation")
            or raw_rule.get("Policy expectation")
            or raw_rule.get("Required action")
        )

        if value:
            remediation.append(str(value))

    remediation = "; ".join(
        dict.fromkeys(remediation)
    )

    if not remediation:
        remediation = (
            "Review and remediate according to policy."
        )

    return [
        overall_outcome,
        "; ".join(triggered),
        reason,
        remediation,
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    print(f"Input dataset: {INPUT}")
    print(f"Policy file: {POLICY_FILE}")

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT}"
        )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_excel(INPUT)

    print(f"Records loaded: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # --------------------------------------------------------
    # Evaluate records
    # --------------------------------------------------------

    results = df.apply(
        check_record,
        axis=1,
        result_type="expand",
    )

    results.columns = [
        "expected_outcome",
        "expected_rule_triggers",
        "expected_reason",
        "suggested_remediation",
    ]

    # --------------------------------------------------------
    # Add results
    # --------------------------------------------------------

    df[
        [
            "expected_outcome",
            "expected_rule_triggers",
            "expected_reason",
            "suggested_remediation",
        ]
    ] = results

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Save Excel
    # --------------------------------------------------------

    df.to_excel(
        OUTPUT,
        index=False,
    )

    # --------------------------------------------------------
    # Format Excel
    # --------------------------------------------------------

    workbook = load_workbook(OUTPUT)
    worksheet = workbook.active

    for cell in worksheet[1]:

        cell.font = Font(bold=True)

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for column in worksheet.columns:

        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:

            if cell.value is not None:

                max_length = max(
                    max_length,
                    len(str(cell.value)),
                )

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max_length + 2,
            60,
        )

    workbook.save(OUTPUT)

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("Policy evaluation complete!")
    print(f"Output: {OUTPUT}")

    print()
    print("Outcome summary:")

    print(
        df["expected_outcome"].value_counts()
    )

    # --------------------------------------------------------
    # Rule summary
    # --------------------------------------------------------

    rule_counts = {}

    for value in df[
        "expected_rule_triggers"
    ].dropna():

        if not str(value).strip():
            continue

        for rule_id in str(value).split(";"):

            rule_id = rule_id.strip()

            if not rule_id:
                continue

            rule_counts[rule_id] = (
                rule_counts.get(rule_id, 0) + 1
            )

    print()
    print("Rule summary:")

    if rule_counts:

        rule_summary = pd.Series(
            rule_counts
        ).sort_values(
            ascending=False
        )

        print(rule_summary)

    else:

        print("No rules triggered.")


if __name__ == "__main__":
    main()