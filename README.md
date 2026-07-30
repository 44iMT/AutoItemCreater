# AutoItemCreator

门店新品 Excel → AI 搜索总部商品库 → 匹配/标准化 → 输出结果 Excel。

## 项目结构

```
config.example.py   配置模板（复制为 config.py 填入密钥）
config.py            实际配置（gitignore，不提交）
requirements.txt     Python 依赖
builder.py           总部商品入库：Excel → 向量嵌入 → Qdrant

tasks/
  match_hq.py        商品匹配：判断门店品是否在总部已存在
  rename_by_hq.py    商品标准化：参考总部范本重命名/补全字段
  diff_hq.py         差异比较：比对门店与总部商品规格差异
  category_by_hq.py  类目补全：为门店商品匹配前台类目

tools/
  search.py          向量语义搜索（BGE 嵌入 + 重排）
  barcode.py         条码精确匹配
  web_search.py      DeepSeek 联网搜索
  category.py        获取通用类目列表

data/
  通用类目.csv         前台类目数据
```

## 四个 Agent

### match_hq — 商品匹配

输入门店新品 Excel，逐行搜索总部库，判断每个品是否总部已有。

```
输入: 商品条码、商品名称、规格、售价...
输出: 总部商品编码、总部商品名称、置信度、判定理由
```

### rename_by_hq — 商品标准化

输入门店新品 Excel，先搜总部库找范本，再按总部风格标准化命名和补全规格、类目、重量等信息。

```
输入: 商品条码、商品名称、规格...
输出: 标准化商品名称、售卖规格、前台类目、商品重量、重量单位、基本单位、范本商品
```

### diff_hq — 差异比较

输入门店商品 Excel，条码匹配总部后对比商品名称和售卖规格差异，标记规格异常。

```
输入: 商品条码、商品名称、售卖规格...
输出: 总部商品编码、总部商品名称、总部售卖规格、相似程度、异常标记、判定理由
```

### category_by_hq — 类目补全

输入门店商品 Excel，搜索总部范本并结合类目列表为商品匹配前台类目。

```
输入: 商品条码、商品名称、规格...
输出: 商品条码、商品名称、前台类目、范本商品
```

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DeepSeek V4 Flash |
| Agent | LangGraph create_agent |
| 向量库 | Qdrant（本地 localhost:6333） |
| 嵌入 | BAAI/bge-large-zh-v1.5（SiliconFlow, 1024维） |
| 重排 | BAAI/bge-reranker-v2-m3（SiliconFlow） |
| 解析 | pandas + json5 |

## 快速开始

### 环境

```bash
pip install -r requirements.txt
```

Qdrant 本地运行在 `http://localhost:6333`。

### 1. 构建向量索引

把总部商品 Excel 导入 Qdrant，只跑一次：

```bash
python builder.py
```

### 2. 改配置

打开要跑的脚本，改顶部变量：

```python
INPUT_FILE  = r"门店新品.xlsx"    # 输入文件
OUTPUT_FILE = r"结果.xlsx"         # 输出文件
CONCURRENCY = 4                    # 并发数
RETRY_TIMES = 3                    # 重试次数

COLUMNS_MAP = {                    # 输入映射：Excel列名 → 提示词显示名
    "商品条码": "商品条码",
    "商品名称": "商品名称",
    # Excel 中没有的列自动跳过，不放进提示词
}
OUT_COLUMNS = {                    # 输出定义：字段名 → 描述
    "总部商品编码": "总部系统中的编码",
    ...
}
```

### 3. 运行

```bash
python tasks/match_hq.py        # 匹配
python tasks/rename_by_hq.py    # 标准化
python tasks/diff_hq.py         # 差异比较
python tasks/category_by_hq.py  # 类目补全
```

## 工具

| 工具 | 用途 |
|------|------|
| `search_by_barcode` | Qdrant payload 精确匹配条码 |
| `search_products` | 向量语义搜索 + BGE 重排 |
| `web_search` | DeepSeek 联网搜索 |
| `get_categories` | 返回全部可用前台类目 |

## 架构

每个商品独立 Agent 对话（独立 thread_id），多线程并发执行，上下文不膨胀。

```
pandas 读 Excel → 每行一个 Agent 调  → 收集结果 → pandas 写 Excel
                    ├ 条码搜索
                    ├ 向量搜索
                    ├ 联网搜索
                    └ 类目查询
```

## 架构决策

这个架构不是一步到位的，经历了 LLM+RAG → Agent → 上下文压缩 → 行间隔离 的完整演进。踩过的坑和收敛的经验记录在 [`经验总结-Agent批处理架构演进.md`](./经验总结-Agent批处理架构演进.md)。

## 相关文章

- [Agent 批处理中上下文压缩为何失败](https://blog.csdn.net/AELimit/article/details/163190245)
- [给 Agent 的工具加了默认参数，它反而更笨了](https://blog.csdn.net/AELimit/article/details/163190791)
- [从 LLM-only 到 Agent：一个商超项目的架构选型](https://blog.csdn.net/AELimit/article/details/163208331)
