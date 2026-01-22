import json
import re
from collections import Counter
import sys
import os

# Ensure we can import from the python directory
sys.path.append('/home/ubuntu/bd_business_dir/python')
from search_engine import normalize_text

def to_bengali_num(n):
    """Converts a number to Bengali numerals string."""
    digits = {'0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪', '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'}
    return "".join(digits.get(d, d) for d in str(n))

def analyze_word_frequency(json_path, output_md='/home/ubuntu/bd_business_dir/python/word_frequency.md'):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_words = []
    for entry in data:
        norm_entry = normalize_text(entry)
        words = re.split(r'[,\s;.\(\)\[\]]+', norm_entry)
        all_words.extend([w for w in words if w])

    counts = Counter(all_words)
    sorted_counts = counts.most_common()

    # Generate Markdown content
    lines = ["# Word Frequency Analysis\n", "```python", "DOMAIN_MAP = {"]
    
    current_line = "    "
    for i, (word, freq) in enumerate(sorted_counts):
        bn_freq = to_bengali_num(freq)
        entry = f"'{word}': '{bn_freq}', "
        current_line += entry
        
        # Every 3 items, start a new line
        if (i + 1) % 3 == 0:
            lines.append(current_line.rstrip())
            current_line = "    "
            
    # Add any remaining items
    if current_line.strip():
        lines.append(current_line.rstrip())
        
    lines.append("}")
    lines.append("```")

    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print(f"Analysis complete. Results saved to {output_md}")
    return counts

if __name__ == "__main__":
    analyze_word_frequency('/home/ubuntu/bd_business_dir/python/all_products.json')
