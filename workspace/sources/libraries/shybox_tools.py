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
from datetime import datetime, timedelta


def _iter_month_chunks(start_dt: datetime, end_dt: datetime):
    """
    Generate (start_of_chunk, end_of_chunk) pairs such that:
    - The first chunk starts at start_dt
    - The last chunk ends at end_dt
    - Intermediate chunks cover one full month each
    """
    current_start = start_dt

    while current_start <= end_dt:

        # First day of next month
        if current_start.month == 12:
            next_month = current_start.replace(
                year=current_start.year + 1,
                month=1, day=1,
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            next_month = current_start.replace(
                month=current_start.month + 1,
                day=1,
                hour=0, minute=0, second=0, microsecond=0
            )

        # End of this chunk (just before next month), but not beyond global end_dt
        candidate_end = next_month - timedelta(seconds=1)
        current_end = min(candidate_end, end_dt)

        yield current_start, current_end

        current_start = next_month


def _run_hmc_converter(
    workspace_path: str,
    config: Dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
    header_msg: str = ""
) -> None:
    """
    Run the HMC converter workflow once for the given time window.
    """

    if header_msg:
        print(header_msg)

    workflow_path = '/app/shybox/workflow/dataset/convert/app_converter_workflow_hmc_iwrn.py'
    #workflow_path = '/home/continuumuser/workdir/sources/libraries/test_workflow.py'
    settings_path = os.path.join(
        workspace_path, 'settings', 'config', 'app_converter_workflow_hmc_ETH.json'
    )

    base_env = {
        'DOMAIN_NAME': config["general"]["domain"],
        'PATH_SRC': os.path.join(config["path"]["hmc_data"], "data_forcing"),
        'PATH_GEO': os.path.join(config["path"]["hmc_data"], "data_geo", "gridded"),
        'PATH_DST': os.path.join(config["path"]["hmc_data"], "data_forcing", "gridded"),
        # 'PATH_DST': os.path.join(config["path"]["hmc_data"], "data_forcing", "converted"),
        'PATH_LOG': os.path.join(config["path"]["hmc_data"], "logs"),
        'PATH_TMP': os.path.join(config["path"]["hmc_data"], "tmp"),
    }
    
    
    
    env = os.environ.copy()
    env.update(base_env)
    env.update({
        'TIME_START': start_dt.isoformat(sep=' '),
        'TIME_END': end_dt.isoformat(sep=' ')
    })

    command = [
        sys.executable,
        workflow_path,
        "-settings",
        settings_path
    ]

    try:
        print(f"   Running the conversion tool from {env['TIME_START']} to {env['TIME_END']}")

        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            check=False  # don't raise automatically, we handle it
        )

        if result.returncode == 0:
            print("   ✅ Script executed successfully.")
        elif "ValueError" in result.stderr:
            if start_dt.hour == start_dt.hour:
                print("   ✅ Script executed successfully.")  
        else:
            print(f"   ⚠️ Script finished with exit code {result.returncode}.")
            print("   --- STDOUT ---")
            print(result.stdout)
            print("   --- STDERR ---")
            print(result.stderr)

    except FileNotFoundError:
        print(f"   ❌ Error: Script not found at '{workflow_path}'")


