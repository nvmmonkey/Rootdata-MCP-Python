import asyncio
import os
from typing import Any
from fastmcp import Client
from fastmcp.client.transports import SSETransport
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerSse
from agents.model_settings import ModelSettings
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()


sse_url = "http://127.0.0.1:8000/sse"

# Option 1: Inferred transport
client = Client(sse_url)

# # Option 2: Explicit transport (e.g., to add custom headers)
# headers = {"Authorization": os.environ.get("ROOTDATA_MCP_API_TOKEN")}
# transport_explicit = SSETransport(url=sse_url, headers=headers)
# client = Client(transport_explicit)


class SearchArgs(BaseModel):
    query: str = Field(..., description="Search keywords")
    precise_x_search: Optional[bool] = Field(
        None, description="Search by X handle (@...)"
    )


async def run(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to answer the questions.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(tool_choice="required"),
    )

    async with client:
        tools = await client.list_tools()
        # print(f"Connected via SSE, found tools: {tools}")

        if any(tool.name == "searchEntities" for tool in tools):
            search_args = {"query": "Vitalik", "precise_x_search": False}
            result = await client.call_tool("searchEntities", search_args)
            print(result)

    message = "Introduce crypto entity Vitalik who found Ethereum using the metadata result from Rootdata MCP"
    prompt = (
        "Introduce crypto entity Vitalik who found Ethereum using the metadata result from Rootdata MCP"
        + str(result)
    )
    print(f"Running: {message}")
    result = await Runner.run(starting_agent=agent, input=prompt)
    print(result.final_output)


async def main():
    async with MCPServerSse(
        name="SSE Python Server",
        params={
            "url": "http://localhost:8000/sse",
        },
    ) as server:
        await run(server)


if __name__ == "__main__":
    asyncio.run(main())
