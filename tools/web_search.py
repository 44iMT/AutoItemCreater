"""
网页搜索工具：通过 DeepSeek 内置联网搜索获取信息
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import DEEPSEEK_KEY, DEEPSEEK_BASE_URL

_search_llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0,
    extra_body={"enable_search": True},
)


def web_search(query: str, max_results: int) -> str:
    """
    在互联网上搜索信息，返回最新网页内容。适用于查询商品信息、市场价格、资讯等。

    参数:
        query:       搜索关键词，越具体越好。
                     正确: '阿里山茉莉花爆珠 价格'、'乐芙娜 商品规格'
                     错误: '查一下这个是什么'
        max_results: 最多返回几条结果，推荐 3-5 条
    """
    print(f"[web_search] '{query}' max: {max_results}")
    messages = [
        SystemMessage(content=(
            f"你是网页搜索助手。请搜索并总结与查询相关的最新信息。"
            f"返回最多 {max_results} 条结果，每条包含标题和摘要。"
            f"用纯文本格式，不要用 markdown。"
        )),
        HumanMessage(content=query),
    ]
    response = _search_llm.invoke(messages)
    content = response.content
    print(f"[web_search] '{query}' → 完成")
    return content
