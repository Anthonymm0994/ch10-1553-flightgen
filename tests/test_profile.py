"""Tests for flight profile generation."""

import pytest
from datetime import datetime, timezone
from ch10gen.flight_profile import FlightProfileGenerator, ISAAtmosphere, FlightState


class TestISAAtmosphere:
    """Test ISA atmosphere model."""
    
    def test_sea_level_conditions(self):
        """Test standard sea level conditions."""
        temp_k = ISAAtmosphere.temperature_k(0)
        assert abs(temp_k - 288.15) < 0.1
        
        pressure_pa = ISAAtmosphere.pressure_pa(0)
        assert abs(pressure_pa - 101325) < 1
        
        density = ISAAtmosphere.density_kg_m3(0)
        assert abs(density - 1.225) < 0.01
    
    def test_altitude_10000ft(self):
        """Test conditions at 10,000 ft."""
        temp_k = ISAAtmosphere.temperature_k(10000)
        assert temp_k < 288.15  # Should be colder
        
        pressure_pa = ISAAtmosphere.pressure_pa(10000)
        assert pressure_pa < 101325  # Should be lower pressure
        
        density = ISAAtmosphere.density_kg_m3(10000)
        assert density < 1.225  # Should be less dense
    
    def test_tas_ias_conversion(self):
        """Test TAS/IAS conversions."""
        # At sea level, TAS should equal IAS
        tas = ISAAtmosphere.tas_from_ias(250, 0)
        assert abs(tas - 250) < 1
        
        # At altitude, TAS should be greater than IAS
        tas = ISAAtmosphere.tas_from_ias(250, 10000)
        assert tas > 250
        
        # Round trip conversion
        ias = ISAAtmosphere.ias_from_tas(tas, 10000)
        assert abs(ias - 250) < 1
    
    def test_speed_of_sound(self):
        """Test speed of sound calculation."""
        # Sea level
        a_kt = ISAAtmosphere.speed_of_sound_kt(0)
        assert abs(a_kt - 661.5) < 10  # Approximately 661.5 knots at sea level
        
        # Higher altitude should have lower speed of sound (colder)
        a_high = ISAAtmosphere.speed_of_sound_kt(35000)
        assert a_high < a_kt


class TestFlightProfileGenerator:
    """Test flight profile generation."""
    
    def test_initialization(self):
        """Test generator initialization."""
        gen = FlightProfileGenerator(seed=42)
        assert gen.sample_rate_hz == 100
        assert len(gen.states) == 0
    
    def test_deterministic_with_seed(self):
        """Test that same seed produces same results."""
        gen1 = FlightProfileGenerator(seed=42)
        gen2 = FlightProfileGenerator(seed=42)
        
        segments = [
            {'type': 'cruise', 'ias_kt': 250, 'duration_s': 10}
        ]
        
        states1 = gen1.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=10,
            segments=segments
        )
        
        states2 = gen2.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=10,
            segments=segments
        )
        
        # Should produce identical results
        assert len(states1) == len(states2)
        for s1, s2 in zip(states1, states2):
            assert abs(s1.altitude_ft - s2.altitude_ft) < 0.01
            assert abs(s1.ias_kt - s2.ias_kt) < 0.01
    
    def test_climb_segment(self):
        """Test climb segment generation."""
        gen = FlightProfileGenerator(seed=42)
        
        segments = [
            {
                'type': 'climb',
                'to_altitude_ft': 10000,
                'ias_kt': 250,
                'vs_fpm': 1500,
                'duration_s': 60
            }
        ]
        
        states = gen.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=60,
            segments=segments,
            initial_altitude_ft=2000
        )
        
        assert len(states) > 0
        
        # Check altitude increases
        assert states[-1].altitude_ft > states[0].altitude_ft
        
        # Check IAS is maintained
        avg_ias = sum(s.ias_kt for s in states) / len(states)
        assert abs(avg_ias - 250) < 5
    
    def test_turn_segment(self):
        """Test turn segment generation."""
        gen = FlightProfileGenerator(seed=42)
        
        segments = [
            {
                'type': 'turn',
                'heading_change_deg': 90,
                'bank_deg': 25,
                'ias_kt': 250,
                'duration_s': 30
            }
        ]
        
        states = gen.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=30,
            segments=segments,
            initial_heading_deg=0
        )
        
        assert len(states) > 0
        
        # Check heading changes
        heading_change = states[-1].heading_deg - states[0].heading_deg
        if heading_change < 0:
            heading_change += 360
        assert abs(heading_change) > 45  # Should have made a significant turn
        
        # Check bank angle during turn
        max_bank = max(abs(s.roll_deg) for s in states)
        assert max_bank > 20  # Should have significant bank
    
    def test_descent_segment(self):
        """Test descent segment generation."""
        gen = FlightProfileGenerator(seed=42)
        
        segments = [
            {
                'type': 'descent',
                'to_altitude_ft': 2000,
                'ias_kt': 250,
                'vs_fpm': -1200,
                'duration_s': 60
            }
        ]
        
        states = gen.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=60,
            segments=segments,
            initial_altitude_ft=10000
        )
        
        assert len(states) > 0
        
        # Check altitude decreases
        assert states[-1].altitude_ft < states[0].altitude_ft
        
        # Check vertical speed is negative
        avg_vs = sum(s.vs_fpm for s in states) / len(states)
        assert avg_vs < 0
    
    def test_cruise_segment(self):
        """Test cruise segment generation."""
        gen = FlightProfileGenerator(seed=42)
        
        segments = [
            {
                'type': 'cruise',
                'ias_kt': 320,
                'hold_s': 30
            }
        ]
        
        states = gen.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=30,
            segments=segments,
            initial_altitude_ft=35000
        )
        
        assert len(states) > 0
        
        # Check altitude remains relatively stable
        altitudes = [s.altitude_ft for s in states]
        alt_variation = max(altitudes) - min(altitudes)
        assert alt_variation < 100  # Should stay within 100 ft
        
        # Check IAS is maintained
        avg_ias = sum(s.ias_kt for s in states) / len(states)
        assert abs(avg_ias - 320) < 5
    
    def test_get_state_at_time(self):
        """Test state interpolation."""
        gen = FlightProfileGenerator(seed=42)
        
        segments = [
            {'type': 'cruise', 'ias_kt': 250, 'duration_s': 10}
        ]
        
        states = gen.generate_profile(
            start_time=datetime.now(timezone.utc),
            duration_s=10,
            segments=segments
        )
        
        # Test exact time
        state = gen.get_state_at_time(0)
        assert state is not None
        assert state.time == 0
        
        # Test interpolation
        state = gen.get_state_at_time(0.5)
        assert state is not None
        assert abs(state.time - 0.5) < 0.01
        
        # Test beyond range
        state = gen.get_state_at_time(100)
        assert state is not None
        assert state.time == states[-1].time
    
    def test_flight_state_get_value(self):
        """Test FlightState value retrieval."""
        state = FlightState(
            time=0,
            lat_deg=37.0,
            lon_deg=-122.0,
            altitude_ft=10000,
            heading_deg=90,
            roll_deg=0,
            pitch_deg=2,
            yaw_deg=90,
            ias_kt=250,
            tas_kt=300,
            mach=0.45,
            vs_fpm=0,
            p_deg_s=0,
            q_deg_s=0,
            r_deg_s=0,
            ax_g=0,
            ay_g=0,
            az_g=1,
            throttle_pct=65
        )
        
        assert state.get_value('altitude_ft') == 10000
        assert state.get_value('ias_kt') == 250
        assert state.get_value('nonexistent') == 0.0
