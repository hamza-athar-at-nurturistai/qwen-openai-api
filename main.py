import logging
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatChoice,
    ChatMessage,
    StreamChoice,
    ModelListResponse,
    ModelInfo,
)
from qwen_client import qwen_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Qwen CLI OpenAI API",
    description="OpenAI-compatible API wrapper for Qwen CLI",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication dependency
async def verify_api_key(authorization: str = Header(None)):
    """Verify API key if configured."""
    if settings.API_KEY:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        # Extract Bearer token
        parts = authorization.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        if parts[1] != settings.API_KEY:
            raise HTTPException(status_code=403, detail="Invalid API key")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": settings.QWEN_MODEL,
        "timestamp": datetime.now().isoformat(),
    }


@app.get(f"{settings.API_BASE_PATH}/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """List available models (OpenAI-compatible)."""
    return ModelListResponse(
        data=[
            ModelInfo(id=settings.QWEN_MODEL),
            ModelInfo(id="qwen2.5-coder"),
        ]
    )


@app.post(
    f"{settings.API_BASE_PATH}/chat/completions",
    dependencies=[Depends(verify_api_key)]
)
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (OpenAI-compatible)."""
    try:
        if request.stream:
            return StreamingResponse(
                stream_chat_completion(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            return await generate_chat_completion(request)
    except RuntimeError as e:
        logger.error(f"Chat completion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def generate_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Generate a non-streaming chat completion."""
    response_text = await qwen_client.generate(
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage={
            "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(response_text.split()),
        }
    )


async def stream_chat_completion(request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Generate a streaming chat completion."""
    chunk_id = f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        async for token in qwen_client.generate_stream(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            chunk = ChatCompletionChunk(
                id=chunk_id,
                model=request.model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"role": "assistant", "content": token},
                        finish_reason=None,
                    )
                ]
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
        
        # Send final chunk with finish_reason
        final_chunk = ChatCompletionChunk(
            id=chunk_id,
            model=request.model,
            choices=[
                StreamChoice(
                    index=0,
                    delta={},
                    finish_reason="stop",
                )
            ]
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        error_chunk = {
            "error": {"message": str(e), "type": "server_error"}
        }
        yield f"data: {error_chunk}\n\n"
        yield "data: [DONE]\n\n"


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return {"error": {"message": "Endpoint not found", "type": "not_found"}}


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return {"error": {"message": "Internal server error", "type": "server_error"}}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