def prepare_hmc_data(workspace_path: str, config: Dict[str, Any], time_start: str, time_end: str) -> None:
    """
    Prepare HMC data.
    - If the time range is within a single month, run the converter once (original behaviour).
    - If the time range spans multiple months, split into monthly chunks and run per month.
    """

    start_dt = datetime.fromisoformat(time_start)
    end_dt = datetime.fromisoformat(time_end)

    #if end_dt < start_dt:
    #    raise ValueError("time_end must be >= time_start")

    # Single-month case → keep the original single-run behaviour
    if start_dt.year == end_dt.year and start_dt.month == end_dt.month:
        _run_hmc_converter(
            workspace_path,
            config,
            start_dt,
            end_dt,
            header_msg=f"\n--> Working on {start_dt.month:02d}/{start_dt.year} (single chunk)"
        )
        return

    # Multi-month case → monthly loop
    for chunk_start, chunk_end in _iter_month_chunks(start_dt, end_dt):
        header = f"\n--> Working on {chunk_start.month:02d}/{chunk_start.year}"
        _run_hmc_converter(
            workspace_path,
            config,
            chunk_start,
            chunk_end,
            header_msg=header
        )

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
    # workflow_path = '/home/continuumuser/workdir/sources/libraries/app_runner_workflow_hmc_base_ETH.py'
    settings_template_path = os.path.join(
        workspace_path, 'settings', 'config', 'app_runner_workflow_hmc_base.json'
    )
    settings_override_path = os.path.join(config["path"]["hmc_data"], 'config','app_runner_workflow_hmc_iwrn.json')
    os.makedirs(os.path.join(config["path"]["hmc_data"], 'config') , exist_ok=True)
    custom_env = {
        'DOMAIN_NAME' : config["general"]["domain"],
        'TIME_RUN' : time_run,
        'TIME_PERIOD' : str(time_period),
        'PATH_SRC' : config["path"]["hmc_data"],        
        'PATH_DST' : config["path"]["hmc_output"],
        'PATH_APP' : os.path.join(config["path"]["hmc_output"],"app"),
        'PATH_NAMELIST' : os.path.join(config["path"]["hmc_output"],"namelist"),
        'PATH_LOG' : os.path.join(config["path"]["hmc_output"], "logs"),
        'PATH_TMP' : os.path.join(config["path"]["hmc_output"], "tmp")
    }
    
    # Ensure folders exist
    paths_to_check = [
    custom_env['PATH_SRC'],
    custom_env['PATH_DST'],
    custom_env['PATH_APP'],
    custom_env['PATH_LOG'],
    ]

    for p in paths_to_check:
        os.makedirs(p, exist_ok=True)
    
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
        print("   --- STDOUT ---")
        print(result.stdout)
        print("   --- STDERR ---")
        print(result.stderr)        
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
    
import os
import time
from datetime import datetime
from threading import Thread
from tqdm.auto import tqdm

def run_hmc_with_progress(workspace_path, config, output_path,
                          date_start_str, date_end_str):

    fmt = "%Y-%m-%d %H:%M"
    dt_start = datetime.strptime(date_start_str, fmt)
    dt_end   = datetime.strptime(date_end_str, fmt)

    # Compute hours to send to HMC
    hours = (dt_end - dt_start).total_seconds() / 3600

    # Expected timesteps
    dt_seconds = 3600
    expected_steps = int((dt_end - dt_start).total_seconds() / dt_seconds)

    hydro_file = os.path.join(output_path["model_results_time_series"],
                              "hmc.hydrograph.txt")

    # ---- Run model in separate thread ----
    def _run():
        run_hmc_model(workspace_path, config,
                                   date_start_str, hours)

    th = Thread(target=_run, daemon=True)
    th.start()

    # ---- Progress update loop ----
    def count_lines():
        if not os.path.isfile(hydro_file):
            return 0
        try:
            # VERY LIGHT: reads only metadata, not entire file
            with open(hydro_file, "r") as f:
                return sum(1 for _ in f)
        except:
            return 0

    def loop(update_fn):
        prev = 0
        while th.is_alive():
            n = count_lines()
            if n > prev:
                update_fn(n - prev)
                prev = n
            time.sleep(2)   # light polling

        # After completion, catch remaining lines
        n = count_lines()
        if n > prev:
            update_fn(n - prev)

    # tqdm or fallback
    if tqdm is not None:
        with tqdm(total=expected_steps, desc="HMC timestep progress") as pbar:
            loop(pbar.update)
    else:
        curr = 0
        def simple(delta):
            nonlocal curr
            curr += delta
            print(f"\r{curr}/{expected_steps} timesteps", end="")
        loop(simple)
        print()

    th.join()
    print("✅ Model finished.")


