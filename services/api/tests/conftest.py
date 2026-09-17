"""Tests must never call real model providers: the developer's services/api/.env (NVIDIA key, Ollama) is
loaded by Settings, so pin the spatial chain to nothing before app.main is imported anywhere."""
import os

os.environ["SPATIAL_PROVIDERS"] = "none"
os.environ["NVIDIA_API_KEY"] = ""
os.environ["LOCAL_LLM_BASE_URL"] = ""
os.environ["BEDROCK_ENABLED"] = "0"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_learning_platform.db")
