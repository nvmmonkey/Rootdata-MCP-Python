#!/usr/bin/env python
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
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
mcp = FastMCP("Rootdata", dependencies=["python-dotenv", "httpx", "pydantic"])

# ----- Input Models -----


# Basic endpoints
class SearchArgs(BaseModel):
    query: str = Field(..., description="Search keywords")
    precise_x_search: Optional[bool] = Field(
        None, description="Search by X handle (@...)"
    )


class GetProjectArgs(BaseModel):
    project_id: int = Field(..., description="Project ID")
    include_team: Optional[bool] = Field(None, description="Include team members")
    include_investors: Optional[bool] = Field(None, description="Include investors")


class GetOrgArgs(BaseModel):
    org_id: int = Field(..., description="Organization ID")
    include_team: Optional[bool] = Field(None, description="Include team members")
    include_investments: Optional[bool] = Field(None, description="Include investments")


class GetPeopleArgs(BaseModel):
    people_id: int = Field(..., description="Person ID")


class GetInvestorsArgs(BaseModel):
    page: Optional[int] = Field(1, description="Page number (default: 1)")
    page_size: Optional[int] = Field(
        CONFIG["DEFAULT_PAGE_SIZE"],
        description="Items per page (default: 10, max: 100)",
    )


class GetFundingRoundsArgs(BaseModel):
    page: Optional[int] = Field(1, description="Page number")
    page_size: Optional[int] = Field(
        CONFIG["DEFAULT_PAGE_SIZE"], description="Items per page (max: 200)"
    )
    start_time: Optional[str] = Field(None, description="Start date (yyyy-MM)")
    end_time: Optional[str] = Field(None, description="End date (yyyy-MM)")
    min_amount: Optional[int] = Field(None, description="Minimum funding amount (USD)")
    max_amount: Optional[int] = Field(None, description="Maximum funding amount (USD)")
    project_id: Optional[int] = Field(None, description="Project ID")


class SyncUpdateArgs(BaseModel):
    begin_time: int = Field(..., description="Start timestamp")
    end_time: Optional[int] = Field(None, description="End timestamp")


class HotProjectsArgs(BaseModel):
    days: int = Field(..., description="Time period (1 or 7 days)", ge=1, le=7)


class XHotProjectsArgs(BaseModel):
    heat: Optional[bool] = Field(True, description="Get heat ranking")
    influence: Optional[bool] = Field(True, description="Get influence ranking")
    followers: Optional[bool] = Field(True, description="Get followers ranking")


class XPopularFiguresArgs(BaseModel):
    page: Optional[int] = Field(1, description="Page number")
    page_size: Optional[int] = Field(
        CONFIG["DEFAULT_PAGE_SIZE"], description="Items per page (max: 100)"
    )
    rank_type: Literal["heat", "influence"] = Field(..., description="Ranking type")


class JobChangesArgs(BaseModel):
    recent_joinees: Optional[bool] = Field(True, description="Get recent job joiners")
    recent_resignations: Optional[bool] = Field(
        True, description="Get recent resignations"
    )


class ProjectsByEcosystemArgs(BaseModel):
    ecosystem_ids: str = Field(..., description="Comma-separated ecosystem IDs")


class ProjectsByTagsArgs(BaseModel):
    tag_ids: str = Field(..., description="Comma-separated tag IDs")


# Advanced endpoints
class ComprehensiveQueryArgs(BaseModel):
    query: str = Field(
        ...,
        description="Natural language query about crypto projects, investors, or trends",
    )
    analysis_type: Optional[
        Literal[
            "project", "investor", "ecosystem", "trends", "fundraising", "comprehensive"
        ]
    ] = Field("comprehensive", description="Type of analysis to perform")
    timeframe: Optional[str] = Field(
        None, description="Time period for analysis (e.g., '7d', '30d', '2024-01')"
    )
    depth: Optional[Literal["basic", "detailed", "full"]] = Field(
        "detailed", description="Level of detail required"
    )
    include_related: Optional[bool] = Field(
        False, description="Include related entities in the analysis"
    )


