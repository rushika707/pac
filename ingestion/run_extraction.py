from pathlib import Path

from pdf_reader import extract_text
from policy_extractor import extract_policy


BASE = Path(__file__).parent.parent

PDF_FILE = BASE / "input" / "policy.pdf"
OUTPUT_FILE = BASE / "policy" / "policy.json"


def main():

    print("=" * 60)
    print("POLICY PDF → JSON")
    print("=" * 60)

    print(f"\nPDF: {PDF_FILE}")

    # --------------------------------------------------------
    # 1. Extract PDF text
    # --------------------------------------------------------

    print("\n[1/2] Extracting PDF text...")

    text = extract_text(PDF_FILE)

    print(f"Extracted characters: {len(text)}")

    # --------------------------------------------------------
    # 2. Send text to Qwen/Ollama
    # --------------------------------------------------------

    print("\n[2/2] Sending policy to Ollama...")

    extract_policy(
        pdf_text=text,
        output_file=OUTPUT_FILE
    )

    print("\nPolicy JSON generated:")
    print(OUTPUT_FILE)

    print("\nDone.")


if __name__ == "__main__":
    main()