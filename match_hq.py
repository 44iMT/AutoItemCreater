import json5
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from config import DEEPSEEK_KEY, DEEPSEEK_BASE_URL
from tools import search_products, search_by_barcode, web_search

# ═══════════════════════════════════════════════════
# 文件路径 & 并发配置
# ═══════════════════════════════════════════════════
INPUT_FILE = r"C:\Users\Administrator\Desktop\测试数据.xls"
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\匹配结果.xlsx"
CONCURRENCY = 4      # 并发数
RETRY_TIMES = 3      # 重试次数

# ═══════════════════════════════════════════════════
# 字段映射
# ═══════════════════════════════════════════════════
COLUMNS_MAP = {
    "商品条码": "商品条码",
    "商品名称": "商品名称",
    "规格": "商品规格",
    "所属分类": "所属分类",
    "供应商": "供应商",
    "进货价": "进货价",
    "零售价": "零售价",
}
OUT_COLUMNS = {
    "总部商品编码": "总部系统中的商品编码，未找到则为空字符串",
    "总部商品名称": "总部系统中的商品名称，未找到则为空字符串",
    "置信度": "匹配置信度，用百分数表示，如 95%",
    "判定理由": "简要说明判断依据",
}

# ═══════════════════════════════════════════════════
# LLM & Agent
# ═══════════════════════════════════════════════════
llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0,
)

agent = create_agent(
    llm,
    [search_products, search_by_barcode, web_search],
    system_prompt=r"""
    你是电商商品查询助手,需要查询并判断门店商品是否是总部商品。
    门店没有加入总部系统，商品命名和信息很不规范（可能缩写、错别字、口语化）。

    ## 处理流程（每个品按以下步骤执行）
    1. 先用 search_by_barcode 搜条码，总部有则直接认定是同一商品。
    2. 条码没命中时，用 search_products 搜品名/货号，看总部是否有相似商品。
    3. 还没找到就 web_search 联网搜该商品信息，再和总部商品比对。
    4. 参考价格、规格等信息综合判断。

    ## 输出要求
    只输出 JSON，不要 markdown 包裹，不要任何解释文字。
    """,
)

# ═══════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    import time, pandas as pd
    from concurrent.futures import ThreadPoolExecutor, as_completed

    rows = pd.read_excel(INPUT_FILE, dtype=str).to_dict("records")
    print(f"[agent] 读取 '{INPUT_FILE}'，{len(rows)} 行，并发={CONCURRENCY}")

    out_keys = list(OUT_COLUMNS.keys())
    json_template = "{\n" + "\n".join(f'  "{k}": "{v}"' for k, v in OUT_COLUMNS.items()) + "\n}"

    def process_one(i, row):
        fields = {COLUMNS_MAP[k]: row[k] for k in COLUMNS_MAP if k in row and row[k] not in ("nan", "None", "")}
        lines = "\n".join(f"- {label}: {value}" for label, value in fields.items())
        prompt = f"""判断这个门店商品是否在总部存在：
        
        {lines}
        
        只输出JSON，不要markdown包裹：
        {json_template}
        """
        last_err = None
        for attempt in range(RETRY_TIMES):
            try:
                result = agent.invoke(
                    {"messages": [HumanMessage(content=prompt)]},
                    {"configurable": {"thread_id": f"item-{i+1}"}},
                )
                text = result["messages"][-1].content
                s = text.find("{")
                if s >= 0:
                    d, e = 1, s + 1
                    while d > 0 and e < len(text):
                        if text[e] == "{": d += 1
                        elif text[e] == "}": d -= 1
                        e += 1
                    text = text[s:e]
                out = json5.loads(text)
                merged = {**fields, **{k: out.get(k, "") for k in out_keys}, "_idx": i}
                print(f"[agent] [{i+1}/{len(rows)}] {fields.get('商品名称', '?')} → {out.get('判定理由', '?')}")
                return merged
            except Exception as e:
                last_err = e
                if attempt < RETRY_TIMES - 1:
                    time.sleep(2 ** attempt)
        print(f"[agent] [{i+1}/{len(rows)}] {fields.get('商品名称', '?')} 重试{RETRY_TIMES}次仍失败: {last_err}")
        return None

    # 并发执行
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(process_one, i, row): i for i, row in enumerate(rows)}
        for f in as_completed(futures):
            r = f.result()
            if r:
                results.append(r)

    # 按原始顺序排列
    results.sort(key=lambda r: r.pop("_idx"))
    print(f"[agent] 成功 {len(results)}/{len(rows)} 个品")

    # 保存
    input_headers = list(dict.fromkeys(v for k, v in COLUMNS_MAP.items() if k in rows[0]))
    pd.DataFrame([[r.get(h, "") for h in input_headers + out_keys] for r in results],
                 columns=input_headers + out_keys).to_excel(OUTPUT_FILE, index=False)
    print(f"[agent] 完成 → '{OUTPUT_FILE}'")
