import json
from pathlib import Path
from typing import Any, Dict


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


def merge_json_files(input_file: str, override_file: str, output_file: str) -> None:
    """
    Merge two JSON files where override values replace matching fields in input.
    
    Args:
        input_file: Path to the input JSON file
        override_file: Path to the override JSON file
        output_file: Path to the output JSON file
    """
    try:
        # Read input JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Read override JSON
        with open(override_file, 'r', encoding='utf-8') as f:
            override_data = json.load(f)
        
        # Merge the data
        merged_data = deep_merge(input_data, override_data)
        
        # Write output JSON with nice formatting
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully merged JSON files!")
        print(f"  Input:    {input_file}")
        print(f"  Override: {override_file}")
        print(f"  Output:   {output_file}")
    
    except FileNotFoundError as e:
        print(f"✗ Error: File not found - {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


if __name__ == "__main__":
    # Define file paths
    script_dir = Path(__file__).parent
    input_file = script_dir / "input.json"
    override_file = script_dir / "override.json"
    output_file = script_dir / "experiment1.json"
    
    # Merge the files
    merge_json_files(str(input_file), str(override_file), str(output_file))
