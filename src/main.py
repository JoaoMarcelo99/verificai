import asyncio
import logging
import os
import shutil
import sys
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from tenacity import retry, stop_after_attempt, wait_fixed

from src.core.models import ChatQuery, ChatResponse, SourceResponse
from src.services.llm_service import get_llm_service
from src.services.parser import ChunkProcessor, PDFProcessor
from src.services.vector_store import VectorStore

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s : %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
file_handler = logging.FileHandler("verificai_operation.log", encoding="utf-8")
file_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

logger = logging.getLogger("VerifiAI")
logger.info("Sistema VerificAI inicializado.")

app = FastAPI(
    title="VerificAI API",
    description="Backend para busca semântica e análise de PDFs",
    version="1.0.0",
)
vector_db = VectorStore(collection_name="meus_documentos")
llm_service = get_llm_service()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def safe_ask_llm(prompt: str):
    return llm_service.ask_llm(prompt=prompt)


@app.get("/")
def read_root():
    return {"status": "AnswerVault is running"}


@app.get("/test-process")
def test_process():
    try:
        sample_path = "/app/data/samples/documento_teste.pdf"

        if not os.path.exists(sample_path):
            raise HTTPException(status_code=404, detail="PDF not found")

        processor = PDFProcessor(sample_path)
        content = processor.extract_rawpages()

        chunk_processor = ChunkProcessor(chunk_size=500, overlap=50)
        chunks = chunk_processor.create_chunks(content, "documento_teste.pdf")
        vector_db.add_chunks(chunks)

        return {
            "status": "success",
            "message": f"{len(chunks)} chunks salvos no Qdrant!",
            "filename": "documento_teste.pdf",
            "chunk_count": len(chunks),
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar o PDF: {str(e)}"
        )


@app.post("/upload-pdfs")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    async def event_generator():
        total = len(files)
        all_chunks = []
        yield {
            "data": f"status:Iniciando processamento de {total} arquivos...|progress:5"
        }
        total_chunks = 0
        for i, file in enumerate(files):
            current_progress = 5 + int((i / total) * 85)
            yield {
                "data": f"status:Processando {file.filename}...|progress:{current_progress}"
            }

            content_bytes = await file.read()
            try:
                processor = PDFProcessor(
                    file_name=file.filename, file_content=content_bytes
                )
                raw_pages = processor.extract_rawpages()

                chunk_processor = ChunkProcessor(chunk_size=500, overlap=50)
                chunks = chunk_processor.create_chunks(raw_pages, file.filename)

                all_chunks.extend(chunks)
                total_chunks += len(chunks)

            except Exception as e:
                yield {
                    "data": f"status:Erro no arquivo {file.filename}: {str(e)}|progress:{current_progress}"
                }
                continue
            finally:
                await file.close()
        if all_chunks:
            yield {
                "data": f"status:Enviando {len(all_chunks)} trechos para o banco vetorial...|progress:80"
            }
            unique_chunks = vector_db.filter_chunks(all_chunks, file.filename)
            vector_db.add_chunks(unique_chunks)
        yield {
            "data": f"status:Concluído! {len(files)} arquivos e {total_chunks} trechos salvos.|progress:100"
        }
        return

    return EventSourceResponse(event_generator())


@app.post("/ask", response_model=ChatResponse)
def ask(payload: ChatQuery, top_k: int = 3):
    try:
        question = payload.question
        current_threshold = payload.threshold

        if not question.strip():
            raise HTTPException(
                status_code=400, detail="A pergunta não pode estar vazia."
            )

        query_vector = vector_db.model.encode(question).tolist()
        results = vector_db.search(query=query_vector, top_k=top_k)

        if not results:
            return {"query": question, "results": "Nenhum contexto encontrado."}

        relevant_results = [
            res for res in results if res.score and res.score >= current_threshold
        ]
        if not relevant_results:
            return {
                "query": payload.question,
                "answer": "Nenhum contexto relevante encontrado acima do limiar definido.",
                "sources": [],
                "estimated_cost": 0.0,
            }
        prompt = llm_service.prompt(question, relevant_results)
        tokens_input = llm_service.count_tokens(prompt)

        if tokens_input > 2000:
            raise HTTPException(
                status_code=400,
                detail=f"O prompt excede o limite de tokens. Tokens no prompt: {tokens_input}",
            )

        answer = llm_service.ask_llm(prompt)
        tokens_output = llm_service.count_tokens(answer)

        cost = (tokens_input + tokens_output) * 0.0000002

        sources = []
        for res in relevant_results:
            res_source = SourceResponse(
                file=res.payload["filename"],
                page=res.payload["page_numbers"][0]
                if isinstance(res.payload["page_numbers"], list)
                else res.payload["page_numbers"],
                content=res.payload.get("content", "Trecho indisponível"),
            )

            sources.append(res_source)

        return ChatResponse(answer=answer, sources=sources, estimated_cost=cost)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@app.get("/test-connection")
def test_connection():
    return {"message": "Conexão bem-sucedida!"}


@app.get("/documents")
async def list_documents():
    try:
        files = vector_db.list_documents()
        return {"documents": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear-database")
async def clear_database():
    try:
        vector_db.clear_database()
        return {"message": "Memória apagada com sucesso. O cérebro está vazio."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    try:
        vector_db.delete_file_points(filename)
        return {"message": f"Documento {filename} deletado com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
