import logging
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
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
    """Health check endpoint (used by Docker HEALTHCHECK)."""
    return {"status": "healthy", "model": settings.QWEN_MODEL}


@app.get(f"{settings.API_BASE_PATH}/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """List available models (OpenAI-compatible)."""
    return ModelListResponse(
        data=[
            ModelInfo(id=settings.QWEN_MODEL),
        ]
    )


@app.post(
    f"{settings.API_BASE_PATH}/chat/completions",
    dependencies=[Depends(verify_api_key)]
)
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (OpenAI-compatible)."""
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


async def generate_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Generate a non-streaming chat completion."""
    response_text = await qwen_client.generate(
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
    completion_tokens = len(response_text.split())

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
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
    )


async def stream_chat_completion(request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Generate a streaming chat completion."""
    chunk_id = f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    got_content = False

    try:
        async for token in qwen_client.generate_stream(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            got_content = True
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

    except RuntimeError:
        # If we got content before the error, send the final chunk gracefully
        pass

    # Always send final chunk with finish_reason
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
