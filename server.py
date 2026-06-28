import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from bot import app as bot_app
import config

server_app = FastAPI()

@server_app.get("/")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "service": "VPlay Bot Streaming Server"}

@server_app.get("/stream/{file_id}")
async def stream_media_file(file_id: str):
    """Streams a Telegram media file chunk-by-chunk on-the-fly to the player."""
    async def chunk_generator():
        try:
            # stream_media yields 1MB chunks sequentially from Telegram DC
            async for chunk in bot_app.stream_media(file_id):
                yield chunk
        except Exception as e:
            print(f"Error in on-the-fly streaming pipeline: {e}")
            
    return StreamingResponse(chunk_generator(), media_type="video/mp4")

async def start_server():
    """Launches the streaming server asynchronously inside the main event loop."""
    server_config = uvicorn.Config(
        app=server_app,
        host="0.0.0.0",
        port=config.PORT,
        log_level="warning"
    )
    server = uvicorn.Server(server_config)
    # Start server as an async task
    asyncio.create_task(server.serve())
