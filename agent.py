from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from config import DEEPSEEK_KEY, DEEPSEEK_BASE_URL
from tools import search_products, search_by_barcode, web_search, read_excel, create_excel, append_rows

# ═══════════════════════════════════════════════════
# LLM
# ═══════════════════════════════════════════════════
llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0,
)

# ═══════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════
checkpointer = MemorySaver()

agent = create_agent(
    llm,
    [search_products, search_by_barcode, web_search, read_excel, create_excel, append_rows],
    checkpointer=checkpointer,
    system_prompt="你是电商商品查询助手，按要求完成用户需要。",
)

# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "demo-1"}}
    content = """
    现在门店追加很多新品
    文件为"D:\PythonProject\AutoItemCreater\数据下载-商品档案_20260622142344.xls"
    
    因为这个门店没有加入系统，所以命名和信息很不规范
    你需要判断每个品是否是总部商品已经有的
    也可先搜一下 条码 在总部有没有， 如果有则可以直接认定是了
    如果没有的话 可以联网补充一下相关信息 然后和总部商品比对 
    可以参考价格 相关信息 进一步判断是不是一个品

    """
    result = agent.invoke(
        {"messages": [HumanMessage(content=content)]},
        config,
    )

    print(f"\n助手: {result['messages'][-1].content}\n".encode("gbk", errors="replace").decode("gbk"))

"""
现在门店追加很多新品
文件为"D:\PythonProject\AutoItemCreater\测试数据.xls"

帮我搜索商品 可以先搜索货号看看是不是已经有了，也可以网页搜索
并结合 总部商品 命名风格
生成返回 商品名称 售卖规格 基本单位 前台类目名称 商品重量 重量单位
检测 未生成的项目 可以再次搜索
商品条码无需改动，表里面有的内容也不用改
并将结果写入excel

"""