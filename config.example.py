"""
全局配置模板。复制为 config.py 并填入真实值。
config.py 已在 .gitignore 中，不会被提交。
"""
import os

from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient

# ---- API Keys ----
DEEPSEEK_KEY = "sk-your-deepseek-key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

GJ_KEY = "sk-your-siliconflow-key"

# ---- 嵌入模型（SiliconFlow 托管 BGE）----
embed_model = OpenAIEmbedding(
    model_name="BAAI/bge-large-zh-v1.5",
    api_key=GJ_KEY,
    api_base="https://api.siliconflow.cn/v1",
)

# ---- 重排模型 ----
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_API_URL = "https://api.siliconflow.cn/v1/rerank"
RERANK_MAX_RETRIES = 3

# ---- 数据文件 ----
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORY_FILE = os.path.join(_BASE_DIR, "data", "通用类目.csv")

# ---- Qdrant 连接 ----
COLLECTION_NAME = "总部商品"
VECTOR_DIM = 1024  # bge-large-zh-v1.5 输出维度

qdrant_client = QdrantClient(url="http://localhost:6333")
