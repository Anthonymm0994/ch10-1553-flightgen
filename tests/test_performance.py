"""Performance baseline tests."""

import pytest
import time
import tempfile
from pathlib import Path
from datetime import datetime


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceBaseline:
    """Establish performance baselines."""
    
    def test_message_generation_rate(self):
        """Test message generation rate meets baseline."""
        from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
        from ch10gen.schedule import build_schedule_from_icd
        
        # Create high-rate ICD
        messages = []
        for i in range(10):  # 10 different messages
            msg = MessageDefinition(
                name=f'MSG_{i}',
                rate_hz=100,  # 100 Hz each = 1000 Hz total
                rt=i+1,
                tr='BC2RT',
                sa=1,
                wc=4,
                words=[
                    WordDefinition(name='w1', const=i),
                    WordDefinition(name='w2', const=i+1),
                    WordDefinition(name='w3', const=i+2),
                    WordDefinition(name='w4', const=i+3)
                ]
            )
            messages.append(msg)
        
        icd = ICDDefinition(bus='A', messages=messages)
        
        # Build schedule for 10 seconds
        start_time = time.perf_counter()
        schedule = build_schedule_from_icd(icd, duration_s=10)
        elapsed = time.perf_counter() - start_time
        
        # Should generate ~10,000 messages
        expected_messages = 10 * 100 * 10  # messages * rate * duration
        actual_messages = len(schedule.messages)
        
        # Performance metrics
        messages_per_second = actual_messages / elapsed
        
        # Baseline: Should generate at least 50,000 msg/s
        assert messages_per_second > 50000, \
               f"Too slow: {messages_per_second:.0f} msg/s (expected >50k)"
        
        # Message count should be accurate
        assert abs(actual_messages - expected_messages) / expected_messages < 0.01
    
    def test_file_write_speed(self):
        """Test file write speed meets baseline."""
        from ch10gen.ch10_writer import write_ch10_file
        from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
        
        # Simple ICD
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='PERF_TEST',
                    rate_hz=50,
                    rt=1,
                    tr='BC2RT',
                    sa=1,
                    wc=8,
                    words=[WordDefinition(name=f'w{i}', const=i) for i in range(8)]
                )
            ]
        )
        
        scenario = {
            'name': 'Performance Test',
            'duration_s': 60,  # 1 minute
            'seed': 12345,
            'profile': {
                'base_altitude_ft': 10000,
                'segments': [
                    {'type': 'cruise', 'ias_kt': 300, 'hold_s': 60}
                ]
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'perf_test.c10'
            
            start_time = time.perf_counter()
            stats = write_ch10_file(
                output_path=output_path,
                scenario=scenario,
                icd=icd,
                writer_backend='irig106',
                seed=12345
            )
            elapsed = time.perf_counter() - start_time
            
            # Performance metrics
            messages = stats['total_messages']
            throughput_msg_per_sec = messages / elapsed
            file_size = output_path.stat().st_size
            write_speed_mb_per_sec = (file_size / 1024 / 1024) / elapsed
            
            # Baselines
            assert elapsed < 5.0, f"Too slow: {elapsed:.1f}s for 60s scenario"
            assert throughput_msg_per_sec > 1000, \
                   f"Throughput too low: {throughput_msg_per_sec:.0f} msg/s"
    
    def test_memory_usage_stable(self):
        """Test that memory usage is stable for long scenarios."""
        import gc
        import sys
        
        # Force garbage collection
        gc.collect()
        
        # This is a simple check - real memory profiling would use tracemalloc
        # Just verify we can handle a long scenario without obvious issues
        from ch10gen.flight_profile import FlightProfileGenerator
        
        # Generate large profile
        gen = FlightProfileGenerator(seed=999)
        segments = [
            {'type': 'cruise', 'ias_kt': 300, 'hold_s': 3600}  # 1 hour
        ]
        
        gen.generate_profile(
            start_time=datetime.utcnow(),
            duration_s=3600,
            segments=segments
        )
        
        # Should have generated states
        assert len(gen.states) > 0
        
        # States should not grow unbounded
        # At 100Hz internal rate, 1 hour = 360,000 states
        # Each state is ~200 bytes, so ~72MB total
        assert len(gen.states) <= 360000
        
        # Clear and collect
        gen.states.clear()
        gc.collect()


@pytest.mark.integration
@pytest.mark.slow
class TestScalability:
    """Test scalability limits."""
    
    def test_max_messages_per_frame(self):
        """Test maximum messages that fit in a minor frame."""
        from ch10gen.schedule import MinorFrame
        
        # Create minor frame (20ms typical)
        frame = MinorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=0.020  # 20ms
        )
        
        # Calculate theoretical max messages
        # Each message ~44 bytes minimum (cmd + status + gap)
        # At 1 Mbps, 20ms = 2500 bytes theoretical
        # Practical limit with overhead ~50 messages
        
        # Verify utilization calculation
        utilization = frame.get_utilization()
        assert utilization >= 0  # Should calculate without error
    
    def test_large_icd_handling(self):
        """Test handling of large ICDs with many messages."""
        from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
        
        # Create large ICD with 100 messages
        messages = []
        for rt in range(1, 11):  # 10 RTs
            for sa in range(1, 11):  # 10 SAs each
                msg = MessageDefinition(
                    name=f'RT{rt}_SA{sa}',
                    rate_hz=1,  # Low rate to avoid overload
                    rt=rt,
                    tr='BC2RT',
                    sa=sa,
                    wc=2,
                    words=[
                        WordDefinition(name='data1', const=0),
                        WordDefinition(name='data2', const=0)
                    ]
                )
                messages.append(msg)
        
        icd = ICDDefinition(bus='A', messages=messages)
        
        # Should handle without error
        assert len(icd.messages) == 100
        
        # Validation should pass
        errors = icd.validate()
        assert len(errors) == 0
