"""
AI ko hum smart assistant samjhte hain, lekin woh kabhi:
- koi field bhool sakta hai,
- text ki jagah list bhej sakta hai,
- importance "five" likh sakta hai,
- ya incomplete JSON bhej sakta hai.
Isliye AI ka response directly app mein use nahi karte. Pehle ek “quality check gate” se pass karte hain.

"""


def normalize_content_parse_result(raw_result: dict) -> dict:

    # Agar result dictionary nahi hai, toh empty dictionary maan lo.
    if not isinstance(raw_result, dict):
        raw_result = {}

    return {
        "content_type": str(raw_result.get("content_type", "unknown")),
        "difficulty": str(raw_result.get("difficulty", "unknown")),
        "domain": str(raw_result.get("domain", "")),
        "overall_topic": str(raw_result.get("overall_topic", "")),
        "prerequisites": _safe_list(raw_result.get("prerequisites")),
        "key_entities": _safe_list(raw_result.get("key_entities", [])),
        "topics": _safe_list(raw_result.get("topics", [])),
        "learning_objectives": _safe_list(raw_result.get("learning_objectives")),
        "knowledge_graph_mermaid": str(raw_result.get("knowledge_graph_mermaid", "")),
    }


"""
_ Python ka convention hai. It means: “yeh internal helper hai; isko bahar ke code se directly call karne ki zaroorat nahi.”
"""


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value

    return []
