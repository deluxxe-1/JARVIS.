#!/bin/bash
echo "=== Pulling ARIA AI models ==="
echo "Pulling Qwen3 8B (main LLM)..."
ollama pull qwen3:8b
echo "Pulling BGE-M3 (embeddings)..."
ollama pull bge-m3
echo "=== All models ready ==="
ollama list
