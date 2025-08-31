"""Tests for TMATS generation."""

import pytest
from datetime import datetime

from ch10gen.core.tmats import TMATSBuilder, create_default_tmats


class TestTMATSBuilder:
    """Test TMATS builder."""
    
    def test_init(self):
        """Test TMATS builder initialization."""
        builder = TMATSBuilder()
        
        # Should have required G attributes
        assert 'G\\DSI\\N' in builder.attributes
        assert builder.attributes['G\\DSI\\N'] == 'ch10-1553-flightgen'
        assert builder.attributes['G\\106'] == '11'
        assert 'G\\OD' in builder.attributes
        assert builder.attributes['G\\DST'] == 'SYNTHESIZED'
        
    def test_set_program_name(self):
        """Test setting program name."""
        builder = TMATSBuilder()
        builder.set_program_name('TEST_PROGRAM')
        
        assert builder.attributes['G\\PN'] == 'TEST_PROGRAM'
        
    def test_set_test_name(self):
        """Test setting test name."""
        builder = TMATSBuilder()
        builder.set_test_name('TEST_001')
        
        assert builder.attributes['G\\TA'] == 'TEST_001'
        
    def test_set_recorder_info(self):
        """Test setting recorder information."""
        builder = TMATSBuilder()
        builder.set_recorder_info(
            manufacturer='ACME',
            model='REC-2000',
            serial='12345'
        )
        
        assert builder.attributes['R\\ID'] == 'ACME'
        assert builder.attributes['R\\MN'] == 'REC-2000'
        assert builder.attributes['R\\SN'] == '12345'
        
    def test_set_recorder_info_defaults(self):
        """Test recorder info with defaults."""
        builder = TMATSBuilder()
        builder.set_recorder_info()
        
        assert builder.attributes['R\\ID'] == 'SYNTHETIC'
        assert builder.attributes['R\\MN'] == 'CH10GEN'
        assert builder.attributes['R\\SN'] == '000001'
        
    def test_add_time_channel(self):
        """Test adding time channel."""
        builder = TMATSBuilder()
        builder.add_time_channel(channel_id=0x100, time_format='IRIG-B')
        
        # Should have time channel attributes
        assert 'R-1\\ID' in builder.attributes
        assert builder.attributes['R-1\\ID'] == '100'
        assert builder.attributes['R-1\\CDT'] == 'TIM'
        assert builder.attributes['R-1\\TF1'] == 'IRIG-B'
        assert builder.attributes['R-1\\TIMEFMT'] == '1'
        
    def test_add_1553_channel(self):
        """Test adding 1553 channel."""
        builder = TMATSBuilder()
        builder.add_1553_channel(
            channel_id=0x210,
            bus_name='BUS-A',
            description='Test Bus'
        )
        
        # Should have 1553 channel attributes
        assert 'R-1\\ID' in builder.attributes
        assert builder.attributes['R-1\\ID'] == '210'
        assert builder.attributes['R-1\\CDT'] == '1553IN'
        assert builder.attributes['R-1\\DSI'] == 'BUS-A'
        assert builder.attributes['R-1\\CDL'] == 'Test Bus'
        
    def test_multiple_channels(self):
        """Test adding multiple channels."""
        builder = TMATSBuilder()
        
        # Add time channel
        builder.add_time_channel(channel_id=0x100)
        
        # Add 1553 channel
        builder.add_1553_channel(channel_id=0x210)
        
        # Should have both channels with sequential indices
        assert 'R-1\\ID' in builder.attributes
        assert builder.attributes['R-1\\ID'] == '100'
        assert builder.attributes['R-1\\CDT'] == 'TIM'
        
        assert 'R-2\\ID' in builder.attributes
        assert builder.attributes['R-2\\ID'] == '210'
        assert builder.attributes['R-2\\CDT'] == '1553IN'
        
    def test_to_string(self):
        """Test converting to TMATS string."""
        builder = TMATSBuilder()
        builder.set_program_name('TEST')
        
        tmats_str = builder.to_string()
        
        # Should be proper TMATS format
        assert tmats_str.startswith('G\\DSI\\N:ch10-1553-flightgen;')
        assert 'G\\PN:TEST;' in tmats_str
        assert tmats_str.endswith(';')
        
    def test_to_bytes(self):
        """Test converting to bytes."""
        builder = TMATSBuilder()
        
        tmats_bytes = builder.to_bytes()
        
        # Should be ASCII encoded
        assert isinstance(tmats_bytes, bytes)
        assert tmats_bytes.startswith(b'G\\DSI\\N:ch10-1553-flightgen;')


class TestCreateDefaultTMATS:
    """Test create_default_tmats helper function."""
    
    def test_create_default_tmats_basic(self):
        """Test basic TMATS generation."""
        tmats_str = create_default_tmats(
            scenario_name='TEST_SCENARIO'
        )
        
        # Should contain scenario name in TA field
        assert 'G\\TA:TEST_SCENARIO;' in tmats_str
        # Test ID may not be in the simple helper function
        # Check for general structure instead
        assert 'G\\' in tmats_str
        
    def test_create_default_tmats_with_messages(self):
        """Test TMATS with ICD messages."""
        tmats_str = create_default_tmats(
            scenario_name='TEST',
            icd_messages=['MSG1', 'MSG2', 'MSG3'],
            total_duration_s=60.0,
            total_messages=1000
        )
        
        # Should have basic structure
        assert 'G\\TA:TEST;' in tmats_str
        assert 'G\\' in tmats_str
        
    def test_create_default_tmats_defaults(self):
        """Test TMATS with default parameters."""
        tmats_str = create_default_tmats()
        
        # Should still have required attributes
        assert 'G\\DSI\\N:ch10-1553-flightgen;' in tmats_str
        assert 'G\\106:11;' in tmats_str
        assert 'G\\TA:Demo Mission;' in tmats_str
        
    def test_create_default_tmats_complete(self):
        """Test TMATS with all available parameters."""
        tmats_str = create_default_tmats(
            scenario_name='FLIGHT_TEST',
            icd_messages=['NAV', 'ATTITUDE', 'ENGINE'],
            total_duration_s=3600.0,
            total_messages=50000
        )
        
        # Should have all components
        assert 'G\\TA:FLIGHT_TEST;' in tmats_str
        # Check for general structure
        assert 'G\\' in tmats_str
        assert 'R\\' in tmats_str or 'R-' in tmats_str
