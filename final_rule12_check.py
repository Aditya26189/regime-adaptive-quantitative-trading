# final_rule12_check.py
import glob
import os

print("="*70)
print("RULE 12 FINAL CHECK - No High/Low/Open Prices")
print("="*70)

violations = []
for file in glob.glob("src/**/*.py", recursive=True):
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            # Check for high/low/open column access
            if (("df['high']" in line or 'df["high"]' in line or
                "df['low']" in line or 'df["low"]' in line or
                "df['open']" in line or 'df["open"]' in line) and
                not line.strip().startswith('#')):  # Ignore comments
                violations.append(f"{file}:{i+1} - {line.strip()}")

if violations:
    print("❌ VIOLATIONS FOUND:")
    for v in violations:
        print(f"  {v}")
    print("\n⚠️  CRITICAL: Fix before submission!")
else:
    print("✅ PASS: No high/low/open column access found")
    print("✅ All strategies use ONLY close prices")
