import os
import sys

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config
from semantic_search import SemanticSearch

print("====================================")
print("  REBUILDING SEARCH INDEX & MODEL  ")
print("====================================")

# 1. Clean up old artifacts
artifacts = [
    os.path.join(config.MODELS_DIR, 'tfidf_vectorizer.pkl'),
    os.path.join(config.MODELS_DIR, 'tfidf_matrix.pkl'),
    os.path.join(config.MODELS_DIR, 'shop_ids.pkl')
]

print("Scanning for old artifacts...")
for file_path in artifacts:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted old: {os.path.basename(file_path)}")
    else:
        print(f"Not found (clean): {os.path.basename(file_path)}")

print("\n------------------------------")
print("Retraining Model...")

# 2. Rebuild Index
try:
    ss = SemanticSearch()
    
    if not os.path.exists(config.DB_PATH):
        print(f"ERROR: Database not found at {config.DB_PATH}")
        exit(1)
        
    ss.build_index(config.DB_PATH)
    print("\nSUCCESS: Search Index Rebuilt Successfully!")
    print(f"Artifacts saved in: {config.MODELS_DIR}")
    
except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback
    traceback.print_exc()
