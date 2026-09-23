import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Policy Evaluation", page_icon="🛡️", layout="wide")

FILE = Path(__file__).parent / "generated_data" / "policy_results.xlsx"
df = pd.read_excel(FILE)

total = len(df)
passed = (df.expected_outcome == "PASS").sum()
flagged = (df.expected_outcome == "FLAG").sum()
blocked = (df.expected_outcome == "BLOCK").sum()
rate = round(passed / total * 100, 1) if total else 0

RULES = {
    "PII-01":"Full name detected","PII-02":"Personal email detected",
    "PII-03":"Phone number detected","PII-04":"Personal address detected",
    "PII-05":"National Insurance number detected","PII-06":"Passport number detected",
    "PII-08":"Credit card number detected","PII-09":"IP address detected",
    "SPII-01":"Medical information detected","SPII-02":"Ethnicity detected",
    "SPII-03":"Religion detected","SPII-04":"Political opinion detected",
    "CPII-01":"Name + date of birth","CPII-02":"Name + address",
    "CPII-03":"Name + phone","CPII-04":"Name + email",
    "CPII-05":"Date of birth + gender","CPII-06":"Employee ID + department + role",
    "CPII-08":"PII detected in feedback"
}

st.markdown("""
<style>
html,body{margin:0!important;overflow:hidden!important}
.stApp{background:#fff;color:#172033}
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none}
.block-container{padding:10px 30px!important}
div[data-testid="stVerticalBlock"]{gap:.15rem}
h1,h2,h3,p,label{color:#172033!important}
[data-testid="stCaptionContainer"]{color:#687386!important}
[data-testid="stTextInput"] input{background:#fff!important;color:#172033!important}
div.stButton>button{background:#fff!important;color:#172033!important;border:1px solid #dfe3e8!important;border-radius:6px!important;padding:5px!important;font-size:12px!important}
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff!important;border-color:#dfe3e8!important}
[data-testid="stAlert"]{border-radius:7px!important;padding:6px 9px!important}
[data-testid="stAlert"] p strong{font-size:32px!important;line-height:34px!important}
hr{margin:4px 0!important}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-thumb{background:#c8cdd5;border-radius:10px}
</style>
""", unsafe_allow_html=True)

st.caption("Evaluations / Run #1")
st.markdown("### Policy evaluation results")
st.caption(f"{total} records evaluated")

# Summary
a,b,c,d = st.columns(4)
a.success(f"✓ PASS\n\n**{passed}**\n\n{passed/total:.1%}" if total else "✓ PASS")
b.warning(f"⚠ FLAG\n\n**{flagged}**\n\n{flagged/total:.1%}" if total else "⚠ FLAG")
c.error(f"✕ BLOCK\n\n**{blocked}**\n\n{blocked/total:.1%}" if total else "✕ BLOCK")
d.info(f"◔ PASS RATE\n\n**{rate}%**\n\n{passed}/{total} passed")

left,right = st.columns([.9,1.3],gap="large")

with left:
    st.markdown(f"### Records ({total})")
    search = st.text_input("Search",placeholder="Search records...",label_visibility="collapsed")

    if "filter" not in st.session_state: st.session_state.filter="All"

    f1,f2,f3,f4 = st.columns(4)
    for col,name in zip((f1,f2,f3,f4),("All","PASS","FLAG","BLOCK")):
        if col.button(name if name=="All" else f"✓ {name}" if name=="PASS" else f"⚠ {name}" if name=="FLAG" else f"✕ {name}",use_container_width=True):
            st.session_state.filter=name

    data = df if st.session_state.filter=="All" else df[df.expected_outcome==st.session_state.filter]

    if search:
        q=search.lower()
        data=data[data.astype(str).apply(lambda x:x.str.lower().str.contains(q,regex=False).any(),axis=1)]

    st.caption(f"Showing {len(data)} records")

    if len(data):
        ids=data.record_id.tolist()
        if st.session_state.get("selected_record") not in ids:
            st.session_state.selected_record=ids[0]

    with st.container(height=425,border=True):
        for _,r in data.iterrows():
            icon={"PASS":"🟢","FLAG":"🟡","BLOCK":"🔴"}[r.expected_outcome]
            rules=str(r.expected_rule_triggers)
            if rules=="nan": rules="No violations"
            if st.button(f"{icon} REC-{int(r.record_id):04d}   {r.expected_outcome}   {rules}",key=f"r{r.record_id}",use_container_width=True):
                st.session_state.selected_record=r.record_id

with right:
    sid=st.session_state.get("selected_record")

    if sid is not None:
        r=df[df.record_id==sid].iloc[0]
        outcome=r.expected_outcome
        st.markdown(f"### REC-{int(sid):04d}")

        if outcome=="PASS": st.success("✓ PASS")
        elif outcome=="FLAG": st.warning("⚠ FLAG")
        else: st.error("✕ BLOCK")

        with st.container(height=425,border=True):
            st.markdown("**Policy rules**")
            rules=str(r.expected_rule_triggers)

            if rules=="nan" or not rules.strip():
                st.success("No policy violations detected.")
            else:
                for rule in [x.strip() for x in rules.split(";") if x.strip()]:
                    with st.container(border=True):
                        st.markdown(f"**{rule}**")
                        st.caption(RULES.get(rule,"Policy condition detected"))

            st.divider()
            st.markdown("**Explanation**")
            if outcome=="PASS": st.success(r.expected_reason)
            elif outcome=="FLAG": st.warning(r.expected_reason)
            else: st.error(r.expected_reason)

            st.divider()
            st.markdown("**Input data**")

            cols=["customer_name","email","phone","address","dob","gender","passport_number",
                  "ni_number","credit_card_number","bank_account","medical_condition",
                  "ethnicity","religion","political_view","employee_id","department",
                  "job_role","ip_address","feedback"]

            x,y=st.columns(2)
            fields=[(c,r[c]) for c in cols if c in r.index and pd.notna(r[c]) and str(r[c]).strip()]

            for i,(col,val) in enumerate(fields):
                with x if i%2==0 else y:
                    with st.container(border=True):
                        st.caption(col.replace("_"," ").title())
                        st.write(str(val))

            st.divider()
            st.markdown("**Suggested remediation**")
            st.info(r.suggested_remediation)