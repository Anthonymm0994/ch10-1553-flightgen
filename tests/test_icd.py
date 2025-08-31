"""Tests for ICD parser and validators."""

import pytest
import yaml
import tempfile
from pathlib import Path
from ch10gen.icd import (
    WordDefinition, MessageDefinition, ICDDefinition,
    validate_icd_file, load_icd
)


class TestWordDefinition:
    """Test word definition validation."""
    
    def test_valid_word(self):
        """Test valid word definition."""
        word = WordDefinition(
            name='altitude',
            src='flight.altitude_ft',
            encode='bnr16',
            scale=1.0,
            offset=0.0,
            min_value=-1000,
            max_value=60000
        )
        
        errors = word.validate()
        assert len(errors) == 0
    
    def test_missing_source_and_const(self):
        """Test word must have either src or const."""
        word = WordDefinition(
            name='test',
            encode='u16'
        )
        
        errors = word.validate()
        assert len(errors) == 1
        assert "must have either 'src' or 'const'" in errors[0]
    
    def test_const_word(self):
        """Test constant value word."""
        word = WordDefinition(
            name='reserved',
            encode='u16',
            const=0
        )
        
        errors = word.validate()
        assert len(errors) == 0
    
    def test_invalid_encoding(self):
        """Test invalid encoding type."""
        word = WordDefinition(
            name='test',
            src='flight.test',
            encode='invalid_type'
        )
        
        errors = word.validate()
        assert len(errors) == 1
        assert 'invalid encoding' in errors[0].lower()
    
    def test_float32_split_validation(self):
        """Test float32_split specific validation."""
        # Missing word_order
        word = WordDefinition(
            name='test',
            src='flight.test',
            encode='float32_split'
        )
        
        errors = word.validate()
        assert len(errors) == 1
        assert 'word_order' in errors[0]
        
        # Invalid word_order
        word = WordDefinition(
            name='test',
            src='flight.test',
            encode='float32_split',
            word_order='invalid'
        )
        
        errors = word.validate()
        assert len(errors) == 1
        assert 'invalid word_order' in errors[0]
        
        # Valid float32_split
        word = WordDefinition(
            name='test',
            src='flight.test',
            encode='float32_split',
            word_order='lsw_msw'
        )
        
        errors = word.validate()
        assert len(errors) == 0
    
    def test_word_count(self):
        """Test word count calculation."""
        # Regular encodings use 1 word
        for encoding in ['u16', 'i16', 'bnr16', 'bcd']:
            word = WordDefinition(name='test', src='test', encode=encoding)
            assert word.get_word_count() == 1
        
        # float32_split uses 2 words
        word = WordDefinition(
            name='test',
            src='test',
            encode='float32_split',
            word_order='lsw_msw'
        )
        assert word.get_word_count() == 2


class TestMessageDefinition:
    """Test message definition validation."""
    
    def test_valid_message(self):
        """Test valid message definition."""
        msg = MessageDefinition(
            name='NAV_50HZ',
            rate_hz=50,
            rt=10,
            tr='BC2RT',
            sa=1,
            wc=4,
            words=[
                WordDefinition(name='w1', src='test.w1', encode='u16'),
                WordDefinition(name='w2', src='test.w2', encode='u16'),
                WordDefinition(name='w3', src='test.w3', encode='u16'),
                WordDefinition(name='w4', src='test.w4', encode='u16'),
            ]
        )
        
        errors = msg.validate()
        assert len(errors) == 0
    
    def test_invalid_rate(self):
        """Test invalid message rate."""
        msg = MessageDefinition(
            name='TEST',
            rate_hz=-1,  # Invalid
            rt=5,
            tr='BC2RT',
            sa=1,
            wc=1,
            words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
        )
        
        errors = msg.validate()
        assert any('Rate must be between 0 and 1000 Hz' in e for e in errors)
        
        msg.rate_hz = 1001  # Too high
        errors = msg.validate()
        assert any('Rate must be between 0 and 1000 Hz' in e for e in errors)
    
    def test_invalid_rt_sa(self):
        """Test invalid RT and SA values."""
        # Invalid RT
        msg = MessageDefinition(
            name='TEST',
            rate_hz=10,
            rt=32,  # > 31
            tr='BC2RT',
            sa=1,
            wc=1,
            words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
        )
        
        errors = msg.validate()
        assert any('RT address must be 0-31' in e for e in errors)
        
        # Invalid SA
        msg.rt = 5
        msg.sa = 32  # > 31
        errors = msg.validate()
        assert any('Subaddress must be 0-31' in e for e in errors)
    
    def test_invalid_transfer_type(self):
        """Test invalid transfer type."""
        msg = MessageDefinition(
            name='TEST',
            rate_hz=10,
            rt=5,
            tr='INVALID',
            sa=1,
            wc=1,
            words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
        )
        
        errors = msg.validate()
        assert any('Transfer type must be one of' in e for e in errors)
    
    def test_word_count_mismatch(self):
        """Test word count mismatch detection."""
        msg = MessageDefinition(
            name='TEST',
            rate_hz=10,
            rt=5,
            tr='BC2RT',
            sa=1,
            wc=3,  # Says 3 words
            words=[
                WordDefinition(name='w1', src='test.w1', encode='u16'),
                WordDefinition(name='w2', src='test.w2', encode='u16')
                # But only 2 words defined
            ]
        )
        
        errors = msg.validate()
        assert any('Word count mismatch: declared 3, calculated 2' in e for e in errors)
    
    def test_float32_word_count(self):
        """Test word count with float32_split."""
        msg = MessageDefinition(
            name='TEST',
            rate_hz=10,
            rt=5,
            tr='BC2RT',
            sa=1,
            wc=4,  # 2 float32_split = 4 words
            words=[
                WordDefinition(name='lat', src='test.lat', encode='float32_split', word_order='lsw_msw'),
                WordDefinition(name='lon', src='test.lon', encode='float32_split', word_order='lsw_msw'),
            ]
        )
        
        errors = msg.validate()
        assert len(errors) == 0
    
    def test_is_receive_transmit(self):
        """Test receive/transmit detection."""
        msg = MessageDefinition(
            name='TEST',
            rate_hz=10,
            rt=5,
            tr='BC2RT',
            sa=1,
            wc=1,
            words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
        )
        
        assert msg.is_receive() == True
        assert msg.is_transmit() == False
        
        msg.tr = 'RT2BC'
        assert msg.is_receive() == False
        assert msg.is_transmit() == True


