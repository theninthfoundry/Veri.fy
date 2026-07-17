import sys
import json
import argparse
from typing import Dict, Any, List

# pyrefly: ignore [missing-import]
from veri.assertions import detect_polarity

def compare_graphs(local_nodes: List[Dict[str, Any]], golden_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    local_map = {n.get("label", n.get("id")): n for n in local_nodes}
    golden_map = {n.get("label", n.get("id")): n for n in golden_nodes}

    added = []
    removed = []
    regressions = []

    for label, n_gold in golden_map.items():
        if label not in local_map:
            removed.append(label)
        else:
            n_local = local_map[label]
            # Compare output content
            gold_val = n_gold.get("content", {}).get("output", "")
            local_val = n_local.get("content", {}).get("output", "")
            if gold_val != local_val:
                # Check for polarity flips (e.g. negation checks)
                gold_pol = detect_polarity(str(gold_val))
                local_pol = detect_polarity(str(local_val))
                if gold_pol != local_pol:
                    regressions.append({
                        "node": label,
                        "type": "polarity_flip",
                        "message": f"Critical Polarity Flip! Golden output had polarity {gold_pol}, but local output has polarity {local_pol}.",
                        "golden": gold_val,
                        "local": local_val
                    })
                else:
                    regressions.append({
                        "node": label,
                        "type": "value_mismatch",
                        "message": "Output value mismatch from golden trace.",
                        "golden": gold_val,
                        "local": local_val
                    })

    for label in local_map:
        if label not in golden_map:
            added.append(label)

    return {
        "added": added,
        "removed": removed,
        "regressions": regressions,
        "passed": len(regressions) == 0
    }

def main():
    parser = argparse.ArgumentParser(description="VERI CI/CD Quality & Regression Gate")
    parser.add_argument("--local-trace", required=True, help="Path to local run trace JSON")
    parser.add_argument("--golden-trace", required=True, help="Path to golden record trace JSON")
    args = parser.parse_args()

    try:
        with open(args.local_trace, "r") as f:
            local_data = json.load(f)
        with open(args.golden_trace, "r") as f:
            golden_data = json.load(f)
    except Exception as e:
        print(f"Error loading trace files: {e}")
        sys.exit(1)

    local_nodes = local_data if isinstance(local_data, list) else local_data.get("nodes", [])
    golden_nodes = golden_data if isinstance(golden_data, list) else golden_data.get("nodes", [])

    print("=" * 60)
    print("VERI CI/CD Regression Gate: Evaluating PR Branch Quality...")
    print("=" * 60)

    result = compare_graphs(local_nodes, golden_nodes)

    print(f"  • Added Nodes: {len(result['added'])} ({', '.join(result['added']) if result['added'] else 'None'})")
    print(f"  • Removed Nodes: {len(result['removed'])} ({', '.join(result['removed']) if result['removed'] else 'None'})")

    if not result["passed"]:
        print("\n❌ CI/CD Gating Failed! Regressions detected:")
        for r in result["regressions"]:
            print(f"\n  [{r['node']}] {r['message']}")
            print(f"    - Golden: {r['golden']}")
            print(f"    - Local:  {r['local']}")
        print("\n" + "=" * 60)
        sys.exit(1)
    else:
        print("\n✅ Verification Passed! No behavioral regressions or polarity flips detected.")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()
