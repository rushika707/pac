import { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import "./App.css";

ChartJS.register(ArcElement, Tooltip, Legend);

const RULES = {
  "PII-01": "Full name detected",
  "PII-02": "Personal email detected",
  "PII-03": "Phone number detected",
  "PII-04": "Personal address detected",
  "PII-05": "National Insurance number detected",
  "PII-06": "Passport number detected",
  "PII-08": "Credit card number detected",
  "PII-09": "IP address detected",
  "SPII-01": "Medical information detected",
  "SPII-02": "Ethnicity detected",
  "SPII-03": "Religion detected",
  "SPII-04": "Political opinion detected",
  "CPII-01": "Name + date of birth",
  "CPII-02": "Name + address",
  "CPII-03": "Name + phone",
  "CPII-04": "Name + email",
  "CPII-05": "Date of birth + gender",
  "CPII-06": "Employee ID + department + role",
  "CPII-08": "PII detected in feedback"
};

const EXPLANATIONS = {
  "PII-01": "A full name can directly identify an individual.",
  "PII-02": "An email address can identify or enable contact with an individual.",
  "PII-03": "A phone number can directly link data to an individual.",
  "PII-04": "A postal address can reveal an individual's location.",
  "PII-05": "A National Insurance number is a highly sensitive personal identifier.",
  "PII-06": "A passport number is a sensitive government-issued identifier.",
  "PII-08": "Credit card data exposes sensitive financial information.",
  "PII-09": "An IP address may be used to identify a user or device.",

  "SPII-01": "Medical information is sensitive personal data requiring strict protection.",
  "SPII-02": "Ethnicity is classified as sensitive personal information.",
  "SPII-03": "Religious beliefs are sensitive personal information.",
  "SPII-04": "Political opinions are sensitive personal information.",

  "CPII-01": "Name and date of birth together increase identification risk.",
  "CPII-02": "Name and address together can directly identify an individual.",
  "CPII-03": "Name and phone number enable identification and direct contact.",
  "CPII-04": "Name and email together strengthen individual identification.",
  "CPII-05": "Date of birth and gender together increase identification risk.",
  "CPII-06": "Employee details combined may reveal an individual's identity.",
  "CPII-08": "Unstructured feedback contains potentially identifiable information."
};

const REMEDIATIONS = {
  "PII-01": "Full Name: Redact or tokenise the customer's name.",
  "PII-02": "Email Address: Mask or replace the email with a token.",
  "PII-03": "Phone Number: Mask the phone number.",
  "PII-04": "Postal Address: Remove or generalise the address.",
  "PII-05": "National Insurance Number: Remove this sensitive identifier.",
  "PII-06": "Passport Number: Remove this sensitive identifier.",
  "PII-08": "Credit Card Number: Remove or mask financial data.",
  "PII-09": "IP Address: Anonymise the IP address.",

  "SPII-01": "Medical Information: Remove or restrict sensitive health data.",
  "SPII-02": "Ethnicity: Remove or restrict sensitive personal data.",
  "SPII-03": "Religion: Remove or restrict sensitive personal data.",
  "SPII-04": "Political Opinion: Remove or restrict sensitive personal data.",

  "CPII-01": "Name + DOB: Remove the name or generalise the date of birth.",
  "CPII-02": "Name + Address: Remove the name or generalise the address.",
  "CPII-03": "Name + Phone: Redact the name and mask the phone number.",
  "CPII-04": "Name + Email: Redact the name and mask the email.",
  "CPII-05": "DOB + Gender: Generalise the DOB or remove gender.",
  "CPII-06": "Employee Details: Tokenise the employee ID and generalise details.",
  "CPII-08": "Feedback PII: Redact identifiable information from feedback."
};
const FILE_PATH = "/policy_results.xlsx";

function App() {
  const [df, setDf] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const response = await fetch(FILE_PATH);

      if (!response.ok) {
        throw new Error("Could not load policy_results.xlsx");
      }

      const buffer = await response.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });

      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(sheet, { defval: "" });

      setDf(data);

      if (data.length > 0) {
        setSelectedId(data[0].record_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const total = df.length;

  const passed = useMemo(
    () => df.filter((r) => r.expected_outcome === "PASS").length,
    [df]
  );

  const flagged = useMemo(
    () => df.filter((r) => r.expected_outcome === "FLAG").length,
    [df]
  );

  const blocked = useMemo(
    () => df.filter((r) => r.expected_outcome === "BLOCK").length,
    [df]
  );

  const passRate = total
    ? ((passed / total) * 100).toFixed(1)
    : 0;

  const filteredData = useMemo(() => {
    let data = [...df];

    if (filter !== "All") {
      data = data.filter(
        (r) => r.expected_outcome === filter
      );
    }

    if (search.trim()) {
  const q = search.toLowerCase().trim();

  data = data.filter((row) =>
    String(row.record_id).includes(q) ||
    String(row.expected_outcome).toLowerCase().includes(q) ||
    String(row.expected_rule_triggers || "")
      .toLowerCase()
      .includes(q)
  );
}

    return data;
  }, [df, filter, search]);

  const selectedRecord = useMemo(
    () =>
      df.find(
        (record) => String(record.record_id) === String(selectedId)
      ),
    [df, selectedId]
  );

const pieData = {
  labels: ["PASS", "FLAG", "BLOCK"],
  datasets: [
    {
      data: [passed, flagged, blocked],
      backgroundColor: ["#22c55e", "#f97316", "#ef4444"],
      borderWidth: 0,
    },
  ],
};

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "bottom",
      labels: {
        padding: 20,
      },
    },
    tooltip: {
      callbacks: {
        label: function (context) {
          const total = context.dataset.data.reduce(
            (sum, value) => sum + value,
            0
          );

          const percentage = total
            ? ((context.raw / total) * 100).toFixed(1)
            : 0;

          return `${context.label}: ${percentage}%`;
        },
      },
    },
  },
};

  const getOutcomeClass = (outcome) => {
    if (outcome === "PASS") return "pass";
    if (outcome === "FLAG") return "flag";
    return "block";
  };

  const getIcon = (outcome) => {
    if (outcome === "PASS") return "✓";
    if (outcome === "FLAG") return "⚠";
    return "✕";
  };

  const formatLines = (text) => {
    if (!text) return [];

    return String(text)
      .split(";")
      .map((item) => item.trim())
      .filter(Boolean);
  };

  const inputFields = [
    "customer_name",
    "email",
    "phone",
    "address",
    "dob",
    "gender",
    "passport_number",
    "ni_number",
    "credit_card_number",
    "bank_account",
    "medical_condition",
    "ethnicity",
    "religion",
    "political_view",
    "employee_id",
    "department",
    "job_role",
    "ip_address"
  ];

  const now = new Date();

  if (error) {
    return (
      <div className="error-page">
        <h2>Unable to load dashboard</h2>
        <p>{error}</p>
        <p>
          Place <b>policy_results.xlsx</b> inside the
          <b> public </b> folder.
        </p>
      </div>
    );
  }

  return (
    <div className="app">

      <header className="header">
        <div>
          <div className="breadcrumb">
            Evaluations / Run #1
          </div>

          <h1>Policy Evaluation Results</h1>

          <p>{total} records evaluated</p>
        </div>

        <div className="run-info">
          <span>RUN DATE & TIME</span>
          <strong>
            {now.toLocaleDateString()}{" "}
            {now.toLocaleTimeString()}
          </strong>
        </div>
      </header>

      <section className="overview">

        <div className="summary-section">

          <div className="summary-grid">

            <div className="summary-card pass-card">
              <span className="card-label">✓ PASS</span>
              <strong>{passed}</strong>
              <small>
                {total
                  ? ((passed / total) * 100).toFixed(1)
                  : 0}
                %
              </small>
            </div>

            <div className="summary-card flag-card">
              <span className="card-label">⚠ FLAG</span>
              <strong>{flagged}</strong>
              <small>
                {total
                  ? ((flagged / total) * 100).toFixed(1)
                  : 0}
                %
              </small>
            </div>

            <div className="summary-card block-card">
              <span className="card-label">✕ BLOCK</span>
              <strong>{blocked}</strong>
              <small>
                {total
                  ? ((blocked / total) * 100).toFixed(1)
                  : 0}
                %
              </small>
            </div>

            <div className="summary-card rate-card">
              <span className="card-label">◔ PASS RATE</span>
              <strong>{passRate}%</strong>
              <small>
                {passed}/{total} passed
              </small>
            </div>

          </div>

        </div>

        <div className="chart-section">
          <h3>Outcome Distribution</h3>

          <div className="pie-container">
            <Pie
              data={pieData}
              options={pieOptions}
            />
          </div>
        </div>

      </section>

      <section className="main-content">

        <div className="records-panel">

          <div className="panel-header">
            <div>
              <h2>Records</h2>
              <span>{filteredData.length} records shown</span>
            </div>
          </div>

          <input
            className="search"
            placeholder="Search records..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="filters">

            {["All", "PASS", "FLAG", "BLOCK"].map((name) => (
              <button
                key={name}
                className={`filter-button ${
                  filter === name ? "active" : ""
                }`}
                onClick={() => setFilter(name)}
              >
                {name === "PASS" && "✓ "}
                {name === "FLAG" && "⚠ "}
                {name === "BLOCK" && "✕ "}
                {name}
              </button>
            ))}

          </div>

          <div className="record-list">

            {filteredData.map((record) => {
              const outcome = record.expected_outcome;
              const rules =
                record.expected_rule_triggers || "No violations";

              return (
                <button
                  key={record.record_id}
                  className={`record-item ${
                    String(selectedId) ===
                    String(record.record_id)
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedId(record.record_id)
                  }
                >

                  <span
                    className={`status-dot ${getOutcomeClass(
                      outcome
                    )}`}
                  >
                    {getIcon(outcome)}
                  </span>

                  <div className="record-info">
                    <strong>
                      REC-
                      {String(record.record_id).padStart(
                        4,
                        "0"
                      )}
                    </strong>

                    <span>{rules}</span>
                  </div>

                  <span
                    className={`outcome-text ${getOutcomeClass(
                      outcome
                    )}`}
                  >
                    {outcome}
                  </span>

                </button>
              );
            })}

          </div>

        </div>

        <div className="analysis-panel">

          {selectedRecord ? (
            <>
              <div className="analysis-header">

                <div>
                  <span className="analysis-label">
                    RECORD POLICY ANALYSIS
                  </span>

                  <h2>
                    REC-
                    {String(
                      selectedRecord.record_id
                    ).padStart(4, "0")}
                  </h2>
                </div>

                <span
                  className={`outcome-badge ${getOutcomeClass(
                    selectedRecord.expected_outcome
                  )}`}
                >
                  {getIcon(
                    selectedRecord.expected_outcome
                  )}{" "}
                  {selectedRecord.expected_outcome}
                </span>

              </div>

              <div className="analysis-content">

                <section className="analysis-section">
                  <h3>Policy Rules</h3>

                  {selectedRecord.expected_rule_triggers ? (
                    <div className="rule-list">

                      {formatLines(
                        selectedRecord.expected_rule_triggers
                      ).map((rule) => (
                        <div
                          className="rule-item"
                          key={rule}
                        >
                          <strong>{rule}</strong>
                          <span>
                            {RULES[rule] ||
                              "Policy condition detected"}
                          </span>
                        </div>
                      ))}

                    </div>
                  ) : (
                    <div className="no-violations">
                      ✓ No policy violations detected
                    </div>
                  )}

                </section>

<section className="analysis-section">
  <h3>Explanation</h3>

  <div className="line-list">

    {formatLines(
      selectedRecord.expected_rule_triggers
    ).length === 0 ? (

      <div className="line-item">
        <span>•</span>
        No PII or sensitive information detected.
      </div>

    ) : (

      formatLines(
        selectedRecord.expected_rule_triggers
      ).map((rule, index) => (

        <div
          className="line-item"
          key={index}
        >
          <span>•</span>
          {EXPLANATIONS[rule] || "Policy violation detected."}
        </div>

      ))

    )}

  </div>
</section>

                <section className="analysis-section">
                  <h3>Input Data</h3>

                  <div className="input-grid">

                    {inputFields.map((field) => {
                      const value = selectedRecord[field];

                      if (
                        value === undefined ||
                        value === null ||
                        String(value).trim() === ""
                      ) {
                        return null;
                      }

                      return (
                        <div
                          className="input-item"
                          key={field}
                        >
                          <span>
                            {field
                              .replaceAll("_", " ")
                              .replace(/\b\w/g, (l) =>
                                l.toUpperCase()
                              )}
                          </span>

                          <strong>{String(value)}</strong>
                        </div>
                      );
                    })}

                  </div>
                </section>
<section className="analysis-section">
  <h3>Suggested Remediation</h3>

  <div className="remediation-list">
    {formatLines(selectedRecord.expected_rule_triggers).length === 0 ? (
      <div className="remediation-item">
        <span>→</span>
        <span>No remediation required.</span>
      </div>
    ) : (
      formatLines(selectedRecord.expected_rule_triggers).map((rule, index) => (
        <div className="remediation-item" key={index}>
          <span>→</span>
          <span>
            <strong>{rule}:</strong> {REMEDIATIONS[rule]}
          </span>
        </div>
      ))
    )}
  </div>
</section>
              </div>
            </>
          ) : (
            <div className="empty-analysis">
              Select a record to view analysis
            </div>
          )}

        </div>

      </section>

    </div>
  );
}

export default App;