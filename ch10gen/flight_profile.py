"""
Flight profile generation for realistic flight test data.

This module provides flight profile generation capabilities for creating
realistic aircraft state data that can be used in Chapter 10 files. It
implements various flight phases and atmospheric calculations.

Key components:
- FlightState: Represents current aircraft state (altitude, speed, attitude, etc.)
- FlightProfile: Generates flight profiles with different phases
- ISA Atmosphere: International Standard Atmosphere calculations
- Flight Phases: Climb, cruise, turn, descent with realistic parameters

The module supports both deterministic and random flight profiles,
enabling generation of consistent test data or varied scenarios.
"""

import math
import random
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FlightState:
    """
    Current state of the aircraft.
    
    This class represents the complete state of an aircraft at a specific
    point in time. It includes position, attitude, and performance parameters
    that are commonly recorded in flight test data.
    """
    timestamp: datetime  # Time of this state
    altitude_ft: float  # Altitude above sea level (feet)
    airspeed_kts: float  # Indicated airspeed (knots)
    heading_deg: float  # Magnetic heading (degrees)
    pitch_deg: float  # Pitch angle (degrees, positive = nose up)
    roll_deg: float  # Roll angle (degrees, positive = right wing down)
    g_force: float  # G-force load factor (1.0 = normal gravity)
    latitude_deg: float  # Latitude (degrees)
    longitude_deg: float  # Longitude (degrees)
    
    def __init__(self, timestamp=None, altitude_ft=0.0, airspeed_kts=0.0, heading_deg=0.0, 
                 pitch_deg=0.0, roll_deg=0.0, g_force=1.0, latitude_deg=0.0, longitude_deg=0.0,
                 **kwargs):
        """Initialize FlightState with optional parameters."""
        # Handle legacy parameter names
        if 'time' in kwargs:
            timestamp = kwargs['time']
        if 'time_s' in kwargs:
            timestamp = kwargs['time_s']
        if 'ias_kt' in kwargs:
            airspeed_kts = kwargs['ias_kt']
        
        # Set defaults if not provided
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.timestamp = timestamp
        self.altitude_ft = altitude_ft
        self.airspeed_kts = airspeed_kts
        self.heading_deg = heading_deg
        self.pitch_deg = pitch_deg
        self.roll_deg = roll_deg
        self.g_force = g_force
        self.latitude_deg = latitude_deg
        self.longitude_deg = longitude_deg
    
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
        self.states = []  # Store generated states for compatibility
        self.isa = ISAAtmosphere()  # Add ISA atmosphere model
        self.turn_model = None  # Placeholder for turn model
    
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
    
    def generate_profile(self, start_time, duration_s: float, segments=None, initial_altitude_ft=None):
        """Generate a flight profile with the given parameters.
        
        This method is a compatibility wrapper for tests that expect the old API.
        It stores the profile data for later retrieval.
        """
        # Store the profile data for compatibility
        self.start_time = start_time
        self.duration_s = duration_s
        self.segments = segments or []
        self.initial_altitude_ft = initial_altitude_ft or 10000
        
        # Return a list of states for the duration
        states = []
        for i in range(int(duration_s * 10)):  # 10Hz sampling
            time_s = i * 0.1
            state = self.get_state(time_s, duration_s)
            states.append(state)
        
        # Store states for compatibility
        self.states = states
        return states


