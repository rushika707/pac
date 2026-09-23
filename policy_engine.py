import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment

from policy.policy_loader import load_policy


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parent

INPUT = BASE / "generated_data" / "synthetic_data.xlsx"
OUTPUT = BASE / "policy-dashboard" / "public" / "policy_results.xlsx"
POLICY_FILE = BASE / "policy" / "policy.json"


# ============================================================
# LOAD POLICY
# ============================================================

policy = load_policy(POLICY_FILE)


# ============================================================
# GENERIC POLICY EXTRACTION
# ============================================================

def extract_rules(policy):
    rules = {}

    def walk(value):
        if isinstance(value, dict):

            rule_id = (
                value.get("rule_id")
                or value.get("Rule ID")
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


def extract_decisions(policy):
    decisions = {}

    def walk(value):
        if isinstance(value, dict):

            for key in ("Decision", "decision"):
                if key in value:
                    decision = str(value[key]).strip()
                    decisions[decision] = value

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(policy)

    return decisions


RULES = extract_rules(policy)
DECISIONS = extract_decisions(policy)

print(f"Loaded executable rules: {len(RULES)}")

print("Loaded decisions:")
for decision in DECISIONS:
    print(f"  {decision}")


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_column_name(value):
    return normalize_text(value)


# ============================================================
# GENERIC CONCEPT ALIASES
#
# These are semantic vocabulary mappings, NOT policy-rule
# mappings. They allow policy concepts to resolve to dataset
# columns without modifying policy.json.
# ============================================================
CONCEPT_ALIASES = {
    "full name": [
        "full name",
        "customer name",
        "customer_name",
        "name",
        "person name",
        "client name",
    ],

    "date of birth": [
        "date of birth",
        "dob",
        "birth date",
        "birthdate",
    ],

    "personal email address": [
        "personal email address",
        "personal email",
        "email address",
        "email",
        "contact email",
    ],

    "phone number": [
        "phone number",
        "phone",
        "mobile",
        "mobile number",
        "telephone",
        "telephone number",
    ],

    "postal address": [
        "postal address",
        "postal/home address",
        "home address",
        "address",
        "street address",
    ],

    "postcode": [
        "postcode",
        "postal code",
        "zip code",
        "zip",
    ],

    "gender": [
        "gender",
        "sex",
    ],

    "employee id": [
        "employee id",
        "employee identifier",
        "employee number",
    ],

    "department": [
        "department",
        "business unit",
        "team",
    ],

    "role": [
        "role",
        "job role",
        "job_role",
        "job title",
        "position",
    ],

    "customer id": [
        "customer id",
        "customer identifier",
        "client id",
        "client identifier",
        "user id",
        "user identifier",
    ],

    "account event details": [
        "account event details",
        "account event",
        "transaction details",
        "account activity",
        "account details",
    ],

    "free text": [
        "free text",
        "free-text",
        "comments",
        "comment",
        "notes",
        "feedback",
        "description",
        "text",
    ],
}


def build_dataset_columns(row):
    return {
        normalize_column_name(column): column
        for column in row.index
    }


def resolve_concept_columns(concept, row):
    """
    Resolve a policy concept to actual dataset columns.
    """

    concept = normalize_text(concept)

    dataset_columns = {
        normalize_column_name(column): column
        for column in row.index
    }

    candidates = []

    # --------------------------------------------------------
    # Direct dataset column
    # --------------------------------------------------------

    if concept in dataset_columns:
        candidates.append(
            dataset_columns[concept]
        )

    # --------------------------------------------------------
    # Search every semantic alias group
    # --------------------------------------------------------

    for canonical, aliases in CONCEPT_ALIASES.items():

        vocabulary = [
            canonical,
            *aliases,
        ]

        normalized_vocabulary = {
            normalize_text(item)
            for item in vocabulary
        }

        if concept not in normalized_vocabulary:
            continue

        for alias in normalized_vocabulary:

            if alias in dataset_columns:
                candidates.append(
                    dataset_columns[alias]
                )

    return list(
        dict.fromkeys(candidates)
    )


# ============================================================
# RULE NORMALIZATION
# ============================================================

def get_rule_description(rule):
    for key in (
        "description",
        "Description",
        "PII type",
        "Sensitive data type",
        "Combination rule",
        "Policy statement",
    ):
        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


def get_rule_outcome(rule):
    for key in (
        "outcome",
        "Outcome",
        "Required outcome",
        "Required policy outcome",
    ):
        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


def get_examples(rule):
    value = (
        rule.get("examples")
        or rule.get("Examples")
        or []
    )

    if isinstance(value, str):
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return []


def normalize_rule(rule_id, rule):

    description = get_rule_description(rule)
    examples = get_examples(rule)

    execution = rule.get("execution", {})

    normalized = {
        "rule_id": rule_id,
        "description": description,
        "examples": examples,
        "outcome": get_rule_outcome(rule),
        "execution": execution,
        "raw": rule,
        "type": "unknown",
    }

    # Existing execution supplied by policy extraction
    if isinstance(execution, dict) and execution.get("type"):
        normalized["type"] = execution["type"]
        return normalized

    description_lower = description.lower()

    # Combination rules are identified from their structure,
    # not from their rule ID.
    if "+" in description:
        normalized["type"] = "combination"
        return normalized

    # Text rules
    if any(
        phrase in description_lower
        for phrase in (
            "free-text",
            "free text",
            "comments containing",
            "text containing",
            "notes containing",
        )
    ):
        normalized["type"] = "text"
        return normalized

    # Example-based field rule
    if examples:
        normalized["type"] = "field"
        return normalized

    return normalized


NORMALIZED_RULES = {
    rule_id: normalize_rule(rule_id, rule)
    for rule_id, rule in RULES.items()
}


# ============================================================
# VALUE CHECK
# ============================================================

def has_value(row, column):
    if column not in row.index:
        return False

    value = row[column]

    if pd.isna(value):
        return False

    return bool(str(value).strip())


# ============================================================
# EXECUTION DEFINED BY POLICY JSON
# ============================================================

def evaluate_execution(row, rule):

    execution = rule.get("execution")

    if not isinstance(execution, dict):
        return None

    execution_type = execution.get("type")

    # --------------------------------------------------------
    # FIELD
    # --------------------------------------------------------

    if execution_type == "field":

        fields = execution.get("fields", [])

        for group in fields:

            if isinstance(group, str):
                group = [group]

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                if any(
                    has_value(row, column)
                    for column in resolved
                ):
                    return True

        return False

    # --------------------------------------------------------
    # COMBINATION
    # --------------------------------------------------------

    if execution_type == "combination":

        groups = execution.get("fields", [])

        if not groups:
            return False

        for group in groups:

            if isinstance(group, str):
                group = [group]

            group_found = False

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                if any(
                    has_value(row, column)
                    for column in resolved
                ):
                    group_found = True
                    break

            if not group_found:
                return False

        return True

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if execution_type == "text":

        fields = execution.get("fields", [])
        patterns = execution.get("patterns", [])

        for group in fields:

            if isinstance(group, str):
                group = [group]

            for field in group:

                resolved = resolve_concept_columns(
                    field,
                    row,
                )

                for column in resolved:

                    if not has_value(row, column):
                        continue

                    value = str(row[column])

                    for pattern in patterns:

                        try:
                            if re.search(
                                pattern,
                                value,
                                flags=re.IGNORECASE,
                            ):
                                return True

                        except re.error as error:
                            print(
                                f"Invalid regex in "
                                f"{rule['rule_id']}: {error}"
                            )

        return False

    return None


# ============================================================
# GENERIC DESCRIPTION PARSER FOR COMBINATION RULES
# ============================================================

def split_combination_description(description):
    """
    Extract the required concepts from a policy combination
    description while ignoring qualifying text.
    """

    description = re.sub(
        r"\s+where\s+.*$",
        "",
        description,
        flags=re.IGNORECASE,
    )

    parts = re.split(
        r"\s*\+\s*",
        description,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]
def concept_present(row, concept):

    alternatives = re.split(
        r"\s+\bor\b\s+",
        concept,
        flags=re.IGNORECASE,
    )

    for alternative in alternatives:

        alternative = alternative.strip()

        if not alternative:
            continue

        columns = resolve_concept_columns(
            alternative,
            row,
        )

        if any(
            has_value(row, column)
            for column in columns
        ):
            return True

    return False
def evaluate_description_combination(row, description):

    concepts = split_combination_description(
        description
    )

    if not concepts:
        return False

    # Every concept must be present.
    for concept in concepts:

        if not concept_present(row, concept):
            return False

    return True


# ============================================================
# GENERIC TEXT DETECTION
# ============================================================

def detect_personal_data_in_text(value):

    if value is None:
        return False

    text = str(value).strip()

    if not text:
        return False

    patterns = [

        # Email
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",

        # Phone
        r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",

        # IP address
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",

        # NI-like identifier
        r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{6}\s?[A-D]\b",

        # Passport-like alphanumeric identifier
        r"\b[A-Z]{1,2}\d{6,9}\b",

        # Credit/payment-card-like number
        r"\b(?:\d[ -]?){13,19}\b",
    ]

    for pattern in patterns:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def evaluate_text_rule(row, rule):

    description = rule.get(
        "description",
        "",
    ).lower()

    # Prefer explicitly declared execution fields.
    execution_result = evaluate_execution(
        row,
        rule,
    )

    if execution_result is not None:
        return execution_result

    # Otherwise inspect fields semantically mentioned by
    # the policy description.
    text_candidates = []

    for column in row.index:

        normalized_column = normalize_column_name(
            column
        )

        if any(
            token in normalized_column
            for token in (
                "feedback",
                "comment",
                "note",
                "description",
                "text",
            )
        ):
            text_candidates.append(column)

    # If policy says free-text/comments but the dataset has
    # no corresponding text field, it is not applicable.
    if not text_candidates:
        return False

    for column in text_candidates:

        if not has_value(row, column):
            continue

        if detect_personal_data_in_text(
            row[column]
        ):
            return True

    return False


# ============================================================
# GENERIC RULE EVALUATION
# ============================================================

def evaluate_rule(row, rule):

    # --------------------------------------------------------
    # Policy-defined execution
    # --------------------------------------------------------

    execution_result = evaluate_execution(
        row,
        rule,
    )

    if execution_result is not None:
        return execution_result

    # --------------------------------------------------------
    # Combination described directly in policy
    # --------------------------------------------------------

    if rule.get("type") == "combination":

        return evaluate_description_combination(
            row,
            rule.get("description", ""),
        )

    # --------------------------------------------------------
    # Text rule
    # --------------------------------------------------------

    if rule.get("type") == "text":

        return evaluate_text_rule(
            row,
            rule,
        )

    # --------------------------------------------------------
    # Example-based field rule
    # --------------------------------------------------------

    if rule.get("type") == "field":

        for example in rule.get("examples", []):

            resolved_columns = resolve_concept_columns(
                example,
                row,
            )

            if any(
                has_value(row, column)
                for column in resolved_columns
            ):
                return True

        return False

    return False


# ============================================================
# OUTCOME
# ============================================================

def extract_outcome(outcome_text):

    if not outcome_text:
        return None

    text = str(
        outcome_text
    ).upper().strip()

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
# RECORD EVALUATION
# ============================================================

def check_record(row):

    triggered = []

    # --------------------------------------------------------
    # Evaluate all executable rules
    # --------------------------------------------------------

    for rule_id, rule in NORMALIZED_RULES.items():

        if rule.get("type") == "requirement":
            continue

        if evaluate_rule(
            row,
            rule,
        ):
            triggered.append(rule_id)

    # --------------------------------------------------------
    # No triggered rules
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
            NORMALIZED_RULES[
                rule_id
            ].get("outcome")
        )

        if outcome:
            outcomes.append(outcome)

    # --------------------------------------------------------
    # Overall outcome
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
        ].get("raw", {})

        value = (
            raw_rule.get("Remediation")
            or raw_rule.get("remediation")
            or raw_rule.get("Policy expectation")
            or raw_rule.get("Required action")
        )

        if value:
            remediation.append(
                str(value)
            )

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
    # Evaluate
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
    # Preserve original dataset columns
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
    # Save
    # --------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for column in worksheet.columns:

        max_length = 0
        column_letter = (
            column[0].column_letter
        )

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

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("Policy evaluation complete!")
    print(f"Output: {OUTPUT}")

    print()
    print("Outcome summary:")

    print(
        df[
            "expected_outcome"
        ].value_counts()
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

        for rule_id in str(
            value
        ).split(";"):

            rule_id = rule_id.strip()

            if not rule_id:
                continue

            rule_counts[rule_id] = (
                rule_counts.get(
                    rule_id,
                    0,
                ) + 1
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