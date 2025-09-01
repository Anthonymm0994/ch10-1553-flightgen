#!/usr/bin/env python3
"""Test inspector functionality for CH10 files."""

import pytest
import tempfile
import json
from pathlib import Path
from ch10gen.icd import load_icd
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.inspector import inspect_1553_timeline, write_timeline


def test_inspector_basic_functionality():
    """Test that the inspector can read and parse CH10 files correctly."""
    # Load test ICD
    icd = load_icd(Path("icd/test_icd.yaml"))
    
    # Create scenario
    scenario = {
        'duration_s': 2,  # Short duration for testing
        'name': 'test_inspector'
    }
    
    # Generate CH10 file
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_inspector.ch10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        # Verify file was created
        assert output_file.exists(), f"CH10 file was not created: {output_file}"
        assert output_file.stat().st_size > 0, f"CH10 file is empty: {output_file}"
        
        # Test inspector with different readers
        for reader in ['wire', 'auto']:
            print(f"\n🔍 Testing inspector with reader: {reader}")
            
            # Inspect the file
            messages = list(inspect_1553_timeline(
                filepath=output_file,
                channel='auto',
                max_messages=100,
                reader=reader
            ))
            
            assert len(messages) > 0, f"No messages found with reader '{reader}'"
            
            # Check message structure
            for msg in messages[:5]:  # Check first 5 messages
                assert 'ipts_ns' in msg, f"Missing 'ipts_ns' in message: {msg}"
                assert 't_rel_ms' in msg, f"Missing 't_rel_ms' in message: {msg}"
                assert 'rt' in msg, f"Missing 'rt' in message: {msg}"
                assert 'sa' in msg, f"Missing 'sa' in message: {msg}"
                assert 'tr' in msg, f"Missing 'tr' in message: {msg}"
                assert 'wc' in msg, f"Missing 'wc' in message: {msg}"
                assert 'status' in msg, f"Missing 'status' in message: {msg}"
                
                # Check that values are reasonable
                assert isinstance(msg['rt'], int), f"RT should be int: {msg['rt']}"
                assert 1 <= msg['rt'] <= 31, f"RT out of range: {msg['rt']}"
                assert isinstance(msg['sa'], int), f"SA should be int: {msg['sa']}"
                assert 0 <= msg['sa'] <= 31, f"SA out of range: {msg['sa']}"
                assert isinstance(msg['wc'], int), f"WC should be int: {msg['wc']}"
                assert 1 <= msg['wc'] <= 32, f"WC out of range: {msg['wc']}"
                assert msg['tr'] in ['BC2RT', 'RT2BC'], f"Invalid TR: {msg['tr']}"
            
            # Check that we can find NAV messages (RT=10)
            nav_messages = [msg for msg in messages if msg['rt'] == 10]
            assert len(nav_messages) > 0, f"No NAV messages (RT=10) found with reader '{reader}'"
            
            print(f"✅ Reader '{reader}': Found {len(messages)} total messages, {len(nav_messages)} NAV messages")


def test_inspector_json_output():
    """Test that the inspector can write JSON output correctly."""
    # Load test ICD
    icd = load_icd(Path("icd/test_icd.yaml"))
    
    # Create scenario
    scenario = {
        'duration_s': 1,  # Very short for testing
        'name': 'test_json_output'
    }
    
    # Generate CH10 file
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_json.ch10"
        json_file = Path(tmpdir) / "test_output.jsonl"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        # Inspect and write to JSON
        message_count = write_timeline(
            filepath=output_file,
            output_path=json_file,
            channel='auto',
            max_messages=50,
            reader='wire'
        )
        
        # Also get messages for comparison
        messages = list(inspect_1553_timeline(
            filepath=output_file,
            channel='auto',
            max_messages=50,
            reader='wire'
        ))
        
        # Verify JSON file was created
        assert json_file.exists(), f"JSON output file was not created: {json_file}"
        assert json_file.stat().st_size > 0, f"JSON output file is empty: {json_file}"
        
        # Read and validate JSON content
        json_messages = []
        with open(json_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    json_messages.append(json.loads(line))
        
        assert len(json_messages) > 0, "No messages in JSON output"
        assert len(json_messages) == message_count, f"Message count mismatch: JSON={len(json_messages)}, written={message_count}"
        assert len(json_messages) == len(messages), f"Message count mismatch: JSON={len(json_messages)}, inspector={len(messages)}"
        
        # Verify JSON structure
        for json_msg in json_messages[:3]:  # Check first 3
            assert 'ipts_ns' in json_msg
            assert 'rt' in json_msg
            assert 'sa' in json_msg
            assert 'wc' in json_msg
            assert isinstance(json_msg['rt'], int)
            assert isinstance(json_msg['sa'], int)
            assert isinstance(json_msg['wc'], int)
        
        print(f"✅ JSON output: {len(json_messages)} messages written correctly")


def test_inspector_error_handling():
    """Test that the inspector handles errors gracefully."""
    # Test with non-existent file
    with pytest.raises(Exception):  # Should raise some kind of error
        list(inspect_1553_timeline(
            filepath=Path("non_existent_file.ch10"),
            channel='auto',
            max_messages=10,
            reader='wire'
        ))
    
    # Test with invalid channel
    # Create a valid file first
    icd = load_icd(Path("icd/test_icd.yaml"))
    scenario = {'duration_s': 0.5, 'name': 'test_error'}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_error.ch10"
        
        write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        # Test with invalid channel - should handle gracefully
        try:
            messages = list(inspect_1553_timeline(
                filepath=output_file,
                channel='invalid_channel',
                max_messages=10,
                reader='wire'
            ))
            # Should either work or raise a clear error
        except Exception as e:
            # Error should be informative
            assert "channel" in str(e).lower() or "invalid" in str(e).lower(), f"Unclear error message: {e}"
    
    print("✅ Error handling works correctly")


if __name__ == "__main__":
    # Run tests directly
    test_inspector_basic_functionality()
    test_inspector_json_output()
    test_inspector_error_handling()
    print("✅ All inspector tests passed!")