class InvestigateEntityArgs(BaseModel):
    entity_name: str = Field(
        ..., description="Name of the project, investor, or person"
    )
    entity_type: Optional[Literal["project", "investor", "person", "auto"]] = Field(
        "auto", description="Type of entity"
    )
    investigation_scope: Optional[
        Literal["basic", "funding", "social", "ecosystem", "all"]
    ] = Field("basic", description="What aspects to investigate")


class FilterBy(BaseModel):
    ecosystem: Optional[str] = Field(None, description="Filter by ecosystem name")
    tags: Optional[str] = Field(None, description="Filter by tags")
    min_funding: Optional[int] = Field(None, description="Minimum funding amount")


class TrackTrendsArgs(BaseModel):
    category: Literal[
        "hot_projects", "funding", "job_changes", "new_tokens", "ecosystem", "all"
    ] = Field(..., description="Category to track")
    time_range: Optional[Literal["1d", "7d", "30d", "3m"]] = Field(
        "7d", description="Time range for trends"
    )
    filter_by: Optional[FilterBy] = Field(None, description="Filtering options")


class CompareEntitiesArgs(BaseModel):
    entities: List[str] = Field(..., description="List of entity names to compare")
    compare_type: Optional[
        Literal["metrics", "funding", "ecosystem", "social", "all"]
    ] = Field("all", description="Type of comparison")


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


def generate_summary(result: Dict[str, Any], args: ComprehensiveQueryArgs) -> str:
    """Generate a summary for comprehensive analysis results"""
    summary = f'Analysis for "{args.query}":\n\n'

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


# ----- Advanced Analysis Tools -----


@mcp.tool()
async def analyzeComprehensive(args: ComprehensiveQueryArgs) -> Dict[str, Any]:
    """Comprehensive analysis combining multiple RootData endpoints for a holistic view"""
    result = {"primary_data": None, "summary": None}

    # First, search for the main entity
    search_response = await make_api_request(
        "ser_inv",
        {
            "query": args.query,
            "precise_x_search": False,
        },
    )

    if not search_response.get("data") or len(search_response["data"]) == 0:
        raise ValueError(f"No results found for query: {args.query}")

    main_entity = search_response["data"][0]

    # Based on entity type and analysis requirements, fetch relevant data
    if main_entity["type"] == 1:  # Project
        # Get detailed project info
        project_response = await make_api_request(
            "get_item",
            {
                "project_id": main_entity["id"],
                "include_team": args.depth != "basic",
                "include_investors": args.depth != "basic",
            },
        )
        result["primary_data"] = project_response["data"]

        # Get funding rounds if requested
        if args.analysis_type in ["comprehensive", "fundraising"]:
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
        if args.include_related:
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
        if args.analysis_type in ["trends", "comprehensive"]:
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
                "include_team": args.depth != "basic",
                "include_investments": True,
            },
        )
        result["primary_data"] = org_response["data"]

        # Get recent funding activities
        if args.analysis_type in ["comprehensive", "investor"]:
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
        if args.include_related:
            job_changes_response = await make_api_request(
                "job_changes",
                {
                    "recent_joinees": True,
                    "recent_resignations": True,
                },
            )
            result["people"] = job_changes_response["data"]

    # Get market trends if comprehensive analysis
    if args.analysis_type == "comprehensive":
        tokens_response = await make_api_request("new_tokens", {})
        result["tokens"] = tokens_response["data"]

    # Generate summary
    result["summary"] = generate_summary(result, args)

    return result


@mcp.tool()
async def investigateEntity(args: InvestigateEntityArgs) -> Dict[str, Any]:
    """Deep dive into a specific entity with all related information"""
    # First identify the entity
    search_response = await make_api_request(
        "ser_inv",
        {
            "query": args.entity_name,
        },
    )

    if not search_response.get("data") or len(search_response["data"]) == 0:
        raise ValueError(f"Entity not found: {args.entity_name}")

    entity = search_response["data"][0]
    investigation = {
        "entity_info": entity,
        "details": None,
        "related_data": {},
    }

    # If entity_type is specified and doesn't match, try to find a better match
    if args.entity_type != "auto":
        type_map = {"project": 1, "investor": 2, "person": 3}
        expected_type = type_map.get(args.entity_type)

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

        if args.investigation_scope in ["funding", "all"]:
            funding_response = await make_api_request(
                "get_fac",
                {
                    "project_id": entity["id"],
                },
            )
            investigation["related_data"]["funding"] = funding_response["data"]

        if args.investigation_scope in ["social", "all"]:
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

        if args.investigation_scope in ["ecosystem", "all"]:
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

        if args.investigation_scope in ["funding", "all"]:
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

        if args.investigation_scope in ["social", "all"]:
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
async def trackTrends(args: TrackTrendsArgs) -> Dict[str, Any]:
    """Track market trends across projects, funding, and social metrics"""
    trends = {}

    if args.category in ["hot_projects", "all"]:
        hot_projects_response = await make_api_request(
            "hot_index",
            {
                "days": 1 if args.time_range == "1d" else 7,
            },
        )
        trends["hot_projects"] = hot_projects_response["data"]

    if args.category in ["funding", "all"]:
        end_date = datetime.now()
        start_date = end_date

        # Calculate start date based on time range
        if args.time_range == "1d":
            start_date = end_date - timedelta(days=1)
        elif args.time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif args.time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif args.time_range == "3m":
            start_date = end_date - timedelta(days=90)
        else:
            # Default to 7 days
            start_date = end_date - timedelta(days=7)

        funding_response = await make_api_request(
            "get_fac",
            {
                "start_time": start_date.strftime("%Y-%m"),
                "end_time": end_date.strftime("%Y-%m"),
                "min_amount": args.filter_by.min_funding if args.filter_by else None,
            },
        )
        trends["funding"] = funding_response["data"]

    if args.category in ["job_changes", "all"]:
        job_changes_response = await make_api_request(
            "job_changes",
            {
                "recent_joinees": True,
                "recent_resignations": True,
            },
        )
        trends["job_changes"] = job_changes_response["data"]

    if args.category in ["new_tokens", "all"]:
        new_tokens_response = await make_api_request("new_tokens", {})
        trends["new_tokens"] = new_tokens_response["data"]

    if args.category in ["ecosystem", "all"]:
        ecosystem_map_response = await make_api_request("ecosystem_map", {})
        trends["ecosystem_map"] = ecosystem_map_response["data"]

        if args.filter_by and args.filter_by.ecosystem:
            ecosystem_name = args.filter_by.ecosystem
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
async def compareEntities(args: CompareEntitiesArgs) -> Dict[str, Any]:
    """Compare multiple projects or investors side by side"""
    comparison = {"entities": [], "metrics": {}, "summary": ""}

    # Search for all entities
    for entity_name in args.entities:
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

                if args.compare_type in ["funding", "all"]:
                    funding_response = await make_api_request(
                        "get_fac",
                        {
                            "project_id": entity["id"],
                        },
                    )
                    entity_data["funding"] = funding_response["data"]

                if args.compare_type in ["social", "all"]:
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
        comparison["entities"], args.compare_type
    )
    comparison["summary"] = generate_comparison_summary(comparison)

    return comparison


# ----- Basic MCP Tools -----


@mcp.tool()
async def searchEntities(args: SearchArgs) -> Dict[str, Any]:
    """Search for projects, VCs, or people by keywords"""
    response = await make_api_request(
        "ser_inv",
        {
            "query": args.query,
            "precise_x_search": args.precise_x_search,
        },
    )
    return response["data"]


@mcp.tool()
async def getProject(args: GetProjectArgs) -> Dict[str, Any]:
    """Get detailed project information"""
    response = await make_api_request(
        "get_item",
        {
            "project_id": args.project_id,
            "include_team": args.include_team,
            "include_investors": args.include_investors,
        },
    )
    return response["data"]


@mcp.tool()
async def getOrg(args: GetOrgArgs) -> Dict[str, Any]:
    """Get detailed VC/organization information"""
    response = await make_api_request(
        "get_org",
        {
            "org_id": args.org_id,
            "include_team": args.include_team,
            "include_investments": args.include_investments,
        },
    )
    return response["data"]