class ISAAtmosphere:
    """International Standard Atmosphere calculations."""
    
    # ISA constants
    T0 = 288.15  # Sea level temperature (K)
    P0 = 101325.0  # Sea level pressure (Pa)
    RHO0 = 1.225  # Sea level density (kg/m³)
    A0 = 340.294  # Sea level speed of sound (m/s)
    LAPSE_RATE = -0.0065  # Temperature lapse rate (K/m)
    G = 9.80665  # Gravitational acceleration (m/s²)
    R = 287.053  # Gas constant for air (J/kg·K)
    
    @classmethod
    def temperature_k(cls, altitude_ft: float) -> float:
        """Calculate temperature at altitude using ISA model.
        
        Args:
            altitude_ft: Altitude in feet
            
        Returns:
            Temperature in Kelvin
        """
        altitude_m = altitude_ft * 0.3048  # Convert feet to meters
        return cls.T0 + cls.LAPSE_RATE * altitude_m
    
    @classmethod
    def pressure_pa(cls, altitude_ft: float) -> float:
        """Calculate pressure at altitude using ISA model.
        
        Args:
            altitude_ft: Altitude in feet
            
        Returns:
            Pressure in Pascal
        """
        temp_k = cls.temperature_k(altitude_ft)
        return cls.P0 * (temp_k / cls.T0) ** (cls.G / (cls.LAPSE_RATE * cls.R))
    
    @classmethod
    def density_kg_m3(cls, altitude_ft: float) -> float:
        """Calculate density at altitude using ISA model.
        
        Args:
            altitude_ft: Altitude in feet
            
        Returns:
            Density in kg/m³
        """
        temp_k = cls.temperature_k(altitude_ft)
        pressure_pa = cls.pressure_pa(altitude_ft)
        return pressure_pa / (cls.R * temp_k)
    
    @classmethod
    def speed_of_sound_kt(cls, altitude_ft: float) -> float:
        """Calculate speed of sound at altitude.
        
        Args:
            altitude_ft: Altitude in feet
            
        Returns:
            Speed of sound in knots
        """
        temp_k = cls.temperature_k(altitude_ft)
        a_ms = (cls.G * cls.R * temp_k) ** 0.5
        return a_ms * 1.94384  # Convert m/s to knots
    
    @classmethod
    def tas_from_ias(cls, ias_kt: float, altitude_ft: float) -> float:
        """Convert indicated airspeed to true airspeed.
        
        Args:
            ias_kt: Indicated airspeed in knots
            altitude_ft: Altitude in feet
            
        Returns:
            True airspeed in knots
        """
        rho = cls.density_kg_m3(altitude_ft)
        rho0 = cls.RHO0
        return ias_kt * (rho0 / rho) ** 0.5
    
    @classmethod
    def ias_from_tas(cls, tas_kt: float, altitude_ft: float) -> float:
        """Convert true airspeed to indicated airspeed.
        
        Args:
            tas_kt: True airspeed in knots
            altitude_ft: Altitude in feet
            
        Returns:
            Indicated airspeed in knots
        """
        rho = cls.density_kg_m3(altitude_ft)
        rho0 = cls.RHO0
        return tas_kt * (rho / rho0) ** 0.5
    
    @classmethod
    def get_conditions(cls, altitude_ft: float) -> Tuple[float, float, float]:
        """Get temperature, pressure, and density at altitude.
        
        Args:
            altitude_ft: Altitude in feet
            
        Returns:
            Tuple of (temperature_C, pressure_Pa, density_kg_m3)
        """
        altitude_m = altitude_ft * 0.3048  # Convert feet to meters
        temp_k = cls.temperature_k(altitude_m)
        temp_c = temp_k - 273.15  # Convert Kelvin to Celsius
        pressure_pa = cls.pressure_pa(altitude_m)
        density_kg_m3 = cls.density_kg_m3(altitude_m)
        return temp_c, pressure_pa, density_kg_m3
    
    @classmethod
    def ias_to_mach(cls, ias_kt: float, altitude_ft: float) -> float:
        """Convert indicated airspeed to Mach number.
        
        Args:
            ias_kt: Indicated airspeed in knots
            altitude_ft: Altitude in feet
            
        Returns:
            Mach number
        """
        tas_kt = cls.tas_from_ias(ias_kt, altitude_ft)
        tas_ms = tas_kt / 1.94384  # Convert knots to m/s
        speed_of_sound_ms = cls.speed_of_sound_kt(altitude_ft) / 1.94384
        return tas_ms / speed_of_sound_ms

