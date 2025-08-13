"""
This Domino MCP Server extended with helper functions for building Streamlit apps
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

# -------------------------------------------------------------------------
# Additional helper functions for Streamlit app development on Domino
# -------------------------------------------------------------------------

@mcp.tool()
async def list_compute_environments() -> Dict[str, Any]:
    """
    List compute environments visible to the authenticated Domino user.

    This function calls the Domino beta API endpoint to retrieve the environments
    that a user can see. Each environment is returned with its id and name.
    """
    api_url = f"{domino_host}/api/environments/beta/environments?offset=0&limit=100"
    headers = {"X-Domino-Api-Key": domino_api_key}
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        envs = response.json()
        environment_list: List[Dict[str, str]] = []
        for env in envs:
            env_id = env.get("id")
            env_name = env.get("name") or env.get("title") or env.get("environmentName")
            environment_list.append({"id": env_id, "name": env_name})
        return {"environments": environment_list}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
async def list_hardware_tiers(include_archived: bool = False) -> Dict[str, Any]:
    """
    List hardware tiers available on the Domino deployment.

    The Domino API exposes hardware tiers via `/api/hardwaretiers/v1/hardwaretiers`.
    This function fetches up to 100 tiers by default and returns id and name.

    Args:
        include_archived (bool): Whether to include archived hardware tiers. Default False.
    """
    include = "true" if include_archived else "false"
    api_url = f"{domino_host}/api/hardwaretiers/v1/hardwaretiers?offset=0&limit=100&includeArchived={include}"
    headers = {"X-Domino-Api-Key": domino_api_key}
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        tiers = response.json()
        hardware_list: List[Dict[str, str]] = []
        for tier in tiers:
            tier_id = tier.get("id")
            tier_name = tier.get("hardwareTierName") or tier.get("name") or tier.get("displayName")
            hardware_list.append({"id": tier_id, "name": tier_name})
        return {"hardware_tiers": hardware_list}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
async def scaffold_streamlit_app(app_name: str) -> Dict[str, Any]:
    """
    Create a basic Streamlit app scaffold (app.py and app.sh) in the project root.

    The generated `app.py` contains a simple form that prompts users to specify
    the name and description for a new Domino app, choose an environment and hardware tier,
    and optionally publish the app using Domino's python-domino SDK.  The `app.sh`
    script runs the Streamlit application on Domino's required port and address.

    Args:
        app_name (str): The name of the Streamlit app to scaffold.

    Returns:
        Dict[str, Any]: A summary of the created files or an error message.
    """
    try:
        # Sanitize app name for filenames (replace spaces with underscores)
        safe_name = re.sub(r"\s+", "_", app_name.strip())
        app_py_path = f"{safe_name}.py"
        app_sh_path = f"{safe_name}.sh"
        # Define the contents of app.py
        app_py_contents = f"""import streamlit as st
from domino import Domino

st.title('Domino Streamlit App Creator')
st.write('This app helps you scaffold and publish new Domino apps.')

st.header('App Details')
new_app_name = st.text_input('New app name', value='')
new_app_description = st.text_area('Description', value='')

st.header('Execution Settings')
env_id = st.text_input('Environment ID')
hardware_tier_id = st.text_input('Hardware Tier ID')

if st.button('Publish'):
    if not new_app_name or not env_id or not hardware_tier_id:
        st.error('Please provide app name, environment ID and hardware tier ID.')
    else:
        # Create a Domino client using credentials available in the Domino workspace
        domino = Domino('{app_name}', api_key=None, host=None)
        try:
            domino.app_publish(hardwareTierId=hardware_tier_id)
            st.success('Published app ' + new_app_name)
        except Exception as e:
            st.error(f'Failed to publish: {{e}}')
"""
        # Define contents of app.sh
        app_sh_contents = f"""#!/bin/bash
streamlit run {app_py_path} --server.port=8888 --server.address=0.0.0.0
"""
        # Write files to the current working directory
        with open(app_py_path, "w", encoding="utf-8") as f_py:
            f_py.write(app_py_contents)
        with open(app_sh_path, "w", encoding="utf-8") as f_sh:
            f_sh.write(app_sh_contents)
        # Make the shell script executable
        os.chmod(app_sh_path, 0o755)
        return {"created_files": [app_py_path, app_sh_path]}
    except Exception as e:
        return {"error": f"Failed to scaffold Streamlit app: {e}"}

if __name__ == "__main__":
    # Start the MCP server when run from the command line.
    mcp.run(transport="stdio")
