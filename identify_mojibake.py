
import re
import os

files = [
    r'frontend/src/app/projects/[id]/page.tsx',
    r'frontend/src/app/projects/[id]/project-details.css'
]

unique_matches = set()

for file_path in files:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find sequences of 2 or more non-ascii characters, or specific known starters like ð, â
        # Mojibake often looks like sequences of unicode replacement chars or latin-1 chars
        # Pattern: anything not standard ascii printable
        # But we want to capture the full sequence e.g. ðŸ“‹
        
        # Regex for non-ascii sequences
        matches = re.findall(r'[^\x00-\x7F]+', content)
        for m in matches:
            unique_matches.add(m)

print("Found unique non-ascii sequences:")
for m in sorted(list(unique_matches)):
    print(f"'{m}'")
