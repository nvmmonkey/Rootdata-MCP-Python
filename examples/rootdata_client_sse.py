from fastmcp import Client
from fastmcp.client.transports import SSETransport
import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()


sse_url = "http://127.0.0.1:8000/sse"

# Option 1: Inferred transport
# client = Client(sse_url)

# # Option 2: Explicit transport (e.g., to add custom headers)
headers = {"Authorization": os.environ.get("ROOTDATA_MCP_API_TOKEN")}
transport_explicit = SSETransport(url=sse_url, headers=headers)
client = Client(transport_explicit)


class SearchArgs(BaseModel):
    query: str = Field(..., description="Search keywords")
    precise_x_search: Optional[bool] = Field(
        None, description="Search by X handle (@...)"
    )


async def main():
    async with client:
        tools = await client.list_tools()
        # print(f"Connected via SSE, found tools: {tools}")

        if any(tool.name == "searchEntities" for tool in tools):
            search_args = {"query": "Vitalik", "precise_x_search": False}
            result = await client.call_tool("searchEntities", search_args)
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
