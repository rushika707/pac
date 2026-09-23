package generated_policy

default decision := "PASS"

# ================================================
# Generic helpers
# ================================================

has_value(field) if {
    value := object.get(input.record, field, "")
    value != null
    value != ""
}

has_any(groups) if {
    some i
    some j
    has_value(groups[i][j])
}

all_groups_present(groups) if {
    every group in groups {
        some i
        has_value(group[i])
    }
}

text_matches(fields, patterns) if {
    some i
    some j
    field := fields[i]
    pattern := patterns[j]
    value := object.get(input.record, field, "")
    value != null
    value != ""
    regex.match(pattern, value)
}

# ================================================
# Rule triggers
# ================================================

trigger_PII_01 if {
    has_any([["first_name", "last_name"], ["full_name", "customer_name"]])
}

trigger_PII_02 if {
    has_any([["email", "personal_email"], ["contact_email"]])
}

trigger_PII_03 if {
    has_any([["mobile", "telephone"], ["phone_number"]])
}

trigger_PII_04 if {
    has_any([["address", "home_address"], ["street", "postcode with address"]])
}

trigger_PII_05 if {
    has_any([["ni_number", "nino"]])
}

trigger_PII_06 if {
    has_any([["passport_number"]])
}

trigger_PII_07 if {
    has_any([["driving_licence_number"]])
}

trigger_PII_08 if {
    has_any([["bank_account", "sort_code"], ["credit_card_number"]])
}

trigger_PII_09 if {
    has_any([["IP address", "device ID"], ["cookie ID", "user ID where linkable to a person"]])
}

trigger_SPII_01 if {
    has_any([["medical_condition", "diagnosis"], ["treatment", "disability information"]])
}

trigger_SPII_02 if {
    has_any([["ethnicity", "race"], ["racial_origin"]])
}

trigger_SPII_03 if {
    has_any([["religion", "belief"]])
}

trigger_SPII_04 if {
    has_any([["political_view", "party_preference"]])
}

trigger_SPII_05 if {
    has_any([["union_member", "trade_union"]])
}

trigger_SPII_06 if {
    has_any([["faceprint", "fingerprint"], ["iris_scan", "DNA profile"]])
}

trigger_CPII_01 if {
    all_groups_present([["full name", "date of birth"]])
}

trigger_CPII_02 if {
    all_groups_present([["full name", "postal address"], ["full name", "postcode"]])
}

trigger_CPII_03 if {
    all_groups_present([["full name", "phone number"]])
}

trigger_CPII_04 if {
    all_groups_present([["full name", "personal email address"]])
}

trigger_CPII_05 if {
    all_groups_present([["date of birth", "postcode", "gender"]])
}

trigger_CPII_06 if {
    all_groups_present([["Employee ID", "department"], ["role where linkable to a person"]])
}

trigger_CPII_07 if {
    all_groups_present([["Customer ID", "account event details"]])
}

trigger_CPII_08 if {
    text_matches(["free-text comments"], ["personal identifiers"])
}

# Triggered rules

triggered_rules contains "PII-01" if {
    trigger_PII_01
}

triggered_rules contains "PII-02" if {
    trigger_PII_02
}

triggered_rules contains "PII-03" if {
    trigger_PII_03
}

triggered_rules contains "PII-04" if {
    trigger_PII_04
}

triggered_rules contains "PII-05" if {
    trigger_PII_05
}

triggered_rules contains "PII-06" if {
    trigger_PII_06
}

triggered_rules contains "PII-07" if {
    trigger_PII_07
}

triggered_rules contains "PII-08" if {
    trigger_PII_08
}

triggered_rules contains "PII-09" if {
    trigger_PII_09
}

triggered_rules contains "SPII-01" if {
    trigger_SPII_01
}

triggered_rules contains "SPII-02" if {
    trigger_SPII_02
}

triggered_rules contains "SPII-03" if {
    trigger_SPII_03
}

triggered_rules contains "SPII-04" if {
    trigger_SPII_04
}

triggered_rules contains "SPII-05" if {
    trigger_SPII_05
}

triggered_rules contains "SPII-06" if {
    trigger_SPII_06
}

triggered_rules contains "CPII-01" if {
    trigger_CPII_01
}

triggered_rules contains "CPII-02" if {
    trigger_CPII_02
}

triggered_rules contains "CPII-03" if {
    trigger_CPII_03
}

triggered_rules contains "CPII-04" if {
    trigger_CPII_04
}

triggered_rules contains "CPII-05" if {
    trigger_CPII_05
}

triggered_rules contains "CPII-06" if {
    trigger_CPII_06
}

triggered_rules contains "CPII-07" if {
    trigger_CPII_07
}

triggered_rules contains "CPII-08" if {
    trigger_CPII_08
}

# ================================================
# Outcome detection
# ================================================

default has_block := false
default has_flag := false
default has_exception := false

has_block if {
    trigger_PII_05
}

has_block if {
    trigger_PII_06
}

has_block if {
    trigger_PII_07
}

has_block if {
    trigger_PII_08
}

has_block if {
    trigger_SPII_01
}

has_block if {
    trigger_SPII_02
}

has_block if {
    trigger_SPII_03
}

has_block if {
    trigger_SPII_04
}

has_block if {
    trigger_SPII_05
}

has_block if {
    trigger_SPII_06
}

has_flag if {
    trigger_PII_01
}

has_flag if {
    trigger_PII_02
}

has_flag if {
    trigger_PII_03
}

has_flag if {
    trigger_PII_04
}

has_flag if {
    trigger_PII_09
}

has_flag if {
    trigger_CPII_01
}

has_flag if {
    trigger_CPII_02
}

has_flag if {
    trigger_CPII_03
}

has_flag if {
    trigger_CPII_04
}

has_flag if {
    trigger_CPII_05
}

has_flag if {
    trigger_CPII_06
}

has_flag if {
    trigger_CPII_07
}

has_flag if {
    trigger_CPII_08
}

# ================================================
# Final decision
# ================================================

decision := "BLOCK" if {
    has_block
}

decision := "FLAG" if {
    not has_block
    has_flag
}

decision := "EXCEPTION APPROVED" if {
    not has_block
    not has_flag
    has_exception
}

# ================================================
# Final result
# ================================================

result := {
    "decision": decision,
    "triggered_rules": [rule | triggered_rules[rule]]
}