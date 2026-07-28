import json5
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from config import DEEPSEEK_KEY, DEEPSEEK_BASE_URL
from tools import search_by_barcode

# ═══════════════════════════════════════════════════
# 文件路径 & 并发配置
# ═══════════════════════════════════════════════════
INPUT_FILE = r"C:\Users\Administrator\Desktop\南磨房.xlsx"
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\南磨房差异结果.xlsx"
CONCURRENCY = 4  # 并发数
RETRY_TIMES = 3  # 重试次数

# ═══════════════════════════════════════════════════
# 字段映射
# ═══════════════════════════════════════════════════
COLUMNS_MAP = {
    "商品条码": "商品条码",
    "商品名称": "商品名称",
    "售卖规格": "售卖规格",
}
OUT_COLUMNS = {
    "总部商品编码": "总部系统中的商品编码，未找到则为空字符串",
    "总部商品名称": "总部系统中的商品名称，未找到则为空字符串",
    "总部售卖规格": "总部系统中的售卖规格，未找到则为空字符串",
    "相似程度": "商品信息相似程度，百分数表示，完全一样为100%",
    "异常标记": "规格异常/无匹配/无",
    "判定理由": "简要说明判定理由",
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
    [search_by_barcode],
    system_prompt=r"""
    你是电商商品查询助手,需要匹配商品条码判断门店商品与总部商品的信息差异
    
    输入的商品条码有的是多个条码，用逗号隔开了，需要分开匹配
    
    根据商品名称、商品规格判断门店与总部商品信息是否一致
    
    主要问题在商品的售卖规格上，需要判断两个品商品规格是否一致
    比如商品名称
    门店： 娃哈哈 AD 钙 一瓶 
    总部： 娃哈哈 AD 钙 一排
    一排是四瓶，像这种需要标记出来
    
    如果只是量词不一样但是 物品数量，克重等核心规格一致就不用标记了
    
    商品规格有时可能过于笼统无法判断，比如刚刚的两个品，商品规格可能都为 1个/份，所以需要结合判断
    
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
        prompt = f"""

        {lines}

        只输出JSON，不要markdown包裹：
        {json_template}
        """
        last_err = None
        for attempt in range(RETRY_TIMES):
            try:
                result = agent.invoke(
                    {"messages": [HumanMessage(content=prompt)]},
                    {"configurable": {"thread_id": f"item-{i + 1}"}},
                )
                text = result["messages"][-1].content
                s = text.find("{")
                if s >= 0:
                    d, e = 1, s + 1
                    while d > 0 and e < len(text):
                        if text[e] == "{":
                            d += 1
                        elif text[e] == "}":
                            d -= 1
                        e += 1
                    text = text[s:e]
                out = json5.loads(text)
                merged = {**fields, **{k: out.get(k, "") for k in out_keys}, "_idx": i}
                print(f"[agent] [{i + 1}/{len(rows)}] {fields.get('商品名称', '?')} → {out.get('判定理由', '?')}")
                return merged
            except Exception as e:
                last_err = e
                if attempt < RETRY_TIMES - 1:
                    time.sleep(2 ** attempt)
        print(f"[agent] [{i + 1}/{len(rows)}] {fields.get('商品名称', '?')} 重试{RETRY_TIMES}次仍失败: {last_err}")
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
