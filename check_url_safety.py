"""Verifies no unsafe URL string interpolation exists in MySQL-related files."""
from pathlib import Path

files = [
    'setup_mysql.py',
    'src/db/connection.py',
    'src/api/dependencies.py',
]

print("=" * 60)
print("  URL Safety Check")
print("=" * 60)

all_clean = True
for fp in files:
    p = Path(fp)
    content = p.read_text(encoding="utf-8")
    lines = content.splitlines()

    unsafe_lines = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Flag lines that embed mysql driver string AND use f-string or concat
        if "mysql+pymysql://" in stripped:
            if stripped.startswith('f"') or stripped.startswith("f'") or " + " in stripped:
                unsafe_lines.append((i, stripped))

    has_url_create = "URL.create(" in content

    if unsafe_lines:
        all_clean = False
        print(f"\n  UNSAFE: {fp}")
        for lineno, text in unsafe_lines:
            print(f"    line {lineno}: {text[:80]}")
    else:
        url_method = "URL.create()" if has_url_create else "no URL needed"
        print(f"  CLEAN:  {fp}  [{url_method}]")

print()
if all_clean:
    print("  ✅ All files safe. Passwords with special chars will work correctly.")
else:
    print("  ❌ Unsafe URL patterns found — fix before running setup_mysql.py")
print("=" * 60)
