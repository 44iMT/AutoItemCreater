"""
获取所有前台类目
"""
from config import CATEGORY_FILE


def get_categories() -> str:
    """返回所有前台类目列表，用于给门店商品分类时参考。"""
    import pandas as pd
    df = pd.read_csv(CATEGORY_FILE, dtype=str, header=0)
    categories = df.iloc[:, 0].dropna().tolist()
    # 过滤掉表头行（如果被当成数据的话）
    categories = [c for c in categories if c != "通用类目" and c.strip()]
    print(f"[category] 读取 {len(categories)} 个类目")
    return "\n".join(categories)
