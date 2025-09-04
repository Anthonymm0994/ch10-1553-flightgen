"""Tests for time utilities."""

import pytest
from datetime import datetime, timezone, timedelta

from ch10gen.utils.util_time import (
    datetime_to_rtc,
    rtc_to_datetime,
    datetime_to_ipts,
    ipts_to_datetime,
    parse_timestamp
)


class TestRTCConversion:
    """Test RTC (Relative Time Counter) conversions."""
    
    def test_datetime_to_rtc_basic(self):
        """Test basic datetime to RTC conversion."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        rtc = datetime_to_rtc(dt)
        
        # Should be microseconds since Unix epoch
        expected = int(dt.timestamp() * 1_000_000)
        assert rtc == expected
        
    def test_datetime_to_rtc_with_base_time(self):
        """Test RTC conversion with base time."""
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        dt = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        rtc = datetime_to_rtc(dt, base_time=base)
        
        # Should be 1 hour = 3600 seconds = 3,600,000,000 microseconds
        assert rtc == 3_600_000_000
        
    def test_datetime_to_rtc_naive(self):
        """Test RTC conversion with naive datetime."""
        dt = datetime(2024, 1, 1, 12, 0, 0)  # No timezone
        rtc = datetime_to_rtc(dt)
        
        # Should add UTC timezone and convert
        assert isinstance(rtc, int)
        assert rtc > 0
        
    def test_rtc_to_datetime(self):
        """Test RTC to datetime conversion."""
        # 1 Jan 2024 00:00:00 UTC in microseconds
        rtc = 1_704_067_200_000_000  
        dt = rtc_to_datetime(rtc)
        
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc
        
    def test_rtc_roundtrip(self):
        """Test RTC conversion roundtrip."""
        original = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=timezone.utc)
        rtc = datetime_to_rtc(original)
        converted = rtc_to_datetime(rtc)
        
        # Should match to microsecond precision
        assert converted.year == original.year
        assert converted.month == original.month
        assert converted.day == original.day
        assert converted.hour == original.hour
        assert converted.minute == original.minute
        assert converted.second == original.second
        assert abs(converted.microsecond - original.microsecond) < 10


class TestIPTSConversion:
    """Test IPTS (Intra-Packet Time Stamp) conversions."""
    
    def test_datetime_to_ipts(self):
        """Test datetime to IPTS conversion."""
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        dt = datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc)  # 1 second later
        
        ipts = datetime_to_ipts(dt, base)
        
        # Should be 1 second = 1,000,000,000 nanoseconds
        assert ipts == 1_000_000_000
        
    def test_datetime_to_ipts_microseconds(self):
        """Test IPTS with microsecond precision."""
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        dt = datetime(2024, 1, 1, 0, 0, 0, 1000, tzinfo=timezone.utc)  # 1ms later
        
        ipts = datetime_to_ipts(dt, base)
        
        # Should be 1ms = 1,000,000 nanoseconds
        assert ipts == 1_000_000
        
    def test_ipts_to_datetime(self):
        """Test IPTS to datetime conversion."""
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ipts = 5_500_000_000  # 5.5 seconds
        
        dt = ipts_to_datetime(ipts, base)
        
        expected = base + timedelta(seconds=5.5)
        assert dt == expected
        
    def test_ipts_roundtrip(self):
        """Test IPTS conversion roundtrip."""
        base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        original = datetime(2024, 1, 1, 0, 1, 23, 456789, tzinfo=timezone.utc)
        
        ipts = datetime_to_ipts(original, base)
        converted = ipts_to_datetime(ipts, base)
        
        # Should match to nanosecond precision (limited by datetime precision)
        delta = abs((converted - original).total_seconds())
        assert delta < 1e-6  # Within 1 microsecond


class TestTimestampParsing:
    """Test timestamp parsing."""
    
    def test_parse_datetime_object(self):
        """Test parsing when already a datetime."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = parse_timestamp(dt)
        assert result == dt
        
    def test_parse_iso_format(self):
        """Test parsing ISO format."""
        timestamps = [
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T12:00:00",
        ]
        
        for ts in timestamps:
            dt = parse_timestamp(ts)
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 1
            assert dt.hour == 12
            assert dt.minute == 0
            assert dt.second == 0
            assert dt.tzinfo == timezone.utc
            
    def test_parse_common_formats(self):
        """Test parsing common timestamp formats."""
        timestamps = [
            ("2024-01-01T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ"),
            ("2024-01-01T12:00:00", "%Y-%m-%dT%H:%M:%S"),
            ("2024-01-01 12:00:00", "%Y-%m-%d %H:%M:%S"),
        ]
        
        for ts, _ in timestamps:
            dt = parse_timestamp(ts)
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 1
            assert dt.hour == 12
            
    def test_parse_invalid_format(self):
        """Test parsing invalid format raises error."""
        with pytest.raises(ValueError, match="Could not parse timestamp"):
            parse_timestamp("not a timestamp")
            
    def test_parse_with_microseconds(self):
        """Test parsing ISO format with microseconds."""
        ts = "2024-01-01T12:00:00.123456Z"
        dt = parse_timestamp(ts)
        
        assert dt.year == 2024
        assert dt.microsecond == 123456
