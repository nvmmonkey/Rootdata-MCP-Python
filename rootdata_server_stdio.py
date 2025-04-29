#!/usr/bin/env python
from fastmcp import FastMCP, Context
from pydantic import Field
import os
from typing import Optional, List, Dict, Any, Union, Literal
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Configuration
CONFIG = {
    "API_KEY": os.environ.get("ROOTDATA_API_KEY"),
    "API_BASE_URL": "https://api.rootdata.com/open",
    "DEFAULT_LANGUAGE": "en",
    "DEFAULT_PAGE_SIZE": 10,
    "MAX_PAGE_SIZE": 100,
}

# Validate environment variables
if not CONFIG["API_KEY"]:
    raise ValueError("ROOTDATA_API_KEY environment variable is required")

# Create the MCP server
mcp = FastMCP(
    name="Rootdata MCP",
    # host="http://127.0.0.1:8000",
    dependencies=["python-dotenv", "httpx", "pydantic"],
)

# ----- API Helper Function -----


async def make_api_request(endpoint: str, data: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Make a request to the Rootdata API."""
    import httpx

    if not CONFIG["API_KEY"]:
        raise ValueError("API key is not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONFIG['API_BASE_URL']}/{endpoint}",
            headers={
                "Content-Type": "application/json",
                "apikey": CONFIG["API_KEY"],
                "language": CONFIG["DEFAULT_LANGUAGE"],
            },
            json=data,
        )

    if response.status_code != 200:
        raise ValueError(f"Rootdata API returned status: {response.status_code}")

    result = response.json()

    if result["result"] != 200:
        raise ValueError(result.get("message", f"API Error: {result['result']}"))

    return result


# ----- Helper Functions -----


def generate_summary(
    result: Dict[str, Any],
    query: str,
    analysis_type: str,
    timeframe: Optional[str] = None,
    depth: str = "detailed",
    include_related: bool = False,
) -> str:
    """Generate a summary for comprehensive analysis results"""
    summary = f'Analysis for "{query}":\n\n'

    if result.get("primary_data"):
        primary_data = result["primary_data"]
        entity_type = (
            "Project"
            if primary_data.get("project_name")
            else "VC/Organization"
            if primary_data.get("org_name")
            else "Person"
            if primary_data.get("people_name")
            else "Entity"
        )

        name = (
            primary_data.get("project_name")
            or primary_data.get("org_name")
            or primary_data.get("people_name")
        )
        summary += f"{entity_type}: {name}\n"

        if primary_data.get("total_funding"):
            total_funding_m = primary_data["total_funding"] / 1e6
            summary += f"Total Funding: ${total_funding_m:.2f}M\n"

        if primary_data.get("establishment_date"):
            summary += f"Established: {primary_data['establishment_date']}\n"

    if result.get("trends") and result["trends"].get("hot_index"):
        hot_index = result["trends"]["hot_index"]
        summary += f"\nHot Index Rank: #{hot_index.get('rank')} (Score: {hot_index.get('eval')})\n"

    if result.get("related_projects"):
        summary += f"\nRelated Projects: {len(result['related_projects'])} projects in the same ecosystem\n"

    if result.get("fundraising") and result["fundraising"].get("items"):
        summary += f"\nFundraising Rounds: {len(result['fundraising']['items'])} rounds found\n"

    return summary


def generate_comparison_metrics(
    entities: List[Dict[str, Any]], compare_type: str
) -> Dict[str, Dict[str, Any]]:
    """Generate comparison metrics for entities"""
    metrics = {}

    for entity in entities:
        if not entity.get("basic_info"):
            continue

        name = entity["basic_info"].get("name")
        if not name:
            continue

        metrics[name] = {}

        if entity["basic_info"].get("type") == 1:  # Project
            if entity.get("details"):
                metrics[name]["funding"] = entity["details"].get("total_funding")
                metrics[name]["established_date"] = entity["details"].get(
                    "establishment_date"
                )
                metrics[name]["ecosystem"] = entity["details"].get("ecosystem")
                metrics[name]["tags"] = entity["details"].get("tags")

            if entity.get("social_metrics"):
                for category in ["heat", "influence", "followers"]:
                    if entity["social_metrics"].get(category):
                        metrics[name][category] = entity["social_metrics"][
                            category
                        ].get("score")

        elif entity["basic_info"].get("type") == 2:  # VC
            if entity.get("details"):
                if entity["details"].get("investments"):
                    metrics[name]["investment_count"] = len(
                        entity["details"]["investments"]
                    )
                metrics[name]["established_date"] = entity["details"].get(
                    "establishment_date"
                )
                metrics[name]["category"] = entity["details"].get("category")

    return metrics


def generate_comparison_summary(comparison: Dict[str, Any]) -> str:
    """Generate a summary for entity comparison"""
    summary = "Comparison Summary:\n\n"

    if not comparison.get("entities"):
        return summary + "No entities found for comparison."

    for i, entity in enumerate(comparison["entities"]):
        entity_type = (
            "Project"
            if entity["basic_info"].get("type") == 1
            else "VC"
            if entity["basic_info"].get("type") == 2
            else "Person"
            if entity["basic_info"].get("type") == 3
            else "Unknown"
        )

        summary += f"{i + 1}. {entity['basic_info'].get('name')} ({entity_type})\n"

    # Add key metric comparisons if available
    if comparison.get("metrics"):
        funding_entities = []
        for name, metrics in comparison["metrics"].items():
            if metrics.get("funding"):
                funding_entities.append((name, metrics["funding"]))

        if funding_entities:
            # Sort by funding (highest first)
            funding_entities.sort(key=lambda x: x[1], reverse=True)

            summary += "\nFunding Comparison:\n"
            for name, funding in funding_entities:
                funding_m = funding / 1e6
                summary += f"{name}: ${funding_m:.2f}M\n"

    return summary


# ----- Prompt Helper -----
@mcp.prompt()
def rootdata_research_strategy() -> Dict[str, str]:
    """System prompt for RootData research strategy."""
    return {
        "role": "system",
        "content": """When using RootData tools, ALWAYS start by calling 
        listAllTools() to understand all available capabilities and recommended 
        research strategies before proceeding with specific tool calls...""",
    }


@mcp.prompt()
def rootdata_system_prompt() -> Dict[str, str]:
    """
    System prompt that guides LLMs on how to effectively use RootData tools.
    This should be included at the beginning of conversations.
    """
    return {
        "role": "system",
        "content": """When using RootData MCP tools to research crypto projects, investors, or market trends, follow this process:

1. ALWAYS start by calling listAllTools() to understand available capabilities and recommended research strategies.
2. Select the most appropriate search strategy based on the query type:
   - For project research: First search, then get details, then examine relationships
   - For market analysis: Look at trends, then hot projects, then funding rounds
   - For investor analysis: First identify the investor, then examine their portfolio
3. For complex queries, use advanced tools like analyzeComprehensive or investigateEntity
4. For simple lookups, use basic tools directly after confirming the entity ID

The listAllTools() function will provide detailed information about each tool, including required parameters and usage examples. This will help you construct an effective research plan.

Always present findings with:
- A clear summary of key information
- Relevant metrics with context
- Significant patterns or anomalies
- Limitations of the data where appropriate""",
    }


# ----- Advanced Analysis Tools -----


@mcp.tool()
async def analyzeComprehensive(
    query: str,
    analysis_type: Optional[
        Literal[
            "project", "investor", "ecosystem", "trends", "fundraising", "comprehensive"
        ]
    ] = "comprehensive",
    timeframe: Optional[str] = None,
    depth: Optional[Literal["basic", "detailed", "full"]] = "detailed",
    include_related: Optional[bool] = False,
) -> Dict[str, Any]:
    """Comprehensive analysis combining multiple RootData endpoints for a holistic view.

    This tool intelligently combines data from multiple endpoints to provide in-depth analysis.

    TIP: For best results, first call listAllTools() to understand all available capabilities.
    If you're unsure which parameters to use, the listAllTools function will provide guidance."""
    result = {"primary_data": None, "summary": None}

    # First, search for the main entity
    search_response = await make_api_request(
        "ser_inv",
        {
            "query": query,
            "precise_x_search": False,
        },
    )

    if not search_response.get("data") or len(search_response["data"]) == 0:
        raise ValueError(f"No results found for query: {query}")

    main_entity = search_response["data"][0]

    # Based on entity type and analysis requirements, fetch relevant data
    if main_entity["type"] == 1:  # Project
        # Get detailed project info
        project_response = await make_api_request(
            "get_item",
            {
                "project_id": main_entity["id"],
                "include_team": depth != "basic",
                "include_investors": depth != "basic",
            },
        )
        result["primary_data"] = project_response["data"]

        # Get funding rounds if requested
        if analysis_type in ["comprehensive", "fundraising"]:
            funding_response = await make_api_request(
                "get_fac",
                {
                    "project_id": main_entity["id"],
                    "page": 1,
                    "page_size": 10,
                },
            )
            result["fundraising"] = funding_response["data"]

        # Get ecosystem data if requested
        if include_related:
            ecosystem_map_response = await make_api_request("ecosystem_map", {})
            # Find relevant ecosystem and get related projects
            if result["primary_data"] and result["primary_data"].get("ecosystem"):
                ecosystem_ids = []
                for eco in ecosystem_map_response["data"]:
                    if eco["ecosystem_name"] in result["primary_data"]["ecosystem"]:
                        ecosystem_ids.append(str(eco["ecosystem_id"]))

                if ecosystem_ids:
                    related_projects_response = await make_api_request(
                        "projects_by_ecosystems",
                        {
                            "ecosystem_ids": ",".join(ecosystem_ids),
                        },
                    )
                    result["related_projects"] = related_projects_response["data"]

        # Get hot index if analyzing trends
        if analysis_type in ["trends", "comprehensive"]:
            hot_index_response = await make_api_request("hot_index", {"days": 7})
            for project in hot_index_response["data"]:
                if project.get("project_id") == main_entity["id"]:
                    result["trends"] = {"hot_index": project}
                    break

    elif main_entity["type"] == 2:  # VC/Investor
        # Get detailed VC info
        org_response = await make_api_request(
            "get_org",
            {
                "org_id": main_entity["id"],
                "include_team": depth != "basic",
                "include_investments": True,
            },
        )
        result["primary_data"] = org_response["data"]

        # Get recent funding activities
        if analysis_type in ["comprehensive", "investor"]:
            investors_response = await make_api_request(
                "get_invest",
                {
                    "page": 1,
                    "page_size": 10,
                },
            )
            for investor in investors_response["data"]["items"]:
                if investor.get("invest_id") == main_entity["id"]:
                    result["investors"] = [investor]
                    break

    elif main_entity["type"] == 3:  # Person
        # Get detailed person info
        people_response = await make_api_request(
            "get_people",
            {
                "people_id": main_entity["id"],
            },
        )
        result["primary_data"] = people_response["data"]

        # Get job changes if available
        if include_related:
            job_changes_response = await make_api_request(
                "job_changes",
                {
                    "recent_joinees": True,
                    "recent_resignations": True,
                },
            )
            result["people"] = job_changes_response["data"]

    # Get market trends if comprehensive analysis
    if analysis_type == "comprehensive":
        tokens_response = await make_api_request("new_tokens", {})
        result["tokens"] = tokens_response["data"]

    # Generate summary
    result["summary"] = generate_summary(
        result, query, analysis_type, timeframe, depth, include_related
    )

    return result


@mcp.tool()
async def investigateEntity(
    entity_name: str,
    entity_type: Optional[Literal["project", "investor", "person", "auto"]] = "auto",
    investigation_scope: Optional[
        Literal["basic", "funding", "social", "ecosystem", "all"]
    ] = "basic",
) -> Dict[str, Any]:
    """Deep dive into a specific entity with all related information

    TIP: For a comprehensive research strategy, call listAllTools() first to understand all available tools and capabilities.

    """
    # First identify the entity
    search_response = await make_api_request(
        "ser_inv",
        {
            "query": entity_name,
        },
    )

    if not search_response.get("data") or len(search_response["data"]) == 0:
        raise ValueError(f"Entity not found: {entity_name}")

    entity = search_response["data"][0]
    investigation = {
        "entity_info": entity,
        "details": None,
        "related_data": {},
    }

    # If entity_type is specified and doesn't match, try to find a better match
    if entity_type != "auto":
        type_map = {"project": 1, "investor": 2, "person": 3}
        expected_type = type_map.get(entity_type)

        if expected_type and entity["type"] != expected_type:
            for potential_entity in search_response["data"]:
                if potential_entity["type"] == expected_type:
                    entity = potential_entity
                    investigation["entity_info"] = entity
                    break

    # Determine entity type and fetch appropriate data
    if entity["type"] == 1:  # Project
        project_response = await make_api_request(
            "get_item",
            {
                "project_id": entity["id"],
                "include_team": True,
                "include_investors": True,
            },
        )
        investigation["details"] = project_response["data"]

        if investigation_scope in ["funding", "all"]:
            funding_response = await make_api_request(
                "get_fac",
                {
                    "project_id": entity["id"],
                },
            )
            investigation["related_data"]["funding"] = funding_response["data"]

        if investigation_scope in ["social", "all"]:
            x_hot_projects_response = await make_api_request(
                "hot_project_on_x",
                {
                    "heat": True,
                    "influence": True,
                    "followers": True,
                },
            )

            investigation["related_data"]["social_metrics"] = {
                "heat": None,
                "influence": None,
                "followers": None,
            }

            # Find matching project in each category
            for category in ["heat", "influence", "followers"]:
                if category in x_hot_projects_response["data"]:
                    for project in x_hot_projects_response["data"][category]:
                        if project.get("project_id") == entity["id"]:
                            investigation["related_data"]["social_metrics"][
                                category
                            ] = project
                            break

        if investigation_scope in ["ecosystem", "all"]:
            ecosystem_map_response = await make_api_request("ecosystem_map", {})
            project_ecosystems = investigation["details"].get("ecosystem", [])

            if project_ecosystems:
                ecosystem_ids = []
                for eco in ecosystem_map_response["data"]:
                    if eco["ecosystem_name"] in project_ecosystems:
                        ecosystem_ids.append(str(eco["ecosystem_id"]))

                if ecosystem_ids:
                    related_projects_response = await make_api_request(
                        "projects_by_ecosystems",
                        {
                            "ecosystem_ids": ",".join(ecosystem_ids),
                        },
                    )
                    investigation["related_data"]["related_projects"] = (
                        related_projects_response["data"]
                    )

    elif entity["type"] == 2:  # VC
        org_response = await make_api_request(
            "get_org",
            {
                "org_id": entity["id"],
                "include_team": True,
                "include_investments": True,
            },
        )
        investigation["details"] = org_response["data"]

        if investigation_scope in ["funding", "all"]:
            investors_response = await make_api_request(
                "get_invest",
                {
                    "page": 1,
                    "page_size": 10,
                },
            )
            investigation["related_data"]["investor_analysis"] = investors_response[
                "data"
            ]

    elif entity["type"] == 3:  # Person
        people_response = await make_api_request(
            "get_people",
            {
                "people_id": entity["id"],
            },
        )
        investigation["details"] = people_response["data"]

        if investigation_scope in ["social", "all"]:
            x_popular_figures_response = await make_api_request(
                "leading_figures_on_crypto_x",
                {
                    "rank_type": "heat",
                    "page": 1,
                    "page_size": 100,
                },
            )

            for person in x_popular_figures_response["data"]["items"]:
                if person.get("people_id") == entity["id"]:
                    investigation["related_data"]["ranking"] = person
                    break

    return investigation


@mcp.tool()
async def trackTrends(
    category: Literal[
        "hot_projects", "funding", "job_changes", "new_tokens", "ecosystem", "all"
    ],
    time_range: Optional[Literal["1d", "7d", "30d", "3m"]] = "7d",
    ecosystem: Optional[str] = None,
    tags: Optional[str] = None,
    min_funding: Optional[int] = None,
) -> Dict[str, Any]:
    """Track market trends across projects, funding, and social metrics

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    trends = {}

    if category in ["hot_projects", "all"]:
        hot_projects_response = await make_api_request(
            "hot_index",
            {
                "days": 1 if time_range == "1d" else 7,
            },
        )
        trends["hot_projects"] = hot_projects_response["data"]

    if category in ["funding", "all"]:
        end_date = datetime.now()
        start_date = end_date

        # Calculate start date based on time range
        if time_range == "1d":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "3m":
            start_date = end_date - timedelta(days=90)
        else:
            # Default to 7 days
            start_date = end_date - timedelta(days=7)

        funding_response = await make_api_request(
            "get_fac",
            {
                "start_time": start_date.strftime("%Y-%m"),
                "end_time": end_date.strftime("%Y-%m"),
                "min_amount": min_funding,
            },
        )
        trends["funding"] = funding_response["data"]

    if category in ["job_changes", "all"]:
        job_changes_response = await make_api_request(
            "job_changes",
            {
                "recent_joinees": True,
                "recent_resignations": True,
            },
        )
        trends["job_changes"] = job_changes_response["data"]

    if category in ["new_tokens", "all"]:
        new_tokens_response = await make_api_request("new_tokens", {})
        trends["new_tokens"] = new_tokens_response["data"]

    if category in ["ecosystem", "all"]:
        ecosystem_map_response = await make_api_request("ecosystem_map", {})
        trends["ecosystem_map"] = ecosystem_map_response["data"]

        if ecosystem:
            ecosystem_name = ecosystem
            ecosystem_id = None

            for eco in ecosystem_map_response["data"]:
                if eco["ecosystem_name"].lower() == ecosystem_name.lower():
                    ecosystem_id = eco["ecosystem_id"]
                    break

            if ecosystem_id:
                ecosystem_projects_response = await make_api_request(
                    "projects_by_ecosystems",
                    {
                        "ecosystem_ids": str(ecosystem_id),
                    },
                )
                trends["ecosystem_projects"] = ecosystem_projects_response["data"]

    return trends


@mcp.tool()
async def compareEntities(
    entities: List[str],
    compare_type: Optional[
        Literal["metrics", "funding", "ecosystem", "social", "all"]
    ] = "all",
) -> Dict[str, Any]:
    """Compare multiple projects or investors side by side

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    comparison = {"entities": [], "metrics": {}, "summary": ""}

    # Search for all entities
    for entity_name in entities:
        search_response = await make_api_request(
            "ser_inv",
            {
                "query": entity_name,
            },
        )

        if search_response.get("data") and len(search_response["data"]) > 0:
            entity = search_response["data"][0]
            entity_data = {
                "basic_info": entity,
                "details": None,
            }

            # Fetch details based on entity type
            if entity["type"] == 1:  # Project
                project_response = await make_api_request(
                    "get_item",
                    {
                        "project_id": entity["id"],
                        "include_team": True,
                        "include_investors": True,
                    },
                )
                entity_data["details"] = project_response["data"]

                if compare_type in ["funding", "all"]:
                    funding_response = await make_api_request(
                        "get_fac",
                        {
                            "project_id": entity["id"],
                        },
                    )
                    entity_data["funding"] = funding_response["data"]

                if compare_type in ["social", "all"]:
                    x_hot_projects_response = await make_api_request(
                        "hot_project_on_x",
                        {
                            "heat": True,
                            "influence": True,
                            "followers": True,
                        },
                    )

                    entity_data["social_metrics"] = {
                        "heat": None,
                        "influence": None,
                        "followers": None,
                    }

                    # Find project in each category
                    for category in ["heat", "influence", "followers"]:
                        if category in x_hot_projects_response["data"]:
                            for project in x_hot_projects_response["data"][category]:
                                if project.get("project_id") == entity["id"]:
                                    entity_data["social_metrics"][category] = project
                                    break

            elif entity["type"] == 2:  # VC
                org_response = await make_api_request(
                    "get_org",
                    {
                        "org_id": entity["id"],
                        "include_team": True,
                        "include_investments": True,
                    },
                )
                entity_data["details"] = org_response["data"]

            elif entity["type"] == 3:  # Person
                people_response = await make_api_request(
                    "get_people",
                    {
                        "people_id": entity["id"],
                    },
                )
                entity_data["details"] = people_response["data"]

            comparison["entities"].append(entity_data)

    # Generate comparison metrics
    comparison["metrics"] = generate_comparison_metrics(
        comparison["entities"], compare_type
    )
    comparison["summary"] = generate_comparison_summary(comparison)

    return comparison


# ----- Basic MCP Tools -----
@mcp.tool()
async def listAllTools() -> Dict[str, Any]:
    """
    List all available tools with descriptions and parameter information to help the LLM decide
    which tools to use for a comprehensive search strategy.
    """
    tools_info = {
        "basic_tools": {
            "searchEntities": {
                "description": "Search for projects, VCs, or people by keywords",
                "parameters": {
                    "query": "Search keywords (required)",
                    "precise_x_search": "Search by X handle (@...) (optional)",
                },
                "example": "searchEntities(query='Ethereum', precise_x_search=False)",
            },
            "getProject": {
                "description": "Get detailed project information",
                "parameters": {
                    "project_id": "Project ID (required)",
                    "include_team": "Include team members (optional)",
                    "include_investors": "Include investors (optional)",
                },
                "example": "getProject(project_id=1234, include_team=True, include_investors=True)",
            },
            "getOrg": {
                "description": "Get detailed VC/organization information",
                "parameters": {
                    "org_id": "Organization ID (required)",
                    "include_team": "Include team members (optional)",
                    "include_investments": "Include investments (optional)",
                },
                "example": "getOrg(org_id=5678, include_team=True, include_investments=True)",
            },
            "getPeople": {
                "description": "Get detailed information about a person (Pro only)",
                "parameters": {"people_id": "Person ID (required)"},
                "example": "getPeople(people_id=9012)",
            },
            "getInvestors": {
                "description": "Get investor information in batches (Plus/Pro only)",
                "parameters": {
                    "page": "Page number (default: 1) (optional)",
                    "page_size": "Items per page (max: 100) (optional)",
                },
                "example": "getInvestors(page=1, page_size=20)",
            },
            "getFundingRounds": {
                "description": "Get fundraising rounds information (Plus/Pro only)",
                "parameters": {
                    "page": "Page number (optional)",
                    "page_size": "Items per page (max: 200) (optional)",
                    "start_time": "Start date (yyyy-MM) (optional)",
                    "end_time": "End date (yyyy-MM) (optional)",
                    "min_amount": "Minimum funding amount (USD) (optional)",
                    "max_amount": "Maximum funding amount (USD) (optional)",
                    "project_id": "Project ID (optional)",
                },
                "example": "getFundingRounds(start_time='2023-01', end_time='2023-12', min_amount=1000000)",
            },
            "syncUpdate": {
                "description": "Get projects updated within a time range (Pro only)",
                "parameters": {
                    "begin_time": "Start timestamp (required)",
                    "end_time": "End timestamp (optional)",
                },
                "example": "syncUpdate(begin_time=1640995200, end_time=1672531199)",
            },
            "getHotProjects": {
                "description": "Get top 100 hot crypto projects (Pro only)",
                "parameters": {"days": "Time period (1 or 7 days) (required)"},
                "example": "getHotProjects(days=7)",
            },
            "getXHotProjects": {
                "description": "Get X platform hot projects rankings (Pro only)",
                "parameters": {
                    "heat": "Get heat ranking (default: True) (optional)",
                    "influence": "Get influence ranking (default: True) (optional)",
                    "followers": "Get followers ranking (default: True) (optional)",
                },
                "example": "getXHotProjects(heat=True, influence=True, followers=False)",
            },
            "getXPopularFigures": {
                "description": "Get X platform popular figures (Pro only)",
                "parameters": {
                    "rank_type": "Ranking type ('heat' or 'influence') (required)",
                    "page": "Page number (default: 1) (optional)",
                    "page_size": "Items per page (max: 100) (optional)",
                },
                "example": "getXPopularFigures(rank_type='heat', page=1, page_size=20)",
            },
            "getJobChanges": {
                "description": "Get job position changes (Pro only)",
                "parameters": {
                    "recent_joinees": "Get recent job joiners (default: True) (optional)",
                    "recent_resignations": "Get recent resignations (default: True) (optional)",
                },
                "example": "getJobChanges(recent_joinees=True, recent_resignations=True)",
            },
            "getNewTokens": {
                "description": "Get newly issued tokens in the past 3 months (Pro only)",
                "parameters": {},
                "example": "getNewTokens()",
            },
            "getEcosystemMap": {
                "description": "Get ecosystem map list (Pro only)",
                "parameters": {},
                "example": "getEcosystemMap()",
            },
            "getTagMap": {
                "description": "Get tag map list (Pro only)",
                "parameters": {},
                "example": "getTagMap()",
            },
            "getProjectsByEcosystem": {
                "description": "Get projects by ecosystem IDs (Pro only)",
                "parameters": {
                    "ecosystem_ids": "Comma-separated ecosystem IDs (required)"
                },
                "example": "getProjectsByEcosystem(ecosystem_ids='1,2,3')",
            },
            "getProjectsByTags": {
                "description": "Get projects by tag IDs (Pro only)",
                "parameters": {"tag_ids": "Comma-separated tag IDs (required)"},
                "example": "getProjectsByTags(tag_ids='10,11,12')",
            },
        },
        "advanced_tools": {
            "analyzeComprehensive": {
                "description": "Comprehensive analysis combining multiple RootData endpoints for a holistic view",
                "parameters": {
                    "query": "Natural language query about crypto projects, investors, or trends (required)",
                    "analysis_type": "Type of analysis ('project', 'investor', 'ecosystem', 'trends', 'fundraising', 'comprehensive') (default: 'comprehensive') (optional)",
                    "timeframe": "Time period for analysis (e.g., '7d', '30d', '2024-01') (optional)",
                    "depth": "Level of detail ('basic', 'detailed', 'full') (default: 'detailed') (optional)",
                    "include_related": "Include related entities (default: False) (optional)",
                },
                "example": "analyzeComprehensive(query='Ethereum Layer 2 solutions', analysis_type='comprehensive', depth='detailed', include_related=True)",
            },
            "investigateEntity": {
                "description": "Deep dive into a specific entity with all related information",
                "parameters": {
                    "entity_name": "Name of the project, investor, or person (required)",
                    "entity_type": "Type of entity ('project', 'investor', 'person', 'auto') (default: 'auto') (optional)",
                    "investigation_scope": "What aspects to investigate ('basic', 'funding', 'social', 'ecosystem', 'all') (default: 'basic') (optional)",
                },
                "example": "investigateEntity(entity_name='Arbitrum', entity_type='project', investigation_scope='all')",
            },
            "trackTrends": {
                "description": "Track market trends across projects, funding, and social metrics",
                "parameters": {
                    "category": "Category to track ('hot_projects', 'funding', 'job_changes', 'new_tokens', 'ecosystem', 'all') (required)",
                    "time_range": "Time range ('1d', '7d', '30d', '3m') (default: '7d') (optional)",
                    "ecosystem": "Filter by ecosystem name (optional)",
                    "tags": "Filter by tags (optional)",
                    "min_funding": "Minimum funding amount (optional)",
                },
                "example": "trackTrends(category='funding', time_range='30d', ecosystem='Layer 2', min_funding=5000000)",
            },
            "compareEntities": {
                "description": "Compare multiple projects or investors side by side",
                "parameters": {
                    "entities": "List of entity names to compare (required)",
                    "compare_type": "Type of comparison ('metrics', 'funding', 'ecosystem', 'social', 'all') (default: 'all') (optional)",
                },
                "example": "compareEntities(entities=['Ethereum', 'Solana', 'Polygon'], compare_type='all')",
            },
        },
        "search_strategies": {
            "project_research": {
                "description": "Research a specific crypto project thoroughly",
                "recommended_flow": [
                    "1. Start with searchEntities(query='project_name') to identify the project",
                    "2. Use investigateEntity(entity_name='project_name', investigation_scope='all') for deep analysis",
                    "3. Optionally use trackTrends and compareEntities to place in context",
                ],
            },
            "investor_analysis": {
                "description": "Analyze an investment firm or VC thoroughly",
                "recommended_flow": [
                    "1. Start with searchEntities(query='investor_name') to identify the investor",
                    "2. Use investigateEntity(entity_name='investor_name', entity_type='investor', investigation_scope='funding') for portfolio analysis",
                    "3. Examine recent investments with getFundingRounds or getInvestors",
                ],
            },
            "market_trends": {
                "description": "Analyze current market trends and hot projects",
                "recommended_flow": [
                    "1. Use trackTrends(category='all', time_range='7d') for a broad market overview",
                    "2. Identify hot projects with getHotProjects(days=7) or getXHotProjects()",
                    "3. Examine funding trends with getFundingRounds() for recent activity",
                ],
            },
            "ecosystem_analysis": {
                "description": "Analyze a specific crypto ecosystem (e.g., Layer 2, DeFi)",
                "recommended_flow": [
                    "1. Get ecosystem map with getEcosystemMap() to identify ecosystem IDs",
                    "2. Get projects in the ecosystem with getProjectsByEcosystem()",
                    "3. Use compareEntities() to compare key projects within the ecosystem",
                ],
            },
            "funding_analysis": {
                "description": "Analyze recent funding activities in the crypto space",
                "recommended_flow": [
                    "1. Use getFundingRounds() with time filters to get recent rounds",
                    "2. Identify top investors with getInvestors()",
                    "3. Analyze specific projects that received funding with getProject()",
                ],
            },
            "comprehensive_query": {
                "description": "For general crypto market questions or complex queries",
                "recommended_flow": [
                    "Use analyzeComprehensive() which intelligently combines multiple endpoints"
                ],
            },
        },
    }

    return {
        "tools_info": tools_info,
        "recommendation": "Based on the query nature, select either a basic tool for simple lookups, "
        "an advanced tool for complex analysis, or follow one of the recommended "
        "search strategies for a guided multi-step approach.",
    }


@mcp.tool()
async def searchEntities(
    query: str, precise_x_search: Optional[bool] = None
) -> Dict[str, Any]:
    """Search for projects, VCs, or people by keywords

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "ser_inv",
        {
            "query": query,
            "precise_x_search": precise_x_search,
        },
    )
    return response["data"]


@mcp.tool()
async def getProject(
    project_id: int,
    include_team: Optional[bool] = None,
    include_investors: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get detailed project information

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "get_item",
        {
            "project_id": project_id,
            "include_team": include_team,
            "include_investors": include_investors,
        },
    )
    return response["data"]


@mcp.tool()
async def getOrg(
    org_id: int,
    include_team: Optional[bool] = None,
    include_investments: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get detailed VC/organization information

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "get_org",
        {
            "org_id": org_id,
            "include_team": include_team,
            "include_investments": include_investments,
        },
    )
    return response["data"]


@mcp.tool()
async def getPeople(people_id: int) -> Dict[str, Any]:
    """Get detailed information about a person (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "get_people",
        {
            "people_id": people_id,
        },
    )
    return response["data"]


@mcp.tool()
async def getInvestors(
    page: Optional[int] = 1, page_size: Optional[int] = None
) -> Dict[str, Any]:
    """Get investor information in batches (Plus/Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    if page_size is None:
        page_size = CONFIG["DEFAULT_PAGE_SIZE"]

    response = await make_api_request(
        "get_invest",
        {
            "page": page,
            "page_size": min(page_size, CONFIG["MAX_PAGE_SIZE"]),
        },
    )
    return response["data"]


@mcp.tool()
async def getFundingRounds(
    page: Optional[int] = 1,
    page_size: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    project_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get fundraising rounds information (Plus/Pro only

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    if page_size is None:
        page_size = CONFIG["DEFAULT_PAGE_SIZE"]

    response = await make_api_request(
        "get_fac",
        {
            "page": page,
            "page_size": min(page_size, 200),
            "start_time": start_time,
            "end_time": end_time,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "project_id": project_id,
        },
    )
    return response["data"]


@mcp.tool()
async def syncUpdate(begin_time: int, end_time: Optional[int] = None) -> Dict[str, Any]:
    """Get projects updated within a time range (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "ser_change",
        {
            "begin_time": begin_time,
            "end_time": end_time,
        },
    )
    return response["data"]


@mcp.tool()
async def getHotProjects(days: int) -> Dict[str, Any]:
    """Get top 100 hot crypto projects (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "hot_index",
        {
            "days": days,
        },
    )
    return response["data"]


@mcp.tool()
async def getXHotProjects(
    heat: Optional[bool] = True,
    influence: Optional[bool] = True,
    followers: Optional[bool] = True,
) -> Dict[str, Any]:
    """Get X platform hot projects rankings (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "hot_project_on_x",
        {
            "heat": heat,
            "influence": influence,
            "followers": followers,
        },
    )
    return response["data"]


@mcp.tool()
async def getXPopularFigures(
    rank_type: Literal["heat", "influence"],
    page: Optional[int] = 1,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Get X platform popular figures (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    if page_size is None:
        page_size = CONFIG["DEFAULT_PAGE_SIZE"]

    response = await make_api_request(
        "leading_figures_on_crypto_x",
        {
            "page": page,
            "page_size": min(page_size, CONFIG["MAX_PAGE_SIZE"]),
            "rank_type": rank_type,
        },
    )
    return response["data"]


@mcp.tool()
async def getJobChanges(
    recent_joinees: Optional[bool] = True, recent_resignations: Optional[bool] = True
) -> Dict[str, Any]:
    """Get job position changes (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "job_changes",
        {
            "recent_joinees": recent_joinees,
            "recent_resignations": recent_resignations,
        },
    )
    return response["data"]


@mcp.tool()
async def getNewTokens() -> Dict[str, Any]:
    """Get newly issued tokens in the past 3 months (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request("new_tokens", {})
    return response["data"]


@mcp.tool()
async def getEcosystemMap() -> Dict[str, Any]:
    """Get ecosystem map list (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request("ecosystem_map", {})
    return response["data"]


@mcp.tool()
async def getTagMap() -> Dict[str, Any]:
    """Get tag map list (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request("tag_map", {})
    return response["data"]


@mcp.tool()
async def getProjectsByEcosystem(ecosystem_ids: str) -> Dict[str, Any]:
    """Get projects by ecosystem IDs (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "projects_by_ecosystems",
        {
            "ecosystem_ids": ecosystem_ids,
        },
    )
    return response["data"]


@mcp.tool()
async def getProjectsByTags(tag_ids: str) -> Dict[str, Any]:
    """Get projects by tag IDs (Pro only)

    TIP: For comprehensive research, call listAllTools() first to understand
    available tools and develop a strategic approach.
    """
    response = await make_api_request(
        "projects_by_tags",
        {
            "tag_ids": tag_ids,
        },
    )
    return response["data"]


# ----- Run the server -----
if __name__ == "__main__":
    # mcp.run(transport="sse", host="127.0.0.1", port=8000, log_level="debug")
    mcp.run(transport="stdio")
    # import asyncio

    # asyncio.run(mcp.run_sse_async(host="127.0.0.1", port=8000, log_level="debug"))
    # asyncio.run(mcp.run)
