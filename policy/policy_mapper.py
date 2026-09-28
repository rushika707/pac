import re


SEMANTIC_ALIASES = {
    "full_name": [
        "full name", "customer name", "person name",
        "client name"
    ],

    "dob": [
        "date of birth", "dob", "birth date", "birthdate"
    ],

    "email": [
        "personal email", "personal email address",
        "email", "email address", "contact email"
    ],

    "phone": [
        "phone", "phone number", "mobile",
        "mobile number", "telephone", "telephone number"
    ],

    "address": [
        "postal address",
        "postal/home address",
        "home address",
        "street address",
        "residential address",
        "delivery address"
    ],

    "postcode": [
        "postcode", "postal code", "zip", "zip code"
    ],

    "gender": [
        "gender", "sex"
    ],

    "ni_number": [
        "ni number", "national insurance number", "nino"
    ],

    "passport_number": [
        "passport", "passport number"
    ],

    "driving_licence_number": [
        "driving licence", "driving licence number",
        "driving license", "driving license number",
        "licence number", "license number"
    ],

    "government_id": [
        "government issued identifier",
        "government-issued identifier",
        "government identifier",
        "national id", "national identifier",
        "tax id", "tax identifier"
    ],

    "bank_account": [
        "bank account", "bank account number",
        "bank account details"
    ],

    "account_number": [
        "account number", "customer account number",
        "customer account id", "customer account identifier"
    ],

    "credit_card_number": [
        "credit card", "credit card number",
        "debit card", "payment card", "card number"
    ],

    "payment_information": [
        "payment information", "payment token",
        "payment details"
    ],

    "ip_address": [
        "ip address", "ip_address",
        "internet protocol address"
    ],

    "device_id": [
        "device id", "device identifier",
        "device identification"
    ],

    "cookie_id": [
        "cookie id", "cookie identifier"
    ],

    "advertising_id": [
        "advertising id", "advertising identifier"
    ],

    "medical_condition": [
        "medical condition", "health",
        "health condition", "diagnosis", "treatment",
        "disability", "disability information"
    ],

    "financial_difficulty": [
        "financial difficulty", "financial hardship",
        "arrears status", "vulnerability flag",
        "financial vulnerability"
    ],

    "location_history": [
        "location history", "precise location history",
        "gps trace", "gps history",
        "precise coordinates", "exact location history"
    ],

    "authentication_secret": [
        "password", "security answer",
        "authentication secret", "authentication secrets",
        "security secret"
    ],

    "fraud_investigation": [
        "fraud investigation", "fraud investigation information",
        "fraud case notes", "investigation details",
        "suspicious activity notes"
    ],

    "biometric": [
        "biometric information", "biometric",
        "voiceprint", "face template",
        "faceprint", "fingerprint template",
        "fingerprint", "iris scan", "dna profile"
    ],

    "ethnicity": [
        "ethnicity", "race", "racial origin"
    ],

    "religion": [
        "religion", "religious belief", "belief"
    ],

    "political_view": [
        "political opinion", "political view",
        "party preference"
    ],

    "employee_id": [
        "employee id", "employee identifier",
        "employee number"
    ],

    "department": [
        "department", "business unit", "team"
    ],

    "job_role": [
        "job role", "job title", "position"
    ],

    "customer_id": [
        "customer id", "customer identifier",
        "client id", "client identifier",
        "user id", "user identifier"
    ],

    "account_balance": [
        "account balance"
    ],

    "account_event_details": [
        "account event", "account event details",
        "account activity", "transaction details",
        "transaction event", "transaction history"
    ],

    "complaint_support_case": [
        "complaint", "complaint details",
        "support case", "support case details",
        "customer support", "case details"
    ],

    "timestamp": [
        "timestamp", "time stamp", "date and time"
    ],

    "free_text": [
        "free text", "free-text", "comment",
        "comments", "notes", "feedback",
        "description"
    ],
}



def normalize(text):
    text = str(text).lower()
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def semantic_concept(text):
    """
    Map policy wording to a semantic concept.
    Uses exact word-boundary matching and avoids generic
    substring matches.
    """

    normalized = normalize(text)
    matches = []

    for concept, aliases in SEMANTIC_ALIASES.items():

        for alias in [concept] + aliases:

            alias = normalize(alias)

            if not alias:
                continue

            pattern = (
                r"(?<!\\w)"
                + re.escape(alias)
                + r"(?!\\w)"
            )

            if not re.search(pattern, normalized):
                continue

            # Generic "address" must not be inferred from
            # phrases such as "email address".
            if concept == "address":
                if not any(
                    phrase in normalized
                    for phrase in [
                        "postal address",
                        "postal home address",
                        "home address",
                        "street address",
                        "residential address",
                        "delivery address",
                    ]
                ):
                    continue

            matches.append(
                (len(alias), concept)
            )

    if not matches:
        return None

    matches.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return matches[0][1]


def map_fields(fields):
    """
    Convert arbitrary policy fields into semantic concepts.
    """

    mapped = []

    for field in fields:
        if not isinstance(field, str):
            continue

        concept = semantic_concept(field)

        mapped.append({
            "original": field,
            "semantic": concept,
        })

    return mapped


def dataset_columns_for_concept(concept):
    """
    Map semantic meaning to the current synthetic dataset.
    """

    mapping = {
        "full_name": ["customer_name"],
        "dob": ["dob"],
        "email": ["email"],
        "phone": ["phone"],
        "address": ["address"],
        "postcode": [],
        "gender": ["gender"],

        "ni_number": ["ni_number"],
        "passport_number": ["passport_number"],
        "driving_licence_number": [],
        "government_id": [],

        "bank_account": ["bank_account"],
        "account_number": [],
        "credit_card_number": ["credit_card_number"],
        "payment_information": [],

        "ip_address": ["ip_address"],
        "device_id": [],
        "cookie_id": [],
        "advertising_id": [],

        "medical_condition": ["medical_condition"],
        "financial_difficulty": [],
        "location_history": [],
        "authentication_secret": [],
        "fraud_investigation": [],
        "biometric": [],

        "ethnicity": ["ethnicity"],
        "religion": ["religion"],
        "political_view": ["political_view"],

        "employee_id": ["employee_id"],
        "department": ["department"],
        "job_role": ["job_role"],
        "customer_id": ["customer_id"],

        "account_balance": [],
        "account_event_details": [],
        "complaint_support_case": [],
        "timestamp": [],

        "free_text": ["feedback"],
    }

    return mapping.get(concept, [])

def map_policy(policy, dataset_columns):
    """
    Map policy semantics to the available dataset columns.
    Does NOT modify the original policy.
    """

    mapped_policy = {}

    def walk(value):
        if isinstance(value, dict):
            result = {}

            rule_id = (
                value.get("rule_id")
                or value.get("Rule ID")
                or value.get("ID")
            )

            for key, child in value.items():
                result[key] = walk(child)

            if rule_id:
                description = (
                    value.get("description")
                    or value.get("Description")
                    or value.get("PII type")
                    or value.get("Sensitive data type")
                    or value.get("Combination rule")
                    or value.get("Policy statement")
                    or ""
                )

                examples = (
                    value.get("examples")
                    or value.get("Examples")
                    or []
                )

                if isinstance(examples, str):
                    examples = [examples]

                concepts = []

                # Prefer explicit examples.
                # For combination rules, parse every component
                # from the policy description.

                concepts = []

                if examples:
                    phrases = [str(x) for x in examples]
                else:
                    description_text = str(description)

                    phrases = re.split(
                        r"\s*\+\s*",
                        description_text,
                        flags=re.IGNORECASE,
                    )

                for phrase in phrases:

                    phrase = phrase.strip()

                    if not phrase:
                        continue

                    concept = semantic_concept(phrase)

                    if concept and concept not in concepts:
                        concepts.append(concept)

                resolved = {}

                for concept in concepts:
                    columns = dataset_columns_for_concept(concept)

                    resolved[concept] = [
                        column
                        for column in columns
                        if column in dataset_columns
                    ]

                result["_mapping"] = {
                    "semantic_concepts": concepts,
                    "dataset_columns": resolved,
                }

            return result

        if isinstance(value, list):
            return [walk(item) for item in value]

        return value

    mapped_policy = walk(policy)

    return mapped_policy