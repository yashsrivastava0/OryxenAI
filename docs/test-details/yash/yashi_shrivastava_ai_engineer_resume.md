# YASHI SHRIVASTAVA
**Staff AI Systems Engineer & LLM Infrastructure Architect**

San Francisco, CA, USA | Open to Hybrid / Remote
yashi.shrivastava.ai@example.com | +1 (415) 555-0198
Portfolio: https://yashishrivastava.dev | GitHub: https://github.com/yashishrivastava | LinkedIn: https://linkedin.com/in/yashi-shrivastava

---

## PROFESSIONAL SUMMARY

Staff AI & Machine Learning Systems Engineer with 8+ years of experience designing, scaling, and deploying frontier generative AI, distributed LLM inference, autonomous agentic systems, and high-throughput ML infrastructure across top-tier Silicon Valley tech companies (Databricks, Scale AI, Uber AI Labs). Deep expertise in LLM fine-tuning (LoRA/QLoRA, DPO/RLHF), agentic orchestration frameworks, low-latency hybrid RAG pipelines, model quantization (AWQ/GPTQ), and speculative decoding on large GPU clusters. Proven track record of reducing p99 inference latency by 42%, scaling vector search across 50M+ embeddings, and orchestrating production multi-agent architectures serving tens of millions of daily queries.

## CORE TECHNICAL CAPABILITIES

- **GenAI & Agentic Architectures:** Agentic reasoning (ReAct, Plan-and-Solve, Multi-Agent Swarms), tool use & function calling, structured generation, self-correcting validation loops, prompt engineering & evals (LLM-as-a-judge, MT-Bench), guardrails & alignment (RLHF, DPO, constitutional AI).
- **LLM Systems & Inference Optimization:** vLLM, TensorRT-LLM, Triton Inference Server, speculative decoding, continuous batching, PagedAttention, KV-cache quantization (FP8, INT4, AWQ), model parallelism (Tensor/Pipeline/Expert Parallelism), Ray Serve.
- **Distributed Training & Fine-Tuning:** PyTorch, DeepSpeed (ZeRO 1/2/3), Megatron-LM, Hugging Face (Transformers, PEFT, TRL), Ray Train, LoRA/QLoRA, full parameter fine-tuning, SLURM, Kubernetes (KubeFlow, Volcano).
- **Information Retrieval & RAG:** Hybrid dense/sparse retrieval (BM25 + SPLADE + dense embeddings), ColBERT token-level re-ranking, vector databases (Qdrant, Pinecone, Milvus, pgvector), chunking strategies, semantic routing, context compression.
- **Platforms & Languages:** Python, C++, Rust, SQL, TypeScript/Node.js, CUDA, Linux, FastAPI, Docker, Kubernetes, AWS (SageMaker, EKS, EC2 P4d/P5), GCP (Vertex AI, Cloud TPU/GPU), Azure AI, Prometheus, Grafana, MLflow, Weights & Biases.

## PROFESSIONAL EXPERIENCE

### Databricks - Staff AI Engineer - Generative AI & Foundation Models Platform
**San Francisco, CA | Apr 2023 - Present**

- Architected the core runtime for the enterprise LLM serving platform powering managed model endpoints for 1,200+ enterprise customers, achieving a 42% p99 latency reduction and $3.2M annual GPU cost savings.
- Designed and implemented an autonomous multi-agent tool execution engine with dynamic backtracking, sandboxed Python code execution, and deterministic validation schema enforcement.
- Built distributed speculative decoding pipelines pairing compact draft models with 70B+ parameter foundation models, boosting token generation throughput by 2.4x.
- Led the end-to-end evaluation harness and safety guardrail infrastructure, automating red-teaming, jailbreak detection, and hallucination scoring across customer-facing agent deployments.
- Mentored 9 machine learning engineers and served on the AI Architecture Review Board, establishing best practices for model quantization, inference caching, and latency budgets.

### Scale AI - Senior AI Systems Engineer - Enterprise GenAI & Frontier Alignment
**San Francisco, CA | Aug 2021 - Mar 2023**

- Built scalable alignment pipelines for frontier LLMs, implementing RLHF and Direct Preference Optimization (DPO) pipelines handling over 5M pairwise reward ratings.
- Architected production enterprise RAG systems across Fortune 500 financial and legal datasets, combining Qdrant vector indexing, BM25 keyword matching, and cross-encoder re-ranking to achieve 89.4% answer precision.
- Engineered continuous model quantization pipelines (AWQ, GPTQ, INT8 weight-only) to compress 13B and 70B parameter models onto single-GPU edge and server instances without perceptual degradation.
- Developed real-time telemetry and streaming evaluation pipelines detecting prompt injection, data leakage, and drift across live client inference sessions.
- Collaborated closely with research teams to translate cutting-edge retrieval and reasoning papers into production-ready libraries and microservices.

