from pdf_reader import extract_text

text = extract_text("input/policy.pdf")

print("Extracted characters:", len(text))
print()
print(text[:3000])