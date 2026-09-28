import json
from pathlib import Path

from ingestion.pdf_reader import extract_text
from ingestion.policy_extractor import extract_policy


BASE = Path(__file__).resolve().parent
TEST_DIR = BASE / "input" / "test"
OUTPUT_DIR = BASE / "test_runs"


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    pdfs = sorted(TEST_DIR.glob("*.pdf"))

    print("=" * 70)
    print("BATCH POLICY EXTRACTION TEST")
    print("=" * 70)
    print(f"PDFs found: {len(pdfs)}")

    for i, pdf in enumerate(pdfs, 1):

        print()
        print("-" * 70)
        print(f"[{i}/{len(pdfs)}] {pdf.name}")
        print("-" * 70)

        run_dir = OUTPUT_DIR / pdf.stem
        run_dir.mkdir(parents=True, exist_ok=True)

        output_file = run_dir / "policy.json"

        try:
            print("Reading PDF...")
            text = extract_text(str(pdf))

            if not text.strip():
                raise ValueError("No text extracted.")

            print(f"Extracted: {len(text):,} characters")

            print("Sending to Qwen...")
            extract_policy(
                text,
                str(output_file)
            )

            # Validate generated JSON
            with open(output_file, encoding="utf-8") as f:
                policy = json.load(f)

            policies = policy.get("policies", [])

            rule_count = sum(
                len(p.get("rules", []))
                for p in policies
            )

            print(f"Rules extracted: {rule_count}")
            print(f"Output: {output_file}")
            print("STATUS: PASS")

        except Exception as e:
            print(f"STATUS: FAIL")
            print(f"ERROR: {e}")

    print()
    print("=" * 70)
    print("BATCH EXTRACTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
