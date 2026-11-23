from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
OWN_URL = os.getenv('MCP_OWN_URL', 'http://127.0.0.1:8000/mcp')
COMMUNITY_URL = os.getenv('MCP_COMMUNITY_URL', 'https://mcp.exa.ai/mcp')
