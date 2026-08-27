def normalize_knowledge_graph_result(result: dict) -> dict:

    if not isinstance(result, dict):
        return empty_knowledge_graph()

    result.setdefault("nodes", [])
    result.setdefault("edges", [])
    result.setdefault("concept_tree", {})
    result.setdefault("dependency_order", [])

    valid_node_ids = {node.get("id") for node in result["nodes"] if node.get("id")}

    result["dependency_order"] = [
        node_id for node_id in result["dependency_order"] if node_id in valid_node_ids
    ]

    return result
