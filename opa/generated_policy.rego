package generated_policy

default decision := "PASS"

# ==================================================
# Generic helpers
# ==================================================

has_value(field) if {
    value := object.get(input.record, field, "")
    value != null
    value != ""
}

has_any(fields) if {
    some i
    field := fields[i]
    has_value(field)
}

all_groups_present(groups) if {
    every group in groups {
        some i
        field := group[i]
        has_value(field)
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

# ==================================================
# Rule triggers
# ==================================================

trigger_CID_01 if {
    has_any(["customer_name"])
}

trigger_CID_02 if {
    has_any(["email"])
}

trigger_CID_03 if {
    has_any(["phone"])
}

trigger_CID_04 if {
    has_any(["address"])
}

trigger_CID_05 if {
    false
}

trigger_CID_06 if {
    false
}

trigger_CID_07 if {
    has_any(["bank_account", "credit_card_number"])
}

trigger_CID_08 if {
    has_any(["ip_address"])
}

trigger_RC_01 if {
    false
}

trigger_RC_02 if {
    has_any(["medical_condition"])
}

trigger_RC_03 if {
    false
}

trigger_RC_04 if {
    false
}

trigger_RC_05 if {
    false
}

trigger_RC_06 if {
    false
}

trigger_CCID_01 if {
    all_groups_present([["customer_name"], ["dob"]])
}

trigger_CCID_02 if {
    all_groups_present([["customer_name"], ["address"]])
}

trigger_CCID_03 if {
    false
}

trigger_CCID_04 if {
    false
}

trigger_CCID_05 if {
    false
}

trigger_CCID_06 if {
    false
}

trigger_CCID_07 if {
    false
}

trigger_CCID_08 if {
    text_matches(["feedback"], ["(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", "(?i)\\b(?:\\+44|0)\\d{9,10}\\b", "\\b(?:\\d[ -]?){13,19}\\b", "\\b[A-Z]{2}\\d{6}[A-Z]?\\b"])
}

# ==================================================
# Triggered rules
# ==================================================

triggered_rules contains "CID-01" if {
    trigger_CID_01
}

triggered_rules contains "CID-02" if {
    trigger_CID_02
}

triggered_rules contains "CID-03" if {
    trigger_CID_03
}

triggered_rules contains "CID-04" if {
    trigger_CID_04
}

triggered_rules contains "CID-05" if {
    trigger_CID_05
}

triggered_rules contains "CID-06" if {
    trigger_CID_06
}

triggered_rules contains "CID-07" if {
    trigger_CID_07
}

triggered_rules contains "CID-08" if {
    trigger_CID_08
}

triggered_rules contains "RC-01" if {
    trigger_RC_01
}

triggered_rules contains "RC-02" if {
    trigger_RC_02
}

triggered_rules contains "RC-03" if {
    trigger_RC_03
}

triggered_rules contains "RC-04" if {
    trigger_RC_04
}

triggered_rules contains "RC-05" if {
    trigger_RC_05
}

triggered_rules contains "RC-06" if {
    trigger_RC_06
}

triggered_rules contains "CCID-01" if {
    trigger_CCID_01
}

triggered_rules contains "CCID-02" if {
    trigger_CCID_02
}

triggered_rules contains "CCID-03" if {
    trigger_CCID_03
}

triggered_rules contains "CCID-04" if {
    trigger_CCID_04
}

triggered_rules contains "CCID-05" if {
    trigger_CCID_05
}

triggered_rules contains "CCID-06" if {
    trigger_CCID_06
}

triggered_rules contains "CCID-07" if {
    trigger_CCID_07
}

triggered_rules contains "CCID-08" if {
    trigger_CCID_08
}

# ==================================================
# Outcome flags
# ==================================================

default has_block := false
default has_flag := false
default has_exception := false

has_flag if {
    trigger_CID_01
}

has_flag if {
    trigger_CID_02
}

has_flag if {
    trigger_CID_03
}

has_flag if {
    trigger_CID_04
}

has_block if {
    trigger_CID_05
}

has_block if {
    trigger_CID_06
}

has_block if {
    trigger_CID_07
}

has_flag if {
    trigger_CID_08
}

has_block if {
    trigger_RC_01
}

has_block if {
    trigger_RC_02
}

has_block if {
    trigger_RC_03
}

has_block if {
    trigger_RC_04
}

has_block if {
    trigger_RC_05
}

has_block if {
    trigger_RC_06
}

has_flag if {
    trigger_CCID_01
}

has_flag if {
    trigger_CCID_02
}

has_flag if {
    trigger_CCID_03
}

has_flag if {
    trigger_CCID_04
}

has_flag if {
    trigger_CCID_05
}

has_flag if {
    trigger_CCID_06
}

has_flag if {
    trigger_CCID_07
}

has_flag if {
    trigger_CCID_08
}

# ==================================================
# Final decision
# ==================================================

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

# ==================================================
# Final result
# ==================================================

result := {
    "decision": decision,
    "triggered_rules": [rule | triggered_rules[rule]]
}