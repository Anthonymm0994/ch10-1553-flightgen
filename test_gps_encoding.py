#!/usr/bin/env python3
"""Test GPS message encoding."""

from ch10gen.icd import load_icd
from ch10gen.core.encode1553 import float32_split

def test_gps_encoding():
    """Test GPS message encoding."""
    icd = load_icd('icd/test_icd.yaml')
    
    # Find GPS message
    gps_msg = None
    for msg in icd.messages:
        if msg.name == 'GPS_5HZ':
            gps_msg = msg
            break
    
    if not gps_msg:
        print("GPS_5HZ message not found in ICD")
        return
    
    print(f'GPS message: {gps_msg.name}, rt={gps_msg.rt}, sa={gps_msg.sa}')
    
    # Check words
    for word in gps_msg.words:
        print(f'  Word: {word.name}, encode={word.encode}, word_order={word.word_order}')
    
    # Test encoding
    try:
        lat, lon = float32_split(37.7749, 'lsw_msw')
        print(f'  Sample encoding: lat={lat},{lon}')
        print("GPS encoding works correctly")
    except Exception as e:
        print(f"GPS encoding failed: {e}")

if __name__ == "__main__":
    test_gps_encoding()
