from typing import Dict, Any, List, Set, Tuple

class BehaviorBOM:
    """
    Computes and formats the Behavioral Bill of Materials (BOM) / Lineage
    for any target decision or output node in the execution graph.
    """
    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.nodes = {n.get("id"): n for n in nodes}
        
        # Build dependency adjacency list (target -> list of sources)
        self.dependencies: Dict[str, List[Tuple[str, str]]] = {}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            kind = edge.get("kind", edge.get("name", "depends_on"))
            if source and target:
                if target not in self.dependencies:
                    self.dependencies[target] = []
                self.dependencies[target].append((source, kind))

    def get_lineage(self, target_node_id: str) -> Dict[str, Any]:
        """
        Recursively extracts the behavioral provenance DAG for the target node.
        """
        visited: Set[str] = set()
        bom_nodes: List[Dict[str, Any]] = []
        bom_edges: List[Dict[str, Any]] = []

        def traverse(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if node:
                bom_nodes.append(node)

            parents = self.dependencies.get(node_id, [])
            for parent_id, kind in parents:
                bom_edges.append({
                    "source": parent_id,
                    "target": node_id,
                    "kind": kind
                })
                traverse(parent_id)

        traverse(target_node_id)

        # Categorize component references
        components = {
            "models": [],
            "prompts": [],
            "retrievals": [],
            "memories": [],
            "tools": []
        }

        for n in bom_nodes:
            category = n.get("category", n.get("kind", ""))
            name = n.get("name", n.get("label", ""))
            content = n.get("content", {})

            if category in ("llm_call", "llm"):
                components["models"].append({
                    "id": n.get("id"),
                    "model": n.get("metrics", {}).get("model", "unknown"),
                    "cost": n.get("metrics", {}).get("cost_usd", 0.0)
                })
                if "prompt" in content:
                    components["prompts"].append({
                        "id": n.get("id"),
                        "name": name,
                        "template_hash": content.get("prompt_hash", "unknown")
                    })
            elif category == "observation" or "retrieval" in name.lower():
                components["retrievals"].append({
                    "id": n.get("id"),
                    "source": name,
                    "output": content.get("output", "")
                })
            elif "memory" in name.lower() or category == "belief":
                components["memories"].append({
                    "id": n.get("id"),
                    "key": name,
                    "value": content.get("output", "")
                })
            elif category in ("tool_invocation", "tool", "action"):
                components["tools"].append({
                    "id": n.get("id"),
                    "name": name,
                    "args": content.get("input", {})
                })

        return {
            "target_node_id": target_node_id,
            "components": components,
            "sub_graph": {
                "nodes": bom_nodes,
                "edges": bom_edges
            }
        }
