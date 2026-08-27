def clean_mermaid(mermaid: str) -> str:

    if not mermaid:
        return ""

    cleaned = mermaid.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        """

        [1:] ka matlab:

        Index 1 se end tak.

        Toh first line:

        ```mermaid

        hat gayi.

        Ab:

        [
            "graph TD",
            "A --> B",
            "```"
        ]
                
        """
        lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
            """ 
            [:-1] ka matlab:

            Last item ko chhod kar baaki sab.
            
            """
        cleaned = "\n".join(lines).strip()

    return cleaned
