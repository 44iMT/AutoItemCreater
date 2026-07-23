"""
条码搜索工具：条码 → Qdrant payload 精确匹配 → 商品详情
"""
from qdrant_client.models import Filter, FieldCondition, MatchText
from config import qdrant_client, COLLECTION_NAME


def search_by_barcode(barcode: str) -> str:
    """
    用商品条码精确查找商品。

    参数:
        barcode: 商品条码，比如 '2009636699012'
    """
    print(f"[barcode] '{barcode}'")
    results, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="商品条码", match=MatchText(text=barcode))]
        ),
        limit=3,
        with_payload=True,
    )

    if not results:
        return f"条码 {barcode} 未找到"

    lines = []
    for i, hit in enumerate(results, 1):
        p = hit.payload
        fields = "\n".join(f"  {k}: {v}" for k, v in p.items())
        lines.append(f"[{i}]\n{fields}")

    print(f"[barcode] '{barcode}' → {len(lines)} 条")
    return "\n".join(lines)
