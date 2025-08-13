"""
Domino MCP Server extended with helper functions for building Streamlit apps
This file is based on the original domino_mcp_server repository.
It defines additional tool functions to list Domino compute environments and hardware tiers,
and to scaffold a basic Streamlit app within a Domino project.

NOTE: To use these tools you need to set up a `.env` file in the same directory containing
your `DOMINO_API_KEY` and `DOMINO_HOST`.  See the project README for details【413309742005627†L288-L337】.
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
import requests
import asyncio
import os
from dotenv import load_dotenv
import re
import webbrowser
import urllib.parse
import json

# Load environment variables (DOMINO_API_KEY and DOMINO_HOST)
load_dotenv()

domino_api_key = os.getenv("DOMINO_API_KEY")
domino_host = os.getenv("DOMINO_HOST")

if not domino_api_key:
    raise ValueError("DOMINO_API_KEY environment variable not set.")



def _validate_url_parameter(param_value: str, param_name: str) -> str:
    """
    Validates and URL-encodes a parameter for safe use in URLs.
    Supports international characters by encoding them properly.

    Args:
        param_value (str): The parameter value to validate and encode
        param_name (str): The name of the parameter (for error messages)

    Returns:
        str: The URL-encoded parameter value

    Raises:
        ValueError: If the parameter contains unsafe URL characters
    """
    if param_value is None:
        raise ValueError(f"{param_name} is required")
    # Basic safety check - reject if contains dangerous chars that could break URL structure
    if any(char in param_value for char in ['/', '\\', '?', '#', '&', '=', '%']):
        raise ValueError(f"Invalid {param_name}: '{param_value}' contains unsafe URL characters")
    return urllib.parse.quote(param_value, safe='')


def _filter_domino_stdout(stdout_text: str) -> str:
    """
    Filters the stdout text from a Domino job run to extract the relevant output.
    It extracts text between the specified start and end markers.
    """
    start_marker = "### Completed /mnt/artifacts/.domino/configure-spark-defaults.sh ###"
    end_marker = "Evaluating cleanup command on EXIT"
    try:
        start_index = stdout_text.index(start_marker) + len(start_marker)
        end_index = stdout_text.index(end_marker, start_index)
        filtered_text = stdout_text[start_index:end_index].strip()
        return filtered_text
    except ValueError:
        print("Warning: could not parse domino job output")
        return "Could not find start or end markers in stdout."


def _extract_and_format_mlflow_url(text: str, user_name: str, project_name: str) -> Optional[str]:
    """
    Finds an MLflow URL in the format http://127.0.0.1:8768/#/experiments/.../runs/...
    and reformats it to the Domino Cloud URL format.
    """
    pattern = r"http://127\.0\.0\.1:8768/#/experiments/(\d+)/runs/([a-f0-9]+)"
    match = re.search(pattern, text)
    if match:
        experiment_id, run_id = match.groups()
        new_url = f"{domino_host}/experiments/{user_name}/{project_name}/{experiment_id}/{run_id}"
        return new_url
    return None


@mcp.tool()
async def check_domino_job_run_results(user_name: str, project_name: str, run_id: str) -> Dict[str, Any]:
    """
    Return the results from a Domino job run, filtering noise and formatting any MLflow URLs.
    """
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
    encoded_run_id = _validate_url_parameter(run_id, "run_id")

    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/run/{encoded_run_id}/stdout"
    headers = {"X-Domino-Api-Key": domino_api_key}
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        raw_stdout = response.json().get('stdout', '')
        filtered_stdout = _filter_domino_stdout(raw_stdout)
        mlflow_url = _extract_and_format_mlflow_url(filtered_stdout, user_name, project_name)
        # Remove local MLflow URLs if present
        if mlflow_url:
            run_pattern = r"http://127\.0\.0\.1:8768/#/experiments/\d+/runs/[a-f0-9]+"
            experiment_pattern = r"View experiment at: http://127\.0\.0\.1:8768/#/experiments/\d+"
            lines = [line for line in filtered_stdout.splitlines()
                     if not re.search(run_pattern, line) and not re.search(experiment_pattern, line)]
            filtered_stdout = "\n".join(lines).strip()
        result: Dict[str, Any] = {"results": filtered_stdout}
        if mlflow_url:
            result["mlflow_url"] = mlflow_url
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}
    return result


@mcp.tool()
async def check_domino_job_run_status(user_name: str, project_name: str, run_id: str) -> Dict[str, Any]:
    """
    Check the status of a Domino job run.
    """
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
    encoded_run_id = _validate_url_parameter(run_id, "run_id")
    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/runs/{encoded_run_id}"
    headers = {"X-Domino-Api-Key": domino_api_key}
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}
    return result


@mcp.tool()
async def run_domino_job(user_name: str, project_name: str, run_command: str, title: str) -> Dict[str, Any]:
    """
    Run a command as a Domino job. The command should be provided as a single string (not list).
    Domino splits the command on whitespace before submitting the job.
    """
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/runs"
    headers = {
        "X-Domino-Api-Key": domino_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "command": run_command.split(),
        "isDirect": False,
        "title": title,
        "publishApiEndpoint": False,
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}
    return result


@mcp.tool()
def open_web_browser(url: str) -> bool:
    """
    Open a URL in the default web browser. Returns True if successful.
    """
    try:
        webbrowser.open_new_tab(url)
        return True
    except webbrowser.Error:
        return False
# Initialize the Fast MCP server
mcp = FastMCP("domino_server")