class TestICDDefinition:
    """Test ICD definition validation."""
    
    def test_load_nav_icd(self):
        """Test loading the actual nav_icd.yaml file."""
        icd_path = Path('icd/nav_icd.yaml')
        if not icd_path.exists():
            pytest.skip(f"ICD file not found: {icd_path}")
        
        icd = load_icd(icd_path)
        
        # Check basic properties
        assert icd.bus == 'A'
        assert len(icd.messages) > 0
        
        # Check first message
        nav_msg = icd.messages[0]
        assert nav_msg.name == 'NAV_50HZ'
        assert nav_msg.rate_hz == 50
        assert nav_msg.rt == 10
        assert nav_msg.tr == 'BC2RT'
        assert nav_msg.sa == 1
        
        # Validate word count matches
        total_word_count = sum(w.get_word_count() for w in nav_msg.words)
        assert total_word_count == nav_msg.wc
        
        # Check required fields are present
        for word in nav_msg.words:
            assert word.name is not None
            assert word.encode in ['bnr16', 'u16', 'i16', 'bcd', 'float32_split']
    
    def test_duplicate_messages(self):
        """Test detection of duplicate message definitions."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='MSG1',
                    rate_hz=10,
                    rt=5,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
                ),
                MessageDefinition(
                    name='MSG2',  # Different name but same RT/SA/TR
                    rate_hz=20,
                    rt=5,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
                )
            ]
        )
        
        errors = icd.validate()
        assert any('Duplicate message' in e for e in errors)
    
    def test_missing_rate_hz(self):
        """Test friendly error for missing rate_hz."""
        yaml_content = """
bus: A
messages:
  - name: TEST_MSG
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 1
    words:
      - {name: test, src: flight.test, encode: u16}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(Exception):  # Should raise on missing rate_hz
                load_icd(temp_path)
        finally:
            temp_path.unlink()
    
    def test_unknown_encoding(self):
        """Test friendly error for unknown encoding."""
        yaml_content = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 1
    words:
      - {name: test, src: flight.test, encode: unknown_type}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="invalid encoding"):
                load_icd(temp_path)
        finally:
            temp_path.unlink()
    
    def test_wc_mismatch(self):
        """Test friendly error for word count mismatch."""
        yaml_content = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 5  # Says 5 words
    words:
      - {name: w1, src: flight.test, encode: u16}
      - {name: w2, src: flight.test, encode: u16}
      # Only 2 words defined
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Word count mismatch: declared 5, calculated 2"):
                load_icd(temp_path)
        finally:
            temp_path.unlink()
    
    def test_get_message_by_name(self):
        """Test message retrieval by name."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='MSG1',
                    rate_hz=10,
                    rt=5,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
                ),
                MessageDefinition(
                    name='MSG2',
                    rate_hz=20,
                    rt=6,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w1', src='test.w1', encode='u16')]
                )
            ]
        )
        
        msg = icd.get_message_by_name('MSG1')
        assert msg is not None
        assert msg.name == 'MSG1'
        assert msg.rate_hz == 10
        
        msg = icd.get_message_by_name('NONEXISTENT')
        assert msg is None
    
    def test_bandwidth_calculation(self):
        """Test total bandwidth calculation."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='MSG1',
                    rate_hz=10,
                    rt=5,
                    tr='BC2RT',
                    sa=1,
                    wc=16,  # 16 words at 10 Hz = 160 words/sec
                    words=[WordDefinition(name=f'w{i}', src=f'test.w{i}', encode='u16') 
                           for i in range(16)]
                ),
                MessageDefinition(
                    name='MSG2',
                    rate_hz=50,
                    rt=6,
                    tr='BC2RT',
                    sa=1,
                    wc=8,  # 8 words at 50 Hz = 400 words/sec
                    words=[WordDefinition(name=f'w{i}', src=f'test.w{i}', encode='u16') 
                           for i in range(8)]
                )
            ]
        )
        
        bandwidth = icd.get_total_bandwidth_words_per_sec()
        assert bandwidth == 560  # 160 + 400