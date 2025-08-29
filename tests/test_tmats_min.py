"""Tests for minimal TMATS builder."""

import pytest
from ch10gen.core.tmats import TMATSBuilder, create_default_tmats


class TestTMATSBuilder:
    """Test TMATS builder functionality."""
    
    def test_minimal_tmats(self):
        """Test building minimal valid TMATS."""
        builder = TMATSBuilder()
        
        # Should have default required fields
        tmats_str = builder.build()
        
        assert 'TMATS\\1.0;' in tmats_str
        assert 'G\\106:' in tmats_str  # IRIG 106 version
        assert 'G\\DSI\\N:' in tmats_str  # Data source ID
        assert 'G\\OD:' in tmats_str  # Origin date
        assert 'G\\DST:' in tmats_str  # Data source type
        assert 'G\\SHA:' in tmats_str  # Checksum placeholder
        
        # Should be non-empty
        assert len(tmats_str) > 50
    
    def test_channel_ids(self):
        """Test adding channel IDs."""
        builder = TMATSBuilder()
        
        # Add time channel
        builder.add_time_channel(channel_id=0x100, time_format='IRIG-B')
        
        # Add 1553 channel
        builder.add_1553_channel(channel_id=0x210, bus_name='BUS-A', 
                                description='Test 1553 Bus')
        
        tmats_str = builder.build()
        
        # Check for channel IDs (formatted as hex)
        assert '100' in tmats_str  # Time channel ID
        assert '210' in tmats_str  # 1553 channel ID
        assert 'TIM' in tmats_str  # Time channel type
        assert '1553IN' in tmats_str  # 1553 channel type
        assert 'BUS-A' in tmats_str
    
    def test_time_source(self):
        """Test time source configuration."""
        builder = TMATSBuilder()
        builder.add_time_channel(channel_id=0x100, time_format='GPS')
        
        tmats_str = builder.build()
        
        assert 'GPS' in tmats_str or 'TIMEFMT' in tmats_str
    
    def test_non_empty_required_fields(self):
        """Test that required fields are non-empty."""
        builder = TMATSBuilder()
        builder.set_program_name('TEST_PROGRAM')
        builder.set_test_name('TEST_MISSION')
        builder.set_recorder_info(manufacturer='TEST_MFG', model='TEST_MODEL', 
                                 serial='123456')
        
        tmats_str = builder.build()
        
        # Check program and test names
        assert 'TEST_PROGRAM' in tmats_str
        assert 'TEST_MISSION' in tmats_str
        
        # Check recorder info
        assert 'TEST_MFG' in tmats_str
        assert 'TEST_MODEL' in tmats_str
        assert '123456' in tmats_str
    
    def test_comments(self):
        """Test adding comments."""
        builder = TMATSBuilder()
        builder.add_comment('This is a test comment')
        builder.add_comment('Another comment with special chars: @#$%')
        
        tmats_str = builder.build()
        
        assert 'This is a test comment' in tmats_str
        assert 'Another comment' in tmats_str
        assert 'G\\COM-' in tmats_str  # Comment field prefix
    
    def test_icd_summary(self):
        """Test adding ICD summary information."""
        builder = TMATSBuilder()
        
        icd_info = {
            'messages': 'NAV_50HZ, GPS_10HZ, STATUS_1HZ',
            'total_rate_hz': 61.0,
            'bus': 'A'
        }
        
        builder.add_icd_summary(icd_info)
        
        tmats_str = builder.build()
        
        assert 'NAV_50HZ' in tmats_str
        assert '61' in tmats_str
        assert 'Primary Bus: A' in tmats_str
    
    def test_bus_attributes(self):
        """Test adding bus-specific attributes."""
        builder = TMATSBuilder()
        
        builder.add_bus_attributes(
            bus_name='BUS-A',
            channel_id=0x210,
            num_messages=1500,
            word_rate=25000.5
        )
        
        tmats_str = builder.build()
        
        assert 'BUS-A' in tmats_str
        assert '1500' in tmats_str  # Number of messages
        assert '25000' in tmats_str  # Word rate
    
    def test_format_compliance(self):
        """Test TMATS format compliance."""
        builder = TMATSBuilder()
        tmats_str = builder.build()
        
        # Should use CRLF line endings
        assert '\r\n' in tmats_str
        
        # Should start with version
        assert tmats_str.startswith('TMATS\\1.0;')
        
        # Each line should follow key:value; format
        lines = tmats_str.split('\r\n')
        for line in lines:
            if line and not line.startswith('TMATS'):
                assert ':' in line or line == ''
                if ':' in line:
                    assert line.endswith(';')
    
    def test_create_default_tmats(self):
        """Test the convenience function for creating default TMATS."""
        tmats_str = create_default_tmats(
            scenario_name='Test Scenario',
            icd_messages=['MSG1', 'MSG2', 'MSG3'],
            total_duration_s=600.5,
            total_messages=30000
        )
        
        assert 'Test Scenario' in tmats_str
        assert 'MSG1, MSG2, MSG3' in tmats_str
        assert '600' in tmats_str
        assert '30000' in tmats_str
        assert 'CH10-1553-FLIGHTGEN' in tmats_str
        
        # Should have standard structure
        assert 'TMATS\\1.0;' in tmats_str
        assert 'G\\106:' in tmats_str
        assert 'G\\SHA:' in tmats_str
    
    def test_channel_index_increment(self):
        """Test that channel indices increment properly."""
        builder = TMATSBuilder()
        
        # Add multiple channels
        builder.add_time_channel(channel_id=0x100)
        builder.add_1553_channel(channel_id=0x210, bus_name='BUS-A')
        builder.add_1553_channel(channel_id=0x211, bus_name='BUS-B')
        
        tmats_str = builder.build()
        
        # Should have R-1, R-2, R-3 channel indices
        assert 'R-1\\' in tmats_str
        assert 'R-2\\' in tmats_str
        assert 'R-3\\' in tmats_str
    
    def test_comment_index_increment(self):
        """Test that comment indices increment properly."""
        builder = TMATSBuilder()
        
        # Add multiple comments
        for i in range(5):
            builder.add_comment(f'Comment {i}')
        
        tmats_str = builder.build()
        
        # Should have G\COM-1 through G\COM-5
        for i in range(1, 6):
            assert f'G\\COM-{i}:Comment {i-1}' in tmats_str