@mcp.tool()
async def getPeople(args: GetPeopleArgs) -> Dict[str, Any]:
    """Get detailed information about a person (Pro only)"""
    response = await make_api_request(
        "get_people",
        {
            "people_id": args.people_id,
        },
    )
    return response["data"]


@mcp.tool()
async def getInvestors(args: GetInvestorsArgs) -> Dict[str, Any]:
    """Get investor information in batches (Plus/Pro only)"""
    response = await make_api_request(
        "get_invest",
        {
            "page": args.page,
            "page_size": min(args.page_size, CONFIG["MAX_PAGE_SIZE"]),
        },
    )
    return response["data"]


@mcp.tool()
async def getFundingRounds(args: GetFundingRoundsArgs) -> Dict[str, Any]:
    """Get fundraising rounds information (Plus/Pro only)"""
    response = await make_api_request(
        "get_fac",
        {
            "page": args.page,
            "page_size": min(args.page_size, 200),
            "start_time": args.start_time,
            "end_time": args.end_time,
            "min_amount": args.min_amount,
            "max_amount": args.max_amount,
            "project_id": args.project_id,
        },
    )
    return response["data"]


@mcp.tool()
async def syncUpdate(args: SyncUpdateArgs) -> Dict[str, Any]:
    """Get projects updated within a time range (Pro only)"""
    response = await make_api_request(
        "ser_change",
        {
            "begin_time": args.begin_time,
            "end_time": args.end_time,
        },
    )
    return response["data"]


@mcp.tool()
async def getHotProjects(args: HotProjectsArgs) -> Dict[str, Any]:
    """Get top 100 hot crypto projects (Pro only)"""
    response = await make_api_request(
        "hot_index",
        {
            "days": args.days,
        },
    )
    return response["data"]


@mcp.tool()
async def getXHotProjects(args: XHotProjectsArgs) -> Dict[str, Any]:
    """Get X platform hot projects rankings (Pro only)"""
    response = await make_api_request(
        "hot_project_on_x",
        {
            "heat": args.heat,
            "influence": args.influence,
            "followers": args.followers,
        },
    )
    return response["data"]


@mcp.tool()
async def getXPopularFigures(args: XPopularFiguresArgs) -> Dict[str, Any]:
    """Get X platform popular figures (Pro only)"""
    response = await make_api_request(
        "leading_figures_on_crypto_x",
        {
            "page": args.page,
            "page_size": min(args.page_size, CONFIG["MAX_PAGE_SIZE"]),
            "rank_type": args.rank_type,
        },
    )
    return response["data"]


@mcp.tool()
async def getJobChanges(args: JobChangesArgs) -> Dict[str, Any]:
    """Get job position changes (Pro only)"""
    response = await make_api_request(
        "job_changes",
        {
            "recent_joinees": args.recent_joinees,
            "recent_resignations": args.recent_resignations,
        },
    )
    return response["data"]


@mcp.tool()
async def getNewTokens() -> Dict[str, Any]:
    """Get newly issued tokens in the past 3 months (Pro only)"""
    response = await make_api_request("new_tokens", {})
    return response["data"]


@mcp.tool()
async def getEcosystemMap() -> Dict[str, Any]:
    """Get ecosystem map list (Pro only)"""
    response = await make_api_request("ecosystem_map", {})
    return response["data"]


@mcp.tool()
async def getTagMap() -> Dict[str, Any]:
    """Get tag map list (Pro only)"""
    response = await make_api_request("tag_map", {})
    return response["data"]


@mcp.tool()
async def getProjectsByEcosystem(args: ProjectsByEcosystemArgs) -> Dict[str, Any]:
    """Get projects by ecosystem IDs (Pro only)"""
    response = await make_api_request(
        "projects_by_ecosystems",
        {
            "ecosystem_ids": args.ecosystem_ids,
        },
    )
    return response["data"]


@mcp.tool()
async def getProjectsByTags(args: ProjectsByTagsArgs) -> Dict[str, Any]:
    """Get projects by tag IDs (Pro only)"""
    response = await make_api_request(
        "projects_by_tags",
        {
            "tag_ids": args.tag_ids,
        },
    )
    return response["data"]


# ----- Run the server -----
if __name__ == "__main__":
    mcp.run()
