"""Tests for channel configuration."""

import pytest

from ch10gen.utils.channel_config import (
    ChannelConfig,
    DATA_TYPE_COMPUTER_F0,
    DATA_TYPE_COMPUTER_F1,
    DATA_TYPE_TIME_F1,
    DATA_TYPE_MS1553_F1,
    PYCHAPTER10_CHANNELS
)


class TestChannelConfig:
    """Test channel configuration."""
    
    def test_default_config(self):
        """Test default channel configuration."""
        config = ChannelConfig()
        
        assert config.writer_backend == 'pychapter10'
        assert config.reader_compat == 'pychapter10_quirks'
        assert config.tmats_channel_id == 0x0200
        assert config.time_channel_id == 0x0100
        assert config.bus_a_channel_id == 0x0210
        assert config.bus_b_channel_id == 0x0220
        
    def test_data_type_pychapter10(self):
        """Test data type for PyChapter10 backend."""
        config = ChannelConfig(writer_backend='pychapter10')
        
        # PyChapter10 always returns COMPUTER_F0
        assert config.get_data_type('tmats') == DATA_TYPE_COMPUTER_F0
        assert config.get_data_type('time') == DATA_TYPE_COMPUTER_F0
        assert config.get_data_type('ms1553') == DATA_TYPE_COMPUTER_F0
        
    def test_data_type_irig106(self):
        """Test data type for IRIG106 backend."""
        config = ChannelConfig(writer_backend='irig106lib')
        
        # IRIG106 returns spec-compliant values
        assert config.get_data_type('tmats') == DATA_TYPE_COMPUTER_F1
        assert config.get_data_type('time') == DATA_TYPE_TIME_F1
        assert config.get_data_type('ms1553') == DATA_TYPE_MS1553_F1
        assert config.get_data_type('unknown') == DATA_TYPE_COMPUTER_F0  # Default
        
    def test_validate_channel_strict(self):
        """Test channel validation in strict mode."""
        config = ChannelConfig(reader_compat='strict')
        
        # Should match exact IDs
        assert config.validate_channel_id(0x0200, 'tmats') == True
        assert config.validate_channel_id(0x0100, 'time') == True
        assert config.validate_channel_id(0x0210, 'ms1553_a') == True
        assert config.validate_channel_id(0x0220, 'ms1553_b') == True
        
        # Wrong IDs should fail
        assert config.validate_channel_id(0x0000, 'tmats') == False
        assert config.validate_channel_id(0x0200, 'time') == False
        
    def test_validate_channel_quirks(self):
        """Test channel validation in quirks mode."""
        config = ChannelConfig(reader_compat='pychapter10_quirks')
        
        # In quirks mode, everything is accepted
        assert config.validate_channel_id(0x0000, 'tmats') == True
        assert config.validate_channel_id(0xFFFF, 'time') == True
        assert config.validate_channel_id(0x1234, 'ms1553_a') == True
        
    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            'writer_backend': 'irig106lib',
            'reader_compat': 'strict',
            'tmats_channel_id': 0x0000,
            'time_channel_id': 0x0001,
            'bus_a_channel_id': 0x0010,
            'bus_b_channel_id': 0x0020,
        }
        
        config = ChannelConfig.from_dict(data)
        
        assert config.writer_backend == 'irig106lib'
        assert config.reader_compat == 'strict'
        assert config.tmats_channel_id == 0x0000
        assert config.time_channel_id == 0x0001
        assert config.bus_a_channel_id == 0x0010
        assert config.bus_b_channel_id == 0x0020
        
    def test_from_dict_defaults(self):
        """Test from_dict with missing values uses defaults."""
        config = ChannelConfig.from_dict({})
        
        assert config.writer_backend == 'pychapter10'
        assert config.reader_compat == 'pychapter10_quirks'
        assert config.tmats_channel_id == 0x0200
        
    def test_custom_config(self):
        """Test custom channel configuration."""
        config = ChannelConfig(
            writer_backend='custom',
            tmats_channel_id=0x1000,
            time_channel_id=0x2000
        )
        
        assert config.writer_backend == 'custom'
        assert config.tmats_channel_id == 0x1000
        assert config.time_channel_id == 0x2000


class TestConstants:
    """Test module constants."""
    
    def test_data_type_constants(self):
        """Test data type constants match spec."""
        assert DATA_TYPE_COMPUTER_F0 == 0x00
        assert DATA_TYPE_COMPUTER_F1 == 0x01
        assert DATA_TYPE_TIME_F1 == 0x11
        assert DATA_TYPE_MS1553_F1 == 0x19
        
    def test_pychapter10_channels(self):
        """Test PyChapter10 channel patterns."""
        assert PYCHAPTER10_CHANNELS['tmats'] == 0x0000
        assert PYCHAPTER10_CHANNELS['time'] == 0x0000
        assert PYCHAPTER10_CHANNELS['bus_a'] == 0x1000
        assert PYCHAPTER10_CHANNELS['bus_b'] == 0x2000
