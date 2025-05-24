##.env
import httpx
import os
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def remote_delete_agent_state(thread_id: str) -> dict:
    AGENT_SERVER = os.getenv("AGENT_SERVER_DELETE")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(
            f"{AGENT_SERVER}/delete_thread/{thread_id}"
        )
        response.raise_for_status()
        return response.json()
