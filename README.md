# Verificai 🛡️

**AI-driven fact verification and semantic search with RAG architecture.**

**Verificai** is a state-of-the-art Retrieval-Augmented Generation (RAG) solution designed to eliminate LLM hallucinations. By anchoring AI responses in a private, verifiable knowledge base, it ensures that every output is grounded in factual data.

---

## 🚀 Core Stack

Built with a decoupled, modern architecture for maximum scalability and performance:

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | TypeScript / Next.js | Reactive UI with strict type safety. |
| **Backend** | Python / FastAPI | High-performance API and AI orchestration. |
| **Vector DB** | Qdrant | Similarity search and high-speed embedding storage. |
| **LLM** | OpenAI / Anthropic | Advanced Natural Language Processing engine. |
| **Container** | Docker | Environment standardization and seamless deployment. |

---

## 🛠️ Architecture & Data Flow

Verificai follows a sophisticated pipeline to ensure data integrity:

1.  **Ingestion:** Documents are processed and transformed into high-dimensional vectors (embeddings).
2.  **Indexing:** Vectors are stored and indexed within **Qdrant**.
3.  **Retrieval:** Upon user query, the system performs a semantic search to find the most relevant context.
4.  **Augmentation:** The query is enriched with the retrieved context and sent to the LLM.
5.  **Generation:** The user receives a response strictly based on the provided data.

---

## 📦 Getting Started

### Prerequisites
* Docker & Docker Compose
* OpenAI API Key (or your preferred provider)

### Quick Setup (Docker)

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/verificai.git](https://github.com/your-username/verificai.git)
   cd verificai
   ```
2. **Configure Environment Variables: Create a .env file in the root directory:**
  ```bash
  OPENAI_API_KEY=your_key_here
  QDRANT_HOST=qdrant
  QDRANT_PORT=6333
  ```
3. **Spin up the environment:**
  ```bash
  docker-compose up--build
  ```
The API will be accessible at http://localhost:8000 and the Frontend at http://localhost:3000.

📈 Roadmap
[x] Phase 1: Core Foundation & Project Scaffolding

[x] Phase 2: Qdrant Integration & Vector Embedding Pipeline

[ ] Phase 3: Real-time Streaming UI & UX Refinement

[ ] Phase 4: Multi-format File Ingestion (PDF/Docx/Web)

---
📄 License
Distributed under the MIT License. See LICENSE for more information.

Developed by João Marcelo — Building Reliable AI for a Data-Driven World.
