import sys
import json
import argparse
import os
from typing import Dict, Any, List, Optional

# pyrefly: ignore [missing-import]
from veri.assertions import detect_polarity
# pyrefly: ignore [missing-import]
from veri.contracts import BehaviorContract
# pyrefly: ignore [missing-import]
from veri.lineage import BehaviorBOM

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
                gold_pol = detect_polarity(str(gold_val))
                local_pol = detect_polarity(str(local_val))
                if gold_pol != local_pol:
                    regressions.append({
                        "node": label,
                        "node_id": n_local.get("id"),
                        "type": "polarity_flip",
                        "message": f"Critical Polarity Flip! Golden output had polarity {gold_pol}, but local output has polarity {local_pol}.",
                        "golden": gold_val,
                        "local": local_val
                    })
                else:
                    regressions.append({
                        "node": label,
                        "node_id": n_local.get("id"),
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

def compare_fingerprints(local_fp: Optional[Dict[str, Any]], golden_fp: Optional[Dict[str, Any]]) -> None:
    if not local_fp or not golden_fp:
        print("  ⚠️ Runtime Fingerprint comparison skipped: missing metadata.")
        return

    local_hash = local_fp.get("hash")
    golden_hash = golden_fp.get("hash")

    if local_hash == golden_hash:
        print("  ✅ Runtime Environment Fingerprint matches golden trace exactly.")
    else:
        print(f"  ⚠️ ALERT: Runtime Environment Drift Detected!")
        print(f"     - Golden Fingerprint: {golden_hash}")
        print(f"     - Local Fingerprint:  {local_hash}")
        
        # Diff snapshots
        gold_snap = golden_fp.get("snapshot", {})
        loc_snap = local_fp.get("snapshot", {})
        
        gold_model = gold_snap.get("model_parameters", {})
        loc_model = loc_snap.get("model_parameters", {})
        if gold_model != loc_model:
            print("     - Drift Source: Model configuration changed:")
            print(f"       • Golden: {gold_model}")
            print(f"       • Local:  {loc_model}")

        gold_prompts = gold_snap.get("prompt_templates", {})
        loc_prompts = loc_snap.get("prompt_templates", {})
        for name, template in gold_prompts.items():
            if name not in loc_prompts:
                print(f"       • Removed prompt template: {name}")
            elif template != loc_prompts[name]:
                print(f"       • Prompt template modified: {name}")

        gold_tools = gold_snap.get("tool_schemas", {})
        loc_tools = loc_snap.get("tool_schemas", {})
        for name, schema in gold_tools.items():
            if name not in loc_tools:
                print(f"       • Removed tool schema: {name}")
            elif schema != loc_tools[name]:
                print(f"       • Tool schema modified: {name}")

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
    local_edges = [] if isinstance(local_data, list) else local_data.get("edges", [])

    print("=" * 60)
    print("VERI CI/CD Regression Gate: Evaluating PR Branch Quality...")
    print("=" * 60)

    # 1. Compare Environment Fingerprints
    local_fp = None if isinstance(local_data, list) else local_data.get("fingerprint")
    golden_fp = None if isinstance(golden_data, list) else golden_data.get("fingerprint")
    compare_fingerprints(local_fp, golden_fp)
    print("-" * 60)

    # 2. Check Behavioral Contracts
    contracts = None
    contracts_path = "veri.yaml"
    if os.path.exists(contracts_path):
        try:
            import yaml
            with open(contracts_path, "r") as f:
                cfg = yaml.safe_load(f)
            guardrails = cfg.get("guardrails", {})
            contracts = BehaviorContract(
                max_cost=guardrails.get("cost_limit"),
                forbidden_tools=cfg.get("testing", {}).get("forbidden_tools", [])
            )
        except Exception:
            pass

    if contracts:
        violations = contracts.verify_trace(local_nodes)
        if violations:
            print("❌ Behavioral Contract Violations Detected:")
            for v in violations:
                print(f"  • [{v.node_name}] Rule '{v.rule}': {v.message}")
            print("-" * 60)
            sys.exit(1)
        else:
            print("  ✅ Behavioral Contracts satisfied.")
            print("-" * 60)

    # 3. Compare Graphs
    result = compare_graphs(local_nodes, golden_nodes)

    print(f"  • Added Nodes: {len(result['added'])} ({', '.join(result['added']) if result['added'] else 'None'})")
    print(f"  • Removed Nodes: {len(result['removed'])} ({', '.join(result['removed']) if result['removed'] else 'None'})")

    if not result["passed"]:
        print("\n❌ CI/CD Gating Failed! Regressions detected:")
        for r in result["regressions"]:
            print(f"\n  [{r['node']}] {r['message']}")
            print(f"    - Golden: {r['golden']}")
            print(f"    - Local:  {r['local']}")
            
            # Print lineage (Behavior BOM) for target node to assist debugging
            if r.get("node_id"):
                bom = BehaviorBOM(local_nodes, local_edges)
                lineage = bom.get_lineage(r["node_id"])
                comp = lineage.get("components", {})
                print(f"    - Behavioral Lineage / BOM:")
                if comp.get("prompts"):
                    print(f"      • Prompts: {[p['name'] for p in comp['prompts']]}")
                if comp.get("retrievals"):
                    print(f"      • Retrievals: {[rt['source'] for rt in comp['retrievals']]}")
                if comp.get("tools"):
                    print(f"      • Tools: {[t['name'] for t in comp['tools']]}")
        print("\n" + "=" * 60)
        sys.exit(1)
    else:
        print("\n✅ Verification Passed! No behavioral regressions or polarity flips detected.")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()