### Uber AI Labs / Michelangelo Platform - Machine Learning Engineer -> Senior ML Engineer
**San Francisco, CA / Seattle, WA | Jun 2018 - Jul 2021**

- Engineered high-throughput, low-latency deep learning inference pipelines on the Michelangelo ML platform, supporting 500k+ real-time QPS for dynamic dispatch and ETA prediction.
- Migrated legacy deep learning training workflows to distributed PyTorch on Kubernetes with Horovod and DeepSpeed, cutting multi-GPU training time from 72 hours to 18 hours.
- Built an automated model monitoring and feature drift detection service tracking 200+ production models, slashing silent performance degradation incidents by 65%.
- Co-developed a unified feature store caching real-time geospatial and user features with sub-5ms read latency.

## SELECTED PROJECTS

### AegisAgent - Distributed Agentic Orchestration & Tool-Execution Engine
**Lead Architect & Core Maintainer**
**Technologies:** Python, FastAPI, Ray, LangGraph, vLLM, Redis, Docker, OpenTelemetry

An asynchronous, high-resilience agent runtime supporting DAG-based multi-step tool execution, state checkpointing, and dynamic backtracking. Features human-in-the-loop verification, isolated code execution sandboxes, and parallel tool calling with latency-optimized streaming responses.

**Impact:** Deployed across internal enterprise suites, handling 15M+ monthly tool executions with a 99.96% execution reliability rate and 35% reduced task completion time.

### OmniRAG - Low-Latency Enterprise Hybrid Retrieval Engine
**System Architect**
**Technologies:** PyTorch, Qdrant, FAISS, pgvector, Hugging Face Transformers, Ray Serve, FastAPI

A modular retrieval-augmented generation engine combining dense-sparse vector indexing (SPLADE + BGE-large), ColBERT token-level re-ranking, and dynamic context compression. Integrated semantic caching to bypass LLM generation for repeated queries.

**Impact:** Achieved sub-45ms p95 retrieval latency across 50M+ documents with an 89.4% factual accuracy score on domain benchmarks and a 52% reduction in repetitive model inference costs.

### SpecInfer-Dist - High-Throughput Distributed Speculative Decoding System
**Core Developer**
**Technologies:** CUDA, C++, PyTorch, TensorRT-LLM, vLLM, Triton Inference Server

An open-source distributed inference framework pairing small draft models with 70B+ parameter target LLMs across multi-node clusters. Implemented tree-based token verification and dynamic draft length adaptation based on acceptance rate telemetry.

**Impact:** Yielded a 2.4x wall-clock speedup for code generation and structured JSON extraction workloads without any loss of generation quality.

## EDUCATION

### Carnegie Mellon University (CMU), Pittsburgh, PA
**Master of Science (M.S.) in Computer Science - Artificial Intelligence & Machine Learning | 2016 - 2018**
- GPA: 3.92 / 4.0
- Coursework: Distributed Systems, Deep Learning, Statistical Machine Learning, Natural Language Processing, Convex Optimization.
- Research Assistant in Language Technologies Institute (LTI); focused on efficient neural sequence models.

### Indian Institute of Technology (IIT), Delhi
**Bachelor of Technology (B.Tech) in Computer Science & Engineering | 2012 - 2016**
- GPA: 9.4 / 10.0 | High Distinction / Department Merit Scholar
- Coursework: Data Structures & Algorithms, Operating Systems, Computer Architecture, Database Systems, Linear Algebra.

## PUBLICATIONS & SPEAKING

- "Speculative Decoding for Structured JSON Generation at Scale" - Workshop on Efficient Systems for Foundation Models (ICML 2024).
- "Autonomous Agentic Tool-Use: Failure Modes, Recovery Strategies, and Enterprise Sandboxing" - Keynote Speaker, AI Engineer World's Fair, San Francisco (2024).
- "Low-Latency Hybrid Retrieval Strategies for Enterprise RAG" - Co-author, Conference on Empirical Methods in Natural Language Processing (EMNLP 2023 Demo Track).

## CERTIFICATIONS & RECOGNITION

- AWS Certified Machine Learning - Specialty (MLS-C01)
- NVIDIA Certified Associate - Generative AI & LLMs
- Open Source Contributor: Active contributor to vLLM, LangGraph, and Hugging Face Transformers
- Winner, Databricks Global Hackathon (GenAI Track, 2023)

## LANGUAGES

- English - Full professional proficiency
- Hindi - Native proficiency
