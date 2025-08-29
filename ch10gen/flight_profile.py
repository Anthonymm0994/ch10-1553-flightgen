"""Flight profile generation for realistic flight test data."""
import math
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FlightState:
    """Current state of the aircraft."""
    timestamp: datetime
    altitude_ft: float
    airspeed_kts: float
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    g_force: float
    latitude_deg: float
    longitude_deg: float
    
    def __repr__(self):
        return f"FlightState(alt={self.altitude_ft:.0f}ft, speed={self.airspeed_kts:.0f}kts, hdg={self.heading_deg:.0f}°)"


class FlightProfile:
    """Generate realistic flight profiles for test data."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize flight profile generator.
        
        Args:
            seed: Random seed for reproducible profiles
        """
        if seed is not None:
            random.seed(seed)
        
        # Default flight parameters
        self.cruise_altitude_ft = 25000
        self.cruise_speed_kts = 450
        self.climb_rate_fpm = 2000
        self.descent_rate_fpm = -1500
        self.turn_rate_deg_per_sec = 3.0
        self.max_g_force = 2.5
        
        # Flight phases
        self.phases = ['takeoff', 'climb', 'cruise', 'descent', 'landing']
        self.current_phase = 0
        self.phase_start_time = 0.0
        
        # Waypoint-based navigation
        self.waypoints = []
    
    def generate_flight_plan(self, duration_s: float) -> Dict[str, Any]:
        """Generate a complete flight plan.
        
        Args:
            duration_s: Total flight duration in seconds
            
        Returns:
            Flight plan dictionary
        """
        # Simple flight plan: takeoff -> climb -> cruise -> descent -> landing
        takeoff_duration = 60  # 1 minute
        climb_duration = (self.cruise_altitude_ft / self.climb_rate_fpm) * 60  # Calculate from climb rate
        cruise_duration = duration_s - takeoff_duration - climb_duration - 120  # Leave time for descent/landing
        descent_duration = (self.cruise_altitude_ft / abs(self.descent_rate_fpm)) * 60
        landing_duration = 60
        
        # Ensure we don't exceed duration
        total_planned = takeoff_duration + climb_duration + cruise_duration + descent_duration + landing_duration
        if total_planned > duration_s:
            # Scale down proportionally
            scale_factor = duration_s / total_planned
            takeoff_duration *= scale_factor
            climb_duration *= scale_factor
            cruise_duration *= scale_factor
            descent_duration *= scale_factor
            landing_duration *= scale_factor
        
        return {
            'takeoff': {'duration_s': takeoff_duration, 'start_time_s': 0},
            'climb': {'duration_s': climb_duration, 'start_time_s': takeoff_duration},
            'cruise': {'duration_s': cruise_duration, 'start_time_s': takeoff_duration + climb_duration},
            'descent': {'duration_s': descent_duration, 'start_time_s': takeoff_duration + climb_duration + cruise_duration},
            'landing': {'duration_s': landing_duration, 'start_time_s': takeoff_duration + climb_duration + cruise_duration + descent_duration}
        }
    
    def get_flight_state(self, time_s: float, duration_s: float) -> FlightState:
        """Get flight state at a specific time.
        
        Args:
            time_s: Time since start in seconds
            duration_s: Total flight duration in seconds
            
        Returns:
            FlightState object
        """
        flight_plan = self.generate_flight_plan(duration_s)
        
        # Determine current phase
        current_phase = 'cruise'  # Default
        for phase, details in flight_plan.items():
            if time_s >= details['start_time_s'] and time_s < details['start_time_s'] + details['duration_s']:
                current_phase = phase
                break
        
        # Generate state based on phase
        if current_phase == 'takeoff':
            altitude = (time_s / flight_plan['takeoff']['duration_s']) * 1000  # Climb to 1000ft
            airspeed = 120 + (time_s / flight_plan['takeoff']['duration_s']) * 80  # 120-200 kts
            heading = 90 + random.uniform(-5, 5)  # Runway heading with slight variation
            pitch = 10 + random.uniform(-2, 2)  # Nose up
            roll = random.uniform(-1, 1)  # Slight roll
            g_force = 1.0 + random.uniform(-0.1, 0.1)
            
        elif current_phase == 'climb':
            phase_time = time_s - flight_plan['climb']['start_time_s']
            phase_duration = flight_plan['climb']['duration_s']
            progress = phase_time / phase_duration
            
            altitude = 1000 + progress * (self.cruise_altitude_ft - 1000)
            airspeed = 200 + progress * (self.cruise_speed_kts - 200)
            heading = 90 + random.uniform(-10, 10)
            pitch = 8 + random.uniform(-2, 2)
            roll = random.uniform(-3, 3)
            g_force = 1.0 + random.uniform(-0.2, 0.2)
            
        elif current_phase == 'cruise':
            altitude = self.cruise_altitude_ft + random.uniform(-500, 500)
            airspeed = self.cruise_speed_kts + random.uniform(-20, 20)
            heading = 90 + random.uniform(-15, 15)
            pitch = random.uniform(-1, 1)
            roll = random.uniform(-5, 5)
            g_force = 1.0 + random.uniform(-0.1, 0.1)
            
        elif current_phase == 'descent':
            phase_time = time_s - flight_plan['descent']['start_time_s']
            phase_duration = flight_plan['descent']['duration_s']
            progress = phase_time / phase_duration
            
            altitude = self.cruise_altitude_ft - progress * (self.cruise_altitude_ft - 1000)
            airspeed = self.cruise_speed_kts - progress * (self.cruise_speed_kts - 200)
            heading = 90 + random.uniform(-10, 10)
            pitch = -5 + random.uniform(-2, 2)
            roll = random.uniform(-3, 3)
            g_force = 1.0 + random.uniform(-0.2, 0.2)
            
        else:  # landing
            altitude = 1000 - (time_s - flight_plan['landing']['start_time_s']) / flight_plan['landing']['duration_s'] * 1000
            airspeed = 200 - (time_s - flight_plan['landing']['start_time_s']) / flight_plan['landing']['duration_s'] * 80
            heading = 90 + random.uniform(-5, 5)
            pitch = -2 + random.uniform(-1, 1)
            roll = random.uniform(-1, 1)
            g_force = 1.0 + random.uniform(-0.1, 0.1)
        
        # Add some realistic noise
        altitude += random.uniform(-100, 100)
        airspeed += random.uniform(-5, 5)
        heading += random.uniform(-1, 1)
        pitch += random.uniform(-0.5, 0.5)
        roll += random.uniform(-0.5, 0.5)
        g_force += random.uniform(-0.05, 0.05)
        
        # Normalize values
        heading = heading % 360
        pitch = max(-20, min(20, pitch))
        roll = max(-45, min(45, roll))
        g_force = max(0.5, min(self.max_g_force, g_force))
        
        # Generate position (simple circular pattern)
        radius_nm = 50  # 50 nautical mile radius
        angle_rad = math.radians(heading)
        latitude = 40.0 + (radius_nm / 60.0) * math.cos(angle_rad)  # Convert nm to degrees
        longitude = -74.0 + (radius_nm / 60.0) * math.sin(angle_rad) / math.cos(math.radians(latitude))
        
        # Create timestamp
        timestamp = datetime.utcnow() + timedelta(seconds=time_s)
        
        return FlightState(
            timestamp=timestamp,
            altitude_ft=altitude,
            airspeed_kts=airspeed,
            heading_deg=heading,
            pitch_deg=pitch,
            roll_deg=roll,
            g_force=g_force,
            latitude_deg=latitude,
            longitude_deg=longitude
        )
    
    def get_flight_data(self, time_s: float, duration_s: float) -> Dict[str, float]:
        """Get flight data as a dictionary for easy access.
        
        Args:
            time_s: Time since start in seconds
            duration_s: Total flight duration in seconds
            
        Returns:
            Dictionary of flight parameters
        """
        state = self.get_flight_state(time_s, duration_s)
        
        return {
            'altitude_ft': state.altitude_ft,
            'airspeed_kts': state.airspeed_kts,
            'heading_deg': state.heading_deg,
            'pitch_deg': state.pitch_deg,
            'roll_deg': state.roll_deg,
            'g_force': state.g_force,
            'latitude_deg': state.latitude_deg,
            'longitude_deg': state.longitude_deg
        }
    
    def add_waypoint(self, time_s: float, altitude_ft: float, airspeed_kts: float, 
                     heading_deg: float, latitude_deg: float, longitude_deg: float):
        """Add a waypoint to the flight plan.
        
        Args:
            time_s: Time since start in seconds
            altitude_ft: Target altitude in feet
            airspeed_kts: Target airspeed in knots
            heading_deg: Target heading in degrees
            latitude_deg: Target latitude
            longitude_deg: Target longitude
        """
        self.waypoints.append({
            'time_s': time_s,
            'altitude_ft': altitude_ft,
            'airspeed_kts': airspeed_kts,
            'heading_deg': heading_deg,
            'latitude_deg': latitude_deg,
            'longitude_deg': longitude_deg
        })
        
        # Sort waypoints by time
        self.waypoints.sort(key=lambda w: w['time_s'])
    
    def get_state_at_time(self, time_s: float) -> Optional[FlightState]:
        """Get flight state at a specific time using waypoints.
        
        Args:
            time_s: Time since start in seconds
            
        Returns:
            FlightState object or None if no waypoints
        """
        if not self.waypoints:
            return None
        
        # Find the appropriate waypoint
        if time_s <= self.waypoints[0]['time_s']:
            # Before first waypoint
            wp = self.waypoints[0]
        elif time_s >= self.waypoints[-1]['time_s']:
            # After last waypoint
            wp = self.waypoints[-1]
        else:
            # Between waypoints - find the one before current time
            for i, wp in enumerate(self.waypoints):
                if wp['time_s'] > time_s:
                    if i > 0:
                        wp = self.waypoints[i-1]
                    break
        
        # Create timestamp
        timestamp = datetime.utcnow() + timedelta(seconds=time_s)
        
        # Return FlightState object
        return FlightState(
            timestamp=timestamp,
            altitude_ft=wp['altitude_ft'],
            airspeed_kts=wp['airspeed_kts'],
            heading_deg=wp['heading_deg'],
            pitch_deg=0.0,  # Default values
            roll_deg=0.0,
            g_force=1.0,
            latitude_deg=wp['latitude_deg'],
            longitude_deg=wp['longitude_deg']
        )


class FlightProfileGenerator:
    """Alternative interface for generating flight profiles."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator."""
        self.profile = FlightProfile(seed)
    
    def get_state(self, time_s: float, duration_s: float) -> FlightState:
        """Get flight state at time."""
        return self.profile.get_flight_state(time_s, duration_s)
    
    def get_data(self, time_s: float, duration_s: float) -> Dict[str, float]:
        """Get flight data at time."""
        return self.profile.get_flight_data(time_s, duration_s)
    
    def get_icd_data(self, time_s: float, duration_s: float) -> Dict[str, Any]:
        """Get flight data in the format expected by ICD files.
        
        This method maps internal field names to the names expected by ICD files.
        """
        state = self.profile.get_flight_state(time_s, duration_s)
        
        return {
            'flight': {
                'altitude_ft': state.altitude_ft,
                'airspeed_kt': state.airspeed_kts,  # Map kts -> kt
                'heading_deg': state.heading_deg,
                'latitude_deg': state.latitude_deg,
                'longitude_deg': state.longitude_deg
            },
            'derived': {
                'status': 1  # Default status
            }
        }

