import asyncio
import json
import logging
from typing import AsyncGenerator, List, Optional
from datetime import datetime

from config import settings
from schemas import ChatMessage

logger = logging.getLogger(__name__)


class QwenCLIClient:
    """Client for interacting with Qwen CLI."""
    
    def __init__(self):
        self.model = settings.QWEN_MODEL
        self.timeout = settings.QWEN_TIMEOUT
    
    def _build_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert OpenAI format messages to a single prompt for Qwen CLI."""
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"<|system|>\n{msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"<|user|>\n{msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{msg.content}")
        
        # Add the assistant prompt to trigger response
        prompt_parts.append("<|assistant|>")
        
        return "\n".join(prompt_parts)
    
    async def generate(self, messages: List[ChatMessage], **kwargs) -> str:
        """Generate a response using Qwen CLI (non-streaming)."""
        prompt = self._build_prompt(messages)
        
        # Build CLI command for Qwen Code
        cmd = [
            settings.QWEN_CLI_PATH,
            "-m", self.model,
            "-p", prompt,
            "--auth-type", "qwen-oauth",
            "--yolo",  # Auto-accept
        ]

        logger.info(f"Running Qwen CLI: {' '.join(cmd[:4])}...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024  # 1MB buffer
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Qwen CLI error: {error_msg}")
                raise RuntimeError(f"Qwen CLI failed: {error_msg}")
            
            response = stdout.decode().strip()
            logger.info(f"Qwen CLI response length: {len(response)}")
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Qwen CLI timed out after {self.timeout}s")
            raise RuntimeError(f"Qwen CLI timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Qwen CLI execution error: {str(e)}")
            raise RuntimeError(f"Qwen CLI execution error: {str(e)}")
    
    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Qwen CLI."""
        prompt = self._build_prompt(messages)
        
        # Build CLI command for Qwen Code
        cmd = [
            settings.QWEN_CLI_PATH,
            "-m", self.model,
            "-p", prompt,
            "--auth-type", "qwen-oauth",
            "--yolo",  # Auto-accept
        ]

        logger.info(f"Running Qwen CLI (streaming): {' '.join(cmd[:4])}...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024
            )
            
            # Read output line by line
            async for line in process.stdout:
                text = line.decode().strip()
                if text:
                    yield text
            
            # Check for errors
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Qwen CLI stream error: {error_msg}")
                raise RuntimeError(f"Qwen CLI failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Qwen CLI streaming error: {str(e)}")
            raise RuntimeError(f"Qwen CLI streaming error: {str(e)}")


# Global client instance
qwen_client = QwenCLIClient()
