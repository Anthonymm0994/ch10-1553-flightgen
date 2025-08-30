"""Test random data generation for all field types."""

import pytest
import tempfile
from pathlib import Path
import yaml

from ch10gen.random_data import RandomDataGenerator, create_random_scenario
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.icd import load_icd


def test_random_generator_basic():
    """Test basic random data generation."""
    gen = RandomDataGenerator()
    
    # Test u16
    value = gen.generate_value({'type': 'u16'})
    assert 0 <= value <= 65535
    
    # Test i16
    value = gen.generate_value({'type': 'i16'})
    assert isinstance(value, int)
    
    # Test bnr16
    value = gen.generate_value({'type': 'bnr16'})
    assert isinstance(value, int)
    
    # Test bcd
    value = gen.generate_value({'type': 'bcd'})
    assert isinstance(value, int)


def test_random_generator_bitfields():
    """Test bitfield generation."""
    gen = RandomDataGenerator()
    
    # Single bit
    value = gen.generate_value({'type': 'u16', 'mask': 0x0001, 'shift': 0})
    assert value in [0, 1]
    
    # Multi-bit field
    value = gen.generate_value({'type': 'u16', 'mask': 0x00F0, 'shift': 4})
    assert 0 <= value <= 15


def test_random_scenario_generation():
    """Test creating a random scenario."""
    scenario = create_random_scenario()
    
    assert scenario['name'] == 'random_test'
    assert scenario['data_mode'] == 'random'
    assert scenario['random_config']['populate_all_fields'] is True


def test_random_ch10_generation():
    """Test generating a CH10 file with random data."""
    # Create a simple test ICD
    icd_data = {
        'bus': 'A',
        'messages': [
            {
                'name': 'TEST_MSG',
                'rate_hz': 10,
                'rt': 10,
                'tr': 'BC2RT',
                'sa': 1,
                'wc': 4,
                'words': [
                    {'name': 'field1', 'encode': 'u16', 'src': 'random'},
                    {'name': 'field2', 'encode': 'i16', 'src': 'random'},
                    {'name': 'field3', 'encode': 'u16', 'src': 'random'},
                    {'name': 'field4', 'encode': 'u16', 'src': 'random'},
                ]
            }
        ]
    }
    
    # Save ICD to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(icd_data, f)
        icd_path = Path(f.name)
    
    try:
        # Load ICD
        icd = load_icd(icd_path)
        
        # Create random scenario
        scenario = create_random_scenario()
        scenario['duration_s'] = 1  # Short duration for test
        
        # Generate CH10 file
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as f:
            output_path = Path(f.name)
        
        stats = write_ch10_file(
            output_path=output_path,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Verify file was created
        assert output_path.exists()
        assert stats['total_messages'] > 0
        assert stats['file_size_bytes'] > 0
        
        # Clean up
        output_path.unlink()
        
    finally:
        # Clean up ICD file
        icd_path.unlink()


def test_all_field_types():
    """Test that all field types generate valid data."""
    gen = RandomDataGenerator()
    
    field_types = ['u16', 'i16', 'bnr16', 'bcd', 'discrete', 'status', 'float32']
    
    for field_type in field_types:
        value = gen.generate_value({'type': field_type})
        assert value is not None
        
        if field_type in ['u16', 'i16', 'bnr16', 'bcd', 'discrete', 'status']:
            assert isinstance(value, int)
        elif field_type == 'float32':
            assert isinstance(value, (int, float))


def test_large_message_generation():
    """Test generating data for messages with many fields."""
    gen = RandomDataGenerator()
    
    # Create a message with many bitfields
    message = {
        'name': 'COMPLEX_MSG',
        'words': []
    }
    
    # Add 32 fields (2 words with 16 bitfields each)
    for word_idx in range(2):
        for bit_idx in range(16):
            message['words'].append({
                'name': f'bit_{word_idx}_{bit_idx}',
                'type': 'u16',
                'mask': 1 << bit_idx,
                'shift': bit_idx,
                'word_index': word_idx
            })
    
    # Generate data
    data = gen.generate_message_data(message)
    
    # Should generate 2 words
    assert len(data) >= 2
    
    # Each word should be 16-bit
    for word in data:
        assert 0 <= word <= 0xFFFF


if __name__ == '__main__':
    # Run basic tests
    test_random_generator_basic()
    test_random_generator_bitfields()
    test_random_scenario_generation()
    test_all_field_types()
    test_large_message_generation()
    
    print("✅ All random data generation tests passed!")
