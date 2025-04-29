from fastmcp import Client
from fastmcp.client.transports import SSETransport
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


sse_url = "http://127.0.0.1:8000/sse"

# Option 1: Inferred transport
# client = Client(sse_url)

# # Option 2: Explicit transport (e.g., to add custom headers)
headers = {"Authorization": os.environ.get("ROOTDATA_MCP_API_TOKEN")}
transport_explicit = SSETransport(url=sse_url, headers=headers)
client = Client(transport_explicit)


async def main():
    # Connection is established here
    async with client:
        # Make MCP calls within the context
        tools = await client.list_tools()
        print(f"Connected via SSE, found tools: {tools}")

        # if any(tool.name == "add" for tool in tools):
        #     result = await client.call_tool("add", {"a": 1, "b": 2})
        #     print(f"Greet result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
