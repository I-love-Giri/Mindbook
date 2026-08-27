def build_mermaid(nodes: list, edges: list) -> str:
    """
    Build Mermaid graph from structured nodes and edges.

    The LLM is responsible for deciding the graph.
    Python is responsible for rendering it.
    """

    if not nodes:
        return ""

    lines = ["graph TD"]

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

    for node in nodes:
        node_id = node.get("id", "").strip()
        label = node.get("label", "").strip()

        if not node_id or not label:
            continue

        # Mermaid-safe label
        label = (
            label.replace('"', "")
            .replace("'", "")
            .replace(":", " -")
            .replace("|", " -")
            .replace("(", "")
            .replace(")", "")
            .replace("[", "")
            .replace("]", "")
        )

        lines.append(f"    {node_id}[{label}]")

    # ---------------------------------------------------------
    # Edges
    # ---------------------------------------------------------

    valid_ids = {node.get("id") for node in nodes if node.get("id")}

    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")

        if source not in valid_ids:
            continue

        if target not in valid_ids:
            continue

        lines.append(f"    {source} --> {target}")

    return "\n".join(lines)
