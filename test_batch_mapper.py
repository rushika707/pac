import json
from pathlib import Path
import pandas as pd

from policy.policy_mapper import map_policy


BASE = Path(__file__).resolve().parent
TEST_DIR = BASE / "test_runs"
DATASET = BASE / "generated_data" / "synthetic_data.xlsx"


def main():
    df = pd.read_excel(DATASET)
    columns = list(df.columns)

    print("=" * 70)
    print("BATCH POLICY MAPPING TEST")
    print("=" * 70)

    for run_dir in sorted(TEST_DIR.iterdir()):
        policy_file = run_dir / "policy.json"

        if not policy_file.exists():
            continue

        print()
        print("-" * 70)
        print(run_dir.name)
        print("-" * 70)

        try:
            with open(policy_file, encoding="utf-8") as f:
                policy = json.load(f)

            mapped = map_policy(policy, columns)

            output = run_dir / "mapped_policy.json"

            with open(output, "w", encoding="utf-8") as f:
                json.dump(mapped, f, indent=2)

            rules = []

            def walk(x):
                if isinstance(x, dict):
                    if "rule_id" in x and "_mapping" in x:
                        rules.append(x)
                    for v in x.values():
                        walk(v)
                elif isinstance(x, list):
                    for v in x:
                        walk(v)

            walk(mapped)

            print(f"Rules mapped: {len(rules)}")
            print(f"Output: {output}")
            print("STATUS: PASS")

        except Exception as e:
            print("STATUS: FAIL")
            print("ERROR:", e)

    print()
    print("=" * 70)
    print("BATCH MAPPING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
