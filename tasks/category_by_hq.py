import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json5
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from config import DEEPSEEK_KEY, DEEPSEEK_BASE_URL
from tools import search_products, search_by_barcode, get_categories

# ═══════════════════════════════════════════════════
# 文件路径 & 并发配置
# ═══════════════════════════════════════════════════
INPUT_FILE = r"C:\Users\Administrator\Desktop\怀特店.xlsx"
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\怀特店分类结果.xlsx"
CONCURRENCY = 4  # 并发数
RETRY_TIMES = 3  # 重试次数

# ═══════════════════════════════════════════════════
# 字段映射
# ═══════════════════════════════════════════════════
COLUMNS_MAP = {
    "商品条码": "商品条码",
    "商品名称": "商品名称",
}

OUT_COLUMNS = {
    "商品条码": "商品条码",
    "商品名称": "商品名称",
    "前台类目": "根据范本和搜索生成的前台类目",
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
    [search_products, search_by_barcode, get_categories],
    system_prompt=r"""
    你是商超商品标准化专家。门店商品前台类目缺失，请参考总部范本搜索进行标准化。
    
    总部商品范本的前台类目有的是时令类目，需要结合总部商品类目列表，要保证类目在里面
    
    若商品条码精确匹配总部商品，直接使用总部商品信息填充，但前台类目还是需要保证在类目列表里
    
    前台类目 只需要填充一个符合的即可，不要放多个
    
    返回的字段结果都采用字符串类型的
    
    只输出 JSON，不要 markdown 包裹。
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
                # 提取最外层 {}，防止前面有"好的"等废话
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
                print(f"[agent] [{i + 1}/{len(rows)}] {fields.get('商品名称', '?')} → {out.get('前台类目', '?')}")
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

    # 保存（只输出 OUT_COLUMNS 字段）
    pd.DataFrame([[r.get(k, "") for k in out_keys] for r in results],
                 columns=out_keys).to_excel(OUTPUT_FILE, index=False)
    print(f"[agent] 完成 → '{OUTPUT_FILE}'")
