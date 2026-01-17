
const fs = require('fs');
const path = require('path');

const files = [
    'frontend/src/app/projects/[id]/page.tsx',
    'frontend/src/app/projects/[id]/project-details.css'
];

const uniqueMatches = new Set();

files.forEach(filePath => {
    if (!fs.existsSync(filePath)) {
        console.log(`File not found: ${filePath}`);
        return;
    }

    const content = fs.readFileSync(filePath, 'utf8');
    // Regex for non-ascii sequences
    const regex = /[^\x00-\x7F]+/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
        uniqueMatches.add(match[0]);
    }
});

console.log("Found unique non-ascii sequences:");
const sorted = Array.from(uniqueMatches).sort();
sorted.forEach(m => {
    console.log(`'${m}'`);
});
