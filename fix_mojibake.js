
const fs = require('fs');

const files = [
    'frontend/src/app/projects/[id]/page.tsx',
    'frontend/src/app/projects/[id]/project-details.css'
];

const replacements = {
    'Ã—': '×',
    'â³': '⏳',
    'âŒ': '❌',
    'â¬…ï¸': '⬅️',
    'âœï¸': '✍️',
    'âœ—': '✗',
    'âœ“': '✓',
    'âœ…': '✅',
    'âš ï¸': '⚠️',
    'âš¡': '⚡',
    'âž¡ï¸': '➡️',
    'â–¶ï¸': '▶️',
    'â—‹': '○',
    'â†': '←',
    'â†’': '→',
    'ðŸ›': '🐛',
    'ðŸ¤–': '🤖',
    'ðŸ§ª': '🧪',
    'ðŸš€': '🚀',
    'ðŸŽ¯': '🎯',
    'ðŸŽ‰': '🎉',
    'ðŸ‘¤': '👤',
    'ðŸ‘¥': '👥',
    'ðŸ’¡': '💡',
    'ðŸ’¼': '💼',
    'ðŸ“': '📝', // Short map, be careful. Maybe check longer ones first.
    'ðŸ“§': '📧',
    'ðŸ“Œ': '📌',
    'ðŸ“Š': '📊',
    'ðŸ“Ž': '📎',
    'ðŸ“ˆ': '📈',
    'ðŸ“‚': '📂',
    'ðŸ“„': '📄',
    'ðŸ“‹': '📋',
    'ðŸ”§': '🔧',
    'ðŸ”¨': '🔨',
    'ðŸ”—': '🔗',
    'ðŸ”’': '🔒',
    'ðŸ””': '🔔',
    'ðŸ”„': '🔄',
    // Remove BOM
    '\uFEFF': ''
};

// Sort keys by length descending to replace longest matches first
const sortedKeys = Object.keys(replacements).sort((a, b) => b.length - a.length);

files.forEach(filePath => {
    if (!fs.existsSync(filePath)) {
        console.log(`File not found: ${filePath}`);
        return;
    }

    let content = fs.readFileSync(filePath, 'utf8');
    let originalContent = content;

    sortedKeys.forEach(bad => {
        const good = replacements[bad];
        // Global replace
        while (content.includes(bad)) {
            content = content.replace(bad, good);
        }
    });

    if (content !== originalContent) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`Fixed mojibake in ${filePath}`);
    } else {
        console.log(`No changes needed for ${filePath}`);
    }
});
