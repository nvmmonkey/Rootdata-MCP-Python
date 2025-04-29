# RootData MCP Python

A Python-based Model Completion Protocol (MCP) server for accessing the RootData API. This project provides a comprehensive toolkit for crypto market intelligence, enabling AI agents and applications to fetch detailed information about crypto projects, investors, market trends, and more.

## Overview

RootData MCP Python creates a bridge between AI assistants/agents and the RootData API, which offers extensive data about the cryptocurrency ecosystem. The project uses FastMCP to create a Model Completion Protocol server that can be accessed via different transport methods:

- Server-Sent Events (SSE)
- Standard IO (stdio)
- Cloudflare Workers

## Features

- **Comprehensive Crypto Data**: Access detailed information about projects, investors, and market trends
- **AI-friendly Interface**: Designed to be easily used by AI assistants and agents
- **Multiple Transport Options**: Support for SSE, stdio, and Cloudflare deployment
- **Advanced Analysis Tools**: High-level functions for comprehensive crypto market analysis
- **Modular Design**: Clean separation between API interaction and MCP server functionality

## Installation

### Prerequisites

- Python 3.12+
- RootData API key

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/rootdata-mcp-python.git
cd rootdata-mcp-python
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
pip install -e .

# use uv cli
uv sync
uv run file-name.py
```

3. Create a `.env` file based on the provided `.env.example`:
```bash
cp .env.example .env
```

4. Add your RootData API key to the `.env` file:
```
ROOTDATA_API_KEY=your_api_key_here
```
### Claude Desktop Integration (For Regular Use)

Use `fastmcp install` to set up your server for persistent use within the Claude Desktop app. It handles creating an isolated environment using `uv`.

```bash
fastmcp install your_server_file.py
# With a custom name in Claude
fastmcp install your_server_file.py --name "My Analysis Tool"
# With extra packages and environment variables
fastmcp install server.py --with requests -v API_KEY=123 -f .env
```

## Usage

### Running the Server

There are three server options available:

#### 1. SSE Server (for web clients)

```bash
python rootdata_server_sse.py
```

This will start an SSE server at `http://127.0.0.1:8000`.

#### 2. Standard IO Server (for direct integration)

```bash
python rootdata_server_stdio.py
```

Ideal for direct integration with applications.

#### 3. Cloudflare Server (for cloud deployment)

```bash
python rootdata_server_cloudflare.py
```

Optimized for deployment to Cloudflare Workers.

### Client Examples

The `examples` directory contains sample clients that demonstrate how to connect to the server:

- `rootdata_client_sse.py`: Example of connecting via SSE
- `rootdata_client_stdio.py`: Example of connecting via stdio
- `rootdata_client_openai.py`: Example of integration with OpenAI

### Available Tools

The server provides several categories of tools:

#### Basic Tools
- `searchEntities`: Search for projects, VCs, or people by keywords
- `getProject`: Get detailed project information
- `getOrg`: Get detailed VC/organization information
- And many more specific data retrieval tools

#### Advanced Analysis Tools
- `analyzeComprehensive`: Comprehensive analysis combining multiple RootData endpoints
- `investigateEntity`: Deep dive into a specific entity with all related information
- `trackTrends`: Track market trends across projects, funding, and social metrics
- `compareEntities`: Compare multiple projects or investors side by side

## Search Strategies

For best results, the following search strategies are recommended:

### Project Research
1. Start with `searchEntities(query='project_name')` to identify the project
2. Use `investigateEntity(entity_name='project_name', investigation_scope='all')` for deep analysis
3. Optionally use `trackTrends` and `compareEntities` to place in context

### Investor Analysis
1. Start with `searchEntities(query='investor_name')` to identify the investor
2. Use `investigateEntity(entity_name='investor_name', entity_type='investor')` for portfolio analysis
3. Examine recent investments with `getFundingRounds` or `getInvestors`

### Market Trends
1. Use `trackTrends(category='all', time_range='7d')` for a broad market overview
2. Identify hot projects with `getHotProjects(days=7)` or `getXHotProjects()`
3. Examine funding trends with `getFundingRounds()` for recent activity

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Specify your license here]

## Acknowledgements

- [RootData](https://rootdata.com/) for providing the crypto market intelligence API
- [FastMCP](https://github.com/fixie-ai/fastmcp) for the Model Completion Protocol implementation
