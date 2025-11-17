#!/usr/bin/env python3
"""
shybox_tools.py

Utility functions for interaction with shybox

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.0.0
Date: 2025-11-17
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.0.0"
__date__ = "2025-11-17"

import subprocess
import os
import sys
import json
from pathlib import Path
from typing import Any, Dict


def prepare_hmc_data(workspace_path: str, config: Dict[str, Any], time_start: str, time_end: str) -> None:    
    """
    Prepare HMC (Hydrological Model Continuum) data by executing a data conversion workflow.
    This function sets up environment variables and executes a Python workflow script
    to convert HMC forcing data from one format to another using specified configuration
    parameters and time range.
    Args:
        workspace_path (str): Path to the workspace directory containing settings and configuration files
        config (Dict[str, Any]): Configuration dictionary containing:
            - general.domain: Domain name for the HMC data processing
            - path.hmc_data: Base path to HMC data directories
        time_start (str): Start time for data processing (format should match workflow requirements)
        time_end (str): End time for data processing (format should match workflow requirements)
    Returns:
        None
    Raises:
        subprocess.CalledProcessError: If the workflow script execution fails
        FileNotFoundError: If the workflow script file is not found at the expected path
    Environment Variables Set:
        - DOMAIN_NAME: Domain name from config
        - TIME_START: Processing start time
        - TIME_END: Processing end time
        - PATH_SRC: Source path for forcing data
        - PATH_GEO: Path to geographical gridded data
        - PATH_DST: Destination path for converted data
        - PATH_LOG: Path for log files
        - PATH_TMP: Path for temporary files
    Note:
        The function executes the HMC IWRN converter workflow script located at
        '/app/shybox/workflow/dataset/convert/app_converter_workflow_hmc_iwrn.py'
        and uses configuration from 'app_converter_workflow_hmc_iwrn.json'.
    """
    workflow_path = '/app/shybox/workflow/dataset/convert/app_converter_workflow_hmc_iwrn.py'
    settings_path = os.path.join(workspace_path, 'settings', 'config','app_converter_workflow_hmc_iwrn.json')
    custom_env = {
        'DOMAIN_NAME' : config["general"]["domain"],
        'TIME_START' : time_start,
        'TIME_END' : time_end,
        'PATH_SRC' : os.path.join(config["path"]["hmc_data"], "data_forcing"),
        'PATH_GEO' : os.path.join(config["path"]["hmc_data"], "data_geo", "gridded"),
        'PATH_DST' : os.path.join(config["path"]["hmc_data"], "data_forcing", "gridded"),
        #'PATH_DST' : os.path.join(config["path"]["hmc_data"], "data_forcing", "converted"),
        'PATH_LOG' : os.path.join(config["path"]["hmc_data"], "logs"),
        'PATH_TMP' : os.path.join(config["path"]["hmc_data"], "tmp")
    }
    
    # get the current environment and add the custom variables
    env = os.environ.copy()
    env.update(custom_env)

    # execute the script as a subprocess
    command = [
        sys.executable, 
        workflow_path, 
        "-settings", 
        settings_path]

    try:
        print("Running the conversion tool")

        result = subprocess.run(
            command, 
            env=env, 
            capture_output=True, 
            text=True, 
            check=True
        )

        print("✅ Script executed successfully.")
        # if result.stderr:
        #     print("\n--- STDERR ---")
        #     print(result.stderr)
            

    except subprocess.CalledProcessError as e:
        # This block runs if the script fails (check=True)
        print(f"❌ Script failed with exit code {e.returncode}")      
    except FileNotFoundError:
        print(f"❌ Error: Script not found at '{workflow_path}'")

def run_hmc_model(workspace_path: str, config: Dict[str, Any], time_run: str, time_period: int) -> None:      
    """
    Execute the HMC (Hydrological Model Continuum) workflow using a subprocess.
    This function runs the HMC model by executing a Python workflow script with 
    specified configuration and environment variables. It sets up the necessary 
    paths and parameters required for the HMC model execution.
    Args:
        workspace_path (str): Path to the workspace directory containing settings 
                             and configuration files.
        config (Dict[str, Any]): Configuration dictionary containing model settings,
                                paths, and domain information. Expected structure:
                                - config["general"]["domain"]: Domain name
                                - config["path"]["hmc_data"]: Source data path
                                - config["path"]["hmc_output"]: Output directory path
                                - config["path"]: Base path for app and namelist directories
        time_run (str): Timestamp or identifier for the current model run.
        time_period (int): Time period parameter for the model execution.
    Returns:
        None: This function does not return a value but prints execution status.
    Raises:
        subprocess.CalledProcessError: If the HMC workflow script fails during execution.
        FileNotFoundError: If the workflow script is not found at the expected path.
    Environment Variables Set:
        - DOMAIN_NAME: Model domain name
        - TIME_RUN: Run timestamp
        - TIME_PERIOD: Model time period
        - PATH_SRC: Source data directory
        - PATH_DST: Output directory
        - PATH_APP: Application files directory
        - PATH_NAMELIST: Namelist files directory
        - PATH_LOG: Log files directory
        - PATH_TMP: Temporary files directory
    """
    workflow_path = '/app/shybox/workflow/runner/app_runner_workflow_hmc_base_main.py'
    settings_template_path = os.path.join(workspace_path, 'settings', 'config','app_runner_workflow_hmc_base.json')
    settings_override_path = os.path.join(config["path"]["hmc_data"], 'config','app_runner_workflow_hmc_iwrn.json')
    custom_env = {
        'DOMAIN_NAME' : config["general"]["domain"],
        'TIME_RUN' : time_run,
        'TIME_PERIOD' : str(time_period),
        'PATH_SRC' : config["path"]["hmc_data"],        
        'PATH_DST' : config["path"]["hmc_output"],
        'PATH_APP' : os.path.join('/home/continuumuser/workdir',config["general"]["domain"],"app"),
        'PATH_NAMELIST' : os.path.join(config["path"]["hmc_output"],"namelist"),
        'PATH_LOG' : os.path.join(config["path"]["hmc_output"], "logs"),
        'PATH_TMP' : os.path.join(config["path"]["hmc_output"], "tmp")
    }
    
    # get the current environment and add the custom variables
    env = os.environ.copy()
    env.update(custom_env)

    # apply the customization of the variables
    hmc_settings = {
        "namelist": {
            "fields": config["fields"]
        }
    }
    generate_hmc_settings(settings_template_path, hmc_settings, settings_override_path)

    # execute the script as a subprocess
    command = [
        sys.executable, 
        workflow_path, 
        "-settings", 
        settings_override_path]

    try:
        print("Running Continuum Hydrological Model...")

        result = subprocess.run(
            command, 
            env=env, 
            capture_output=True, 
            text=True, 
            check=True
        )

        print("✅ Script executed successfully.")
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
            

    except subprocess.CalledProcessError as e:
        # This block runs if the script fails (check=True)
        print(f"❌ Script failed with exit code {e.returncode}")      
    except FileNotFoundError:
        print(f"❌ Error: Script not found at '{workflow_path}'")


def generate_hmc_settings(input_file: str, override_data: Dict[str, Any], output_file: str) -> None:
    """
    Merge two JSON files where override values replace matching fields in input.
    
    Args:
        input_file: Path to the input JSON file
        override_data: Override data 
        output_file: Path to the output JSON file
    """
    try:
        # Read input JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Merge the data
        merged_data = deep_merge(input_data, override_data)
        
        # Write output JSON with nice formatting
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully merged JSON files!")
        print(f"  Input:    {input_file}")
        print(f"  Output:   {output_file}")
    
    except FileNotFoundError as e:
        print(f"✗ Error: File not found - {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge override dictionary into base dictionary.
    Values from override take precedence over base values.
    
    Args:
        base: The base dictionary (original data)
        override: The override dictionary (values to override with)
    
    Returns:
        Merged dictionary with overrides applied
    """
    result = base.copy()
    
    for key, override_value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(override_value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], override_value)
        else:
            # Override the value
            result[key] = override_value
    
    return result