"""Simple tests for flight state."""

from ch10gen.flight_profile import FlightState, ISAAtmosphere


class TestFlightState:
    """Test FlightState dataclass."""
    
    def test_flight_state_creation(self):
        """Test creating a flight state."""
        state = FlightState(
            time=0.0,
            lat_deg=37.0,
            lon_deg=-122.0,
            altitude_ft=10000.0,
            heading_deg=90.0,
            roll_deg=0.0,
            pitch_deg=5.0,
            yaw_deg=90.0,
            ias_kt=250.0,
            tas_kt=280.0,
            mach=0.42,
            vs_fpm=500.0,
            p_deg_s=0.0,
            q_deg_s=0.0,
            r_deg_s=0.0,
            ax_g=0.0,
            ay_g=0.0,
            az_g=1.0,
            throttle_pct=75.0
        )
        
        assert state.time == 0.0
        assert state.altitude_ft == 10000.0
        assert state.ias_kt == 250.0
        assert state.throttle_pct == 75.0
        
    def test_flight_state_get_value(self):
        """Test getting values by key."""
        state = FlightState(
            time=10.0,
            lat_deg=40.0,
            lon_deg=-100.0,
            altitude_ft=25000.0,
            heading_deg=180.0,
            roll_deg=15.0,
            pitch_deg=2.0,
            yaw_deg=180.0,
            ias_kt=300.0,
            tas_kt=450.0,
            mach=0.75,
            vs_fpm=0.0,
            p_deg_s=5.0,
            q_deg_s=0.0,
            r_deg_s=2.0,
            ax_g=0.1,
            ay_g=0.5,
            az_g=1.2,
            throttle_pct=90.0
        )
        
        assert state.get_value('altitude_ft') == 25000.0
        assert state.get_value('ias_kt') == 300.0
        assert state.get_value('roll_deg') == 15.0
        assert state.get_value('non_existent') == 0.0  # Default


class TestISAAtmosphere:
    """Test ISA atmosphere model."""
    
    def test_temperature_at_sea_level(self):
        """Test temperature at sea level."""
        temp = ISAAtmosphere.temperature_k(0.0)
        
        # Should be ~288.15K (15°C)
        assert 287 < temp < 289
        
    def test_temperature_at_altitude(self):
        """Test temperature at various altitudes."""
        # At 10,000 ft
        temp_10k = ISAAtmosphere.temperature_k(10000.0)
        assert 265 < temp_10k < 270  # Should be colder
        
        # At 35,000 ft  
        temp_35k = ISAAtmosphere.temperature_k(35000.0)
        assert 215 < temp_35k < 220  # Much colder
        
    def test_pressure_at_sea_level(self):
        """Test pressure at sea level."""
        pressure = ISAAtmosphere.pressure_pa(0.0)
        
        # Should be ~101325 Pa
        assert 101000 < pressure < 102000
        
    def test_pressure_decreases_with_altitude(self):
        """Test that pressure decreases with altitude."""
        p0 = ISAAtmosphere.pressure_pa(0.0)
        p10k = ISAAtmosphere.pressure_pa(10000.0)
        p30k = ISAAtmosphere.pressure_pa(30000.0)
        
        assert p10k < p0
        assert p30k < p10k
        
    def test_density_at_sea_level(self):
        """Test density at sea level."""
        density = ISAAtmosphere.density_kg_m3(0.0)
        
        # Should be ~1.225 kg/m³
        assert 1.2 < density < 1.3
        
    def test_speed_of_sound(self):
        """Test speed of sound calculation."""
        # At sea level
        a0 = ISAAtmosphere.speed_of_sound_kt(0.0)
        assert 660 < a0 < 670  # ~661 knots
        
        # At 35,000 ft
        a35k = ISAAtmosphere.speed_of_sound_kt(35000.0)
        assert 570 < a35k < 580  # Slower in cold air
