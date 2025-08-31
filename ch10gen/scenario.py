"""
Scenario loading and management for CH10 generation.
Handles flight profiles and test scenarios.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .flight_profile import FlightProfile

def load_scenario(scenario_file: Path) -> Dict[str, Any]:
    """
    Load a scenario from a YAML file.
    
    Args:
        scenario_file: Path to the scenario YAML file
        
    Returns:
        Dictionary containing scenario configuration
        
    Raises:
        FileNotFoundError: If scenario file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if not scenario_file.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_file}. Check the file path and ensure the file exists.")
    
    with open(scenario_file, 'r') as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError("Scenario file is empty or contains no valid YAML data. Check the file content.")
    
    # Handle both nested and flat scenario structures
    if 'scenario' in data:
        scenario = data['scenario']
    else:
        scenario = data
    
    # Ensure required fields
    if 'name' not in scenario:
        scenario['name'] = 'Unnamed Scenario'
    
    if 'duration_s' not in scenario:
        if 'duration' in scenario:
            scenario['duration_s'] = scenario['duration']
        else:
            scenario['duration_s'] = 60.0  # Default 1 minute
    
    return data

def create_flight_profile(scenario_data: Dict[str, Any]) -> FlightProfile:
    """
    Create a FlightProfile from scenario data.
    
    Args:
        scenario_data: Scenario configuration dictionary
        
    Returns:
        Configured FlightProfile instance
    """
    # Extract scenario metadata
    if 'scenario' in scenario_data:
        scenario = scenario_data['scenario']
    else:
        scenario = scenario_data
    
    duration = scenario.get('duration_s', 60.0)
    seed = scenario.get('seed', None)
    
    # Extract flight profile configuration
    if 'flight_profile' in scenario_data:
        profile_config = scenario_data['flight_profile']
    else:
        # Create default profile
        profile_config = {
            'segments': [{
                'type': 'level',
                'duration_s': duration,
                'altitude_ft': 10000,
                'airspeed_kts': 250,
                'heading_deg': 90
            }]
        }
    
    # Create and configure the flight profile
    profile = FlightProfile(duration_s=duration, seed=seed)
    
    # Load segments if provided
    if 'segments' in profile_config:
        for segment in profile_config['segments']:
            profile.add_segment(segment)
    
    return profile

def validate_scenario(scenario_file: Path) -> bool:
    """
    Validate a scenario file.
    
    Args:
        scenario_file: Path to scenario YAML file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        data = load_scenario(scenario_file)
        
        # Check required fields
        if 'scenario' in data:
            scenario = data['scenario']
        else:
            scenario = data
        
        if 'duration_s' not in scenario and 'duration' not in scenario:
            print(f"Warning: No duration specified in scenario. Using default 60 seconds.")
        
        # Try to create a flight profile to validate structure
        profile = create_flight_profile(data)
        
        return True
        
    except Exception as e:
        print(f"Scenario validation failed: {e}")
        return False

__all__ = ['load_scenario', 'create_flight_profile', 'validate_scenario']
