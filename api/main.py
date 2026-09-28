from pathlib import Path
import sqlite3
import json
import math

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from policy_engine import (
    evaluate_dataframe,
    save_evaluations_to_database,
)


BASE = Path(__file__).resolve().parent.parent

DB_PATH = BASE / "data" / "policy.db"
POLICY_FILE = BASE / "policy" / "policy.json"
DATASET_FILE = BASE / "generated_data" / "synthetic_data.xlsx"


app = FastAPI(title="Policy-as-Code API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_execution_id(conn):
    row = conn.execute(
        """
        SELECT id
        FROM executions
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    return row["id"] if row else None


@app.get("/")
def root():
    return {"message": "Policy-as-Code API running"}


# ---------------------------------------------------------
# DATASET INFO
# ---------------------------------------------------------

@app.get("/api/dataset/info")
def dataset_info():

    if not DATASET_FILE.exists():
        return {
            "error": "Dataset file not found"
        }

    df = pd.read_excel(DATASET_FILE)

    return {
        "file": DATASET_FILE.name,
        "total_records": len(df),
        "columns": list(df.columns),
    }


# ---------------------------------------------------------
# DATASET BATCH EVALUATION
# ---------------------------------------------------------

@app.post("/api/dataset/evaluate")
def evaluate_dataset(
    start_record: int,
    end_record: int
):

    if not DATASET_FILE.exists():
        return {
            "error": "Dataset file not found"
        }

    if start_record < 1:
        return {
            "error": "start_record must be >= 1"
        }

    if end_record < start_record:
        return {
            "error": "end_record must be >= start_record"
        }

    df = pd.read_excel(DATASET_FILE)

    total_records = len(df)

    if start_record > total_records:
        return {
            "error": f"start_record exceeds dataset size ({total_records})"
        }

    if end_record > total_records:
        return {
            "error": f"end_record exceeds dataset size ({total_records})"
        }

    # Convert 1-based record numbers to pandas positions
    start_index = start_record - 1
    end_index = end_record

    selected_df = df.iloc[start_index:end_index].copy()

    # Evaluate ONLY this batch
    result_df = evaluate_dataframe(selected_df)

    # Save ONLY this batch
    execution_id = save_evaluations_to_database(
        result_df,
        start_record=start_record,
        end_record=end_record,
    )

    batch_number = ((start_record - 1) // 1000) + 1

    return {
        "success": True,
        "execution_id": execution_id,
        "batch_number": batch_number,
        "start_record": start_record,
        "end_record": end_record,
        "records_evaluated": len(result_df),
        "total_records": total_records,
    }


# ---------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------

@app.get("/api/statistics")
def statistics(execution_id: int | None = None):

    conn = get_db()

    if execution_id is None:
        execution_id = get_latest_execution_id(conn)

    if execution_id is None:
        conn.close()

        return {
            "execution_id": None,
            "total": 0,
            "pass": 0,
            "flag": 0,
            "block": 0,
        }

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM evaluations
        WHERE execution_id = ?
        """,
        (execution_id,),
    ).fetchone()[0]

    pass_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM evaluations
        WHERE execution_id = ?
        AND decision = 'PASS'
        """,
        (execution_id,),
    ).fetchone()[0]

    flag_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM evaluations
        WHERE execution_id = ?
        AND decision = 'FLAG'
        """,
        (execution_id,),
    ).fetchone()[0]

    block_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM evaluations
        WHERE execution_id = ?
        AND decision = 'BLOCK'
        """,
        (execution_id,),
    ).fetchone()[0]

    conn.close()

    return {
        "execution_id": execution_id,
        "total": total,
        "pass": pass_count,
        "flag": flag_count,
        "block": block_count,
    }


# ---------------------------------------------------------
# EVALUATIONS
# ---------------------------------------------------------

@app.get("/api/evaluations")
def evaluations(execution_id: int | None = None):

    conn = get_db()

    if execution_id is None:
        execution_id = get_latest_execution_id(conn)

    if execution_id is None:
        conn.close()
        return []

    rows = conn.execute(
        """
        SELECT
            e.id,
            e.record_id,
            e.decision,
            e.reason,
            e.remediation,
            e.evaluated_at,
            e.execution_id,
            GROUP_CONCAT(
                tr.rule_id,
                '; '
            ) AS triggered_rules
        FROM evaluations e
        LEFT JOIN triggered_rules tr
            ON e.id = tr.evaluation_id
        WHERE e.execution_id = ?
        GROUP BY e.id
        ORDER BY e.id
        """,
        (execution_id,),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ---------------------------------------------------------
# SINGLE RECORD
# ---------------------------------------------------------

@app.get("/api/evaluations/{record_id}")
def evaluation(
    record_id: str,
    execution_id: int | None = None
):

    conn = get_db()

    if execution_id is None:
        execution_id = get_latest_execution_id(conn)

    if execution_id is None:
        conn.close()
        return {"error": "Record not found"}

    row = conn.execute(
        """
        SELECT
            e.id,
            e.record_id,
            e.decision,
            e.reason,
            e.remediation,
            e.input_data,
            e.evaluated_at,
            e.execution_id
        FROM evaluations e
        WHERE e.record_id = ?
        AND e.execution_id = ?
        ORDER BY e.id DESC
        LIMIT 1
        """,
        (record_id, execution_id),
    ).fetchone()

    if row is None:
        conn.close()
        return {"error": "Record not found"}

    result = dict(row)

    result["input_data"] = json.loads(
        result["input_data"] or "{}"
    )

    rules = conn.execute(
        """
        SELECT rule_id
        FROM triggered_rules
        WHERE evaluation_id = ?
        """,
        (result["id"],),
    ).fetchall()

    result["triggered_rules"] = [
        rule["rule_id"]
        for rule in rules
    ]

    conn.close()

    return result


# ---------------------------------------------------------
# POLICY RULES
# ---------------------------------------------------------

@app.get("/api/rules")
def rules():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            rule_id,
            description,
            outcome
        FROM policy_rules
        ORDER BY rule_id
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ---------------------------------------------------------
# EXECUTION HISTORY
# ---------------------------------------------------------

@app.get("/api/executions")
def executions():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            e.id,
            e.total_records,
            e.batch_size,
            e.total_batches,
            e.start_record,
            e.end_record,
            e.started_at,
            e.completed_at,

            (
                SELECT COUNT(*)
                FROM evaluations ev
                WHERE ev.execution_id = e.id
                AND ev.decision = 'PASS'
            ) AS pass_count,

            (
                SELECT COUNT(*)
                FROM evaluations ev
                WHERE ev.execution_id = e.id
                AND ev.decision = 'FLAG'
            ) AS flag_count,

            (
                SELECT COUNT(*)
                FROM evaluations ev
                WHERE ev.execution_id = e.id
                AND ev.decision = 'BLOCK'
            ) AS block_count

        FROM executions e
        ORDER BY e.id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ---------------------------------------------------------
# POLICY DEFINITIONS
# ---------------------------------------------------------

@app.get("/api/policy/definitions")
def policy_definitions():

    with open(
        POLICY_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        policy = json.load(f)

    policy_item = policy["policies"][0]

    return {
        "policy_metadata":
            policy_item.get(
                "policy_metadata",
                {}
            ),

        "classification_catalogue":
            policy_item.get(
                "classificationCatalogue",
                {}
            ),

        "requirements":
            policy_item.get(
                "mandatoryPolicyRequirements",
                []
            ),

        "decisions":
            policy_item.get(
                "datasetDecisionOutcomes",
                []
            ),

        "remediation":
            policy_item.get(
                "remediationRequirements",
                []
            ),

        "evidence":
            policy_item.get(
                "minimumEvidenceRequired",
                []
            ),
    }