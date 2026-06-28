import asyncio
import logging
from pyrogram import idle

import config
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("VPlayBot")

# Run validation FIRST before importing modules that instantiate Clients at load time
try:
    config.validate_config()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

import database
import queue_manager

async def main():
    logger.info("Initializing VPlay Bot...")
    
    # Initialize Database
    logger.info("Initializing MongoDB client...")
    database.init_db()
    
    # Start on-the-fly streaming HTTP server
    logger.info(f"Starting local streaming server on port {config.PORT}...")
    from server import start_server
    await start_server()
    
    # Import bot and assistant inside the running asyncio loop to allow their decorators to register on the active loop
    logger.info("Loading Bot and Assistant modules...")
    from bot import app as bot_app
    from assistant import assistant_app, call_py
    
    # Let the loop process the handler creation tasks
    await asyncio.sleep(0.5)
    
    # Start bot and assistant clients
    logger.info("Starting Telegram Bot account...")
    await bot_app.start()
    bot_me = await bot_app.get_me()
    logger.info(f"Bot started successfully as @{bot_me.username}")
    
    logger.info("Starting Telegram Assistant account...")
    await assistant_app.start()
    assistant_me = await assistant_app.get_me()
    logger.info(f"Assistant started successfully as @{assistant_me.username or assistant_me.id}")
    
    # Start PyTgCalls
    logger.info("Starting PyTgCalls VC media client...")
    await call_py.start()
    
    logger.info("VPlay Bot system is active and idling. Press Ctrl+C to terminate.")
    
    # Keep the program running until interrupted
    await idle()
    
    # Graceful Shutdown Sequence
    logger.info("Shutting down VPlay Bot service...")
    
    try:
        await call_py.stop()
        logger.info("PyTgCalls stopped.")
    except Exception as e:
        logger.warning(f"Error stopping PyTgCalls: {e}")
        
    try:
        await assistant_app.stop()
        logger.info("Assistant client stopped.")
    except Exception as e:
        logger.warning(f"Error stopping Assistant Client: {e}")
        
    try:
        await bot_app.stop()
        logger.info("Bot client stopped.")
    except Exception as e:
        logger.warning(f"Error stopping Bot Client: {e}")
        
    logger.info("Closing MongoDB database client...")
    await database.close_db()
    
    # Clean up downloaded media in active playing sessions
    logger.info("Cleaning up cached media files...")
    for chat_id in list(queue_manager._active_playbacks.keys()):
        state = queue_manager.get_playback(chat_id)
        if state:
            state.cleanup_local_file()
            
    logger.info("Shutdown sequence finalized successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("VPlay Bot service terminated by keyboard interrupt.")
