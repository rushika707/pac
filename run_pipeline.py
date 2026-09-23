import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent


def run_step(name, command):
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=BASE,
        text=True
    )

    if result.returncode != 0:
        print()
        print(f"FAILED: {name}")
        sys.exit(result.returncode)


def main():

    # 1. Generate policy evaluation Excel
    run_step(
        "PYTHON POLICY ENGINE",
        [sys.executable, "policy_engine.py"]
    )

    # 2. Generate Rego from policy.json
    run_step(
        "REGO GENERATION",
        [sys.executable, "opa/rego_generator.py"]
    )

    # 3. Validate Rego syntax
    run_step(
        "OPA SYNTAX CHECK",
        ["opa-bin", "check", "opa/generated_policy.rego"]
    )

    # 4. Validate Python results against OPA
    run_step(
        "OPA VALIDATION",
        [sys.executable, "opa/opa_validator.py"]
    )

    print()
    print("=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()