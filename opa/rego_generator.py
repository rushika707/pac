import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
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


def get_description(rule):
    for key in (
        "description",
        "Description",
        "PII type",
        "Sensitive data type",
        "Combination rule",
    ):
        value = rule.get(key)

        if value:
            return str(value).strip()

    return ""


def extract_outcome(rule):
    text = str(
        rule.get("Required policy outcome")
        or rule.get("Required outcome")
        or rule.get("outcome")
        or rule.get("Outcome")
        or ""
    ).upper()

    if "EXCEPTION APPROVED" in text:
        return "EXCEPTION APPROVED"

    if "BLOCK" in text:
        return "BLOCK"

    if "FLAG" in text:
        return "FLAG"

    if "PASS" in text:
        return "PASS"

    return "FLAG"


def normalize_text(value):
    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


# ============================================================
# POLICY CONCEPT VOCABULARY
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

def resolve_concept_fields(concept):
    """
    Resolve policy concepts/examples to actual dataset columns.
    """

    concept = normalize_text(concept)

    FIELD_MAP = {
        # Direct PII
        "full name": ["customer_name"],
        "customer name": ["customer_name"],
        "first name": ["customer_name"],
        "last name": ["customer_name"],
        "name": ["customer_name"],

        "date of birth": ["dob"],
        "dob": ["dob"],

        "personal email address": ["email"],
        "personal email": ["email"],
        "email address": ["email"],
        "email": ["email"],
        "contact email": ["email"],

        "phone number": ["phone"],
        "phone": ["phone"],
        "mobile": ["phone"],
        "mobile number": ["phone"],
        "telephone": ["phone"],
        "telephone number": ["phone"],

        "postal address": ["address"],
        "home address": ["address"],
        "address": ["address"],
        "street": ["address"],
        "street address": ["address"],

        "postcode": [],
        "postal code": [],
        "zip": [],
        "zip code": [],

        "ni number": ["ni_number"],
        "nino": ["ni_number"],

        "passport number": ["passport_number"],

        "driving licence number": [],

        "bank account": ["bank_account"],
        "sort code": [],
        "credit card number": ["credit_card_number"],

        "ip address": ["ip_address"],
        "device id": [],
        "cookie id": [],
        "user id": ["customer_id"],

        # Sensitive PII
        "medical condition": ["medical_condition"],
        "diagnosis": ["medical_condition"],
        "treatment": ["medical_condition"],
        "disability information": ["medical_condition"],

        "ethnicity": ["ethnicity"],
        "race": ["ethnicity"],
        "racial origin": ["ethnicity"],

        "religion": ["religion"],
        "belief": ["religion"],

        "political view": ["political_view"],
        "party preference": ["political_view"],

        "trade union": [],
        "union member": [],

        "faceprint": [],
        "fingerprint": [],
        "iris scan": [],
        "dna profile": [],

        # Combination concepts
        "gender": ["gender"],
        "sex": ["gender"],

        "employee id": ["employee_id"],
        "employee identifier": ["employee_id"],
        "employee number": ["employee_id"],

        "department": ["department"],
        "business unit": ["department"],
        "team": ["department"],

        "role": ["job_role"],
        "job role": ["job_role"],
        "job title": ["job_role"],
        "position": ["job_role"],

        "customer id": ["customer_id"],
        "customer identifier": ["customer_id"],
        "client id": ["customer_id"],
        "client identifier": ["customer_id"],

        # Account-event fields are absent from current dataset
        "account event details": [],
        "account event": [],
        "account activity": [],
        "account details": [],
        "transaction details": [],

        # Free text
        "free text": ["feedback"],
        "comments": ["feedback"],
        "comment": ["feedback"],
        "notes": ["feedback"],
        "feedback": ["feedback"],
        "description": ["feedback"],
        "text": ["feedback"],
    }

    if concept in FIELD_MAP:
        return FIELD_MAP[concept]

    for canonical, aliases in CONCEPT_ALIASES.items():
        vocabulary = {
            normalize_text(canonical),
            *(normalize_text(alias) for alias in aliases),
        }

        if concept in vocabulary:
            return FIELD_MAP.get(
                normalize_text(canonical),
                []
            )

    return []


# ============================================================
# REGO HELPERS
# ============================================================

def generate_helpers(lines):

    lines.extend([
        "# ==================================================",
        "# Generic helpers",
        "# ==================================================",
        "",

        "has_value(field) if {",
        '    value := object.get(input.record, field, "")',
        "    value != null",
        '    value != ""',
        "}",
        "",

        "has_any(fields) if {",
        "    some i",
        "    field := fields[i]",
        "    has_value(field)",
        "}",
        "",

        "all_groups_present(groups) if {",
        "    every group in groups {",
        "        some i",
        "        field := group[i]",
        "        has_value(field)",
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
    ])


# ============================================================
# FIELD CONDITION
# ============================================================

def generate_field_condition(fields):

    resolved = []

    for field in fields:

        if isinstance(field, str):
            resolved.extend(
                resolve_concept_fields(field)
            )

    resolved = sorted(
        set(resolved)
    )

    if not resolved:
        return "false"

    return f"has_any({json.dumps(resolved)})"


# ============================================================
# COMBINATION DESCRIPTION
# ============================================================

def split_combination_description(description):

    # Remove qualifying text such as:
    #
    # "where linkable to a person"
    #
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


def generate_combination_condition(description):

    concepts = split_combination_description(
        description
    )

    if not concepts:
        return "false"

    groups = []

    for concept in concepts:

        # Support:
        #
        # postal address or postcode
        #
        alternatives = re.split(
            r"\s+\bor\b\s+",
            concept,
            flags=re.IGNORECASE,
        )

        group = []

        for alternative in alternatives:

            alternative = alternative.strip()

            if not alternative:
                continue

            group.extend(
                resolve_concept_fields(
                    alternative
                )
            )

        group = sorted(
            set(group)
        )

        if not group:
            return "false"

        groups.append(group)

    return (
        "all_groups_present("
        + json.dumps(groups)
        + ")"
    )


# ============================================================
# TEXT CONDITION
# ============================================================

def generate_text_condition(rule):

    execution = rule.get(
        "execution",
        {}
    )

    fields = execution.get(
        "fields",
        []
    )

    patterns = execution.get(
        "patterns",
        []
    )

    resolved_fields = []

    for group in fields:

        if isinstance(group, str):
            group = [group]

        for field in group:
            resolved_fields.extend(
                resolve_concept_fields(field)
            )

    resolved_fields = sorted(
        set(resolved_fields)
    )

    if not resolved_fields:
        return "false"

    return (
        "text_matches("
        + json.dumps(resolved_fields)
        + ", "
        + json.dumps(patterns)
        + ")"
    )


# ============================================================
# RULE CONDITION
# ============================================================

def generate_condition(rule):

    execution = rule.get(
        "execution",
        {}
    )

    execution_type = execution.get(
        "type"
    )

    # --------------------------------------------------------
    # Policy-defined execution
    # --------------------------------------------------------

    if execution_type == "field":

        return generate_field_condition(
            execution.get(
                "fields",
                []
            )
        )

    if execution_type == "combination":

        fields = execution.get(
            "fields",
            []
        )

        if fields:
            groups = []

            for group in fields:

                if isinstance(group, str):
                    group = [group]

                resolved_group = []

                for field in group:
                    resolved_group.extend(
                        resolve_concept_fields(field)
                    )

                groups.append(
                    sorted(set(resolved_group))
                )

            return (
                "all_groups_present("
                + json.dumps(groups)
                + ")"
            )

        # No machine-readable execution.
        # Fall back to policy description.

        return generate_combination_condition(
            get_description(rule)
        )

    if execution_type == "text":

        return generate_text_condition(
            rule
        )

    # --------------------------------------------------------
    # Description-based combination
    # --------------------------------------------------------

    description = get_description(rule)

    if "+" in description:

        return generate_combination_condition(
            description
        )

    # --------------------------------------------------------
    # Example-based field rule
    # --------------------------------------------------------

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

    if examples:

        return generate_field_condition(
            examples
        )

    # --------------------------------------------------------
    # Free-text policy rule
    # --------------------------------------------------------

    normalized_description = normalize_text(description)

    if (
        "free text" in normalized_description
        or "comments" in normalized_description
        or "personal identifiers" in normalized_description
    ):
        return (
            "text_matches("
            + json.dumps(["feedback"])
            + ", "
            + json.dumps([
                r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
                r"(?i)\b(?:\+44|0)\d{9,10}\b",
                r"\b(?:\d[ -]?){13,19}\b",
                r"\b[A-Z]{2}\d{6}[A-Z]?\b",
            ])
            + ")"
        )

    # --------------------------------------------------------
    # No executable representation
    # --------------------------------------------------------

    return "false"


# ============================================================
# GENERATE REGO
# ============================================================

def generate(policy):

    rules = extract_rules(policy)

    lines = [
        "package generated_policy",
        "",
        'default decision := "PASS"',
        "",
    ]

    generate_helpers(lines)

    lines.extend([
        "# ==================================================",
        "# Rule triggers",
        "# ==================================================",
        "",
    ])

    generated_rules = []

    for rule_id, rule in rules.items():

        safe_id = re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            rule_id,
        )

        condition = generate_condition(
            rule
        )

        outcome = extract_outcome(
            rule
        )

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

    # ========================================================
    # Triggered rules
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Triggered rules",
        "# ==================================================",
        "",
    ])

    for rule in generated_rules:

        lines.extend([
            (
                f'triggered_rules contains '
                f'{json.dumps(rule["id"])} if {{'
            ),
            f'    trigger_{rule["safe_id"]}',
            "}",
            "",
        ])

    # ========================================================
    # Outcome flags
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Outcome flags",
        "# ==================================================",
        "",
        "default has_block := false",
        "default has_flag := false",
        "default has_exception := false",
        "",
    ])

    for rule in generated_rules:

        if rule["outcome"] == "BLOCK":

            lines.extend([
                "has_block if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

        elif rule["outcome"] == "FLAG":

            lines.extend([
                "has_flag if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

        elif rule["outcome"] == "EXCEPTION APPROVED":

            lines.extend([
                "has_exception if {",
                f'    trigger_{rule["safe_id"]}',
                "}",
                "",
            ])

    # ========================================================
    # Final decision
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Final decision",
        "# ==================================================",
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
    ])

    # ========================================================
    # Final result
    # ========================================================

    lines.extend([
        "# ==================================================",
        "# Final result",
        "# ==================================================",
        "",

        "result := {",
        '    "decision": decision,',
        (
            '    "triggered_rules": '
            '[rule | triggered_rules[rule]]'
        ),
        "}",
    ])

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    policy = load_policy()

    rego = generate(
        policy
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            rego
        )

    print(
        f"Generated: {OUTPUT_FILE}"
    )