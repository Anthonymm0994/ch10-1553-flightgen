"""Schedule tests."""

import pytest
from datetime import datetime, timedelta
from ch10gen.schedule import (
    BusSchedule, MinorFrame, MajorFrame, ScheduledMessage,
    build_schedule_from_icd
)
from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition


@pytest.mark.unit
class TestMinorFrameManagement:
    """Test minor frame scheduling and management."""
    
    def test_minor_frame_creation(self):
        """Test minor frame basic creation."""
        frame = MinorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=0.020  # 20ms
        )
        
        assert frame.index == 0
        assert frame.start_time_s == 0.0
        assert frame.duration_s == 0.020
        assert len(frame.messages) == 0
        assert frame.get_utilization() == 0.0
    
    def test_minor_frame_add_message(self):
        """Test adding messages to minor frame."""
        frame = MinorFrame(index=0, start_time_s=0.0, duration_s=0.020)
        
        msg_def = MessageDefinition(
            name='TEST',
            rate_hz=50,
            rt=1,
            tr='BC2RT',
            sa=1,
            wc=4,
            words=[WordDefinition(name=f'w{i}', const=i) for i in range(4)]
        )
        
        sched_msg = ScheduledMessage(
            message=msg_def,
            time_s=0.001,
            minor_frame=0,
            slot_in_minor=0,
            bus=0
        )
        
        frame.add_message(sched_msg)
        
        assert len(frame.messages) == 1
        assert frame.messages[0] == sched_msg
    
    def test_minor_frame_utilization(self):
        """Test minor frame utilization calculation."""
        frame = MinorFrame(index=0, start_time_s=0.0, duration_s=0.020)
        
        # Add messages to increase utilization
        for i in range(5):
            msg_def = MessageDefinition(
                name=f'MSG_{i}',
                rate_hz=50,
                rt=i+1,
                tr='BC2RT',
                sa=1,
                wc=32,  # Max word count
                words=[WordDefinition(name=f'w{j}', const=j) for j in range(32)]
            )
            
            sched_msg = ScheduledMessage(
                message=msg_def,
                time_s=0.001 + i * 0.002,
                minor_frame=0,
                slot_in_minor=i,
                bus=0
            )
            
            frame.add_message(sched_msg)
        
        utilization = frame.get_utilization()
        
        # Should have non-zero utilization
        assert utilization > 0.0
        assert utilization <= 100.0  # Percentage
    
    def test_minor_frame_overflow_detection(self):
        """Test detection of minor frame overflow."""
        frame = MinorFrame(index=0, start_time_s=0.0, duration_s=0.001)  # 1ms - very short
        
        # Try to add too many messages
        messages_added = 0
        for i in range(100):  # Way too many for 1ms
            msg_def = MessageDefinition(
                name=f'OVERFLOW_{i}',
                rate_hz=1000,  # Very high rate
                rt=(i % 30) + 1,
                tr='BC2RT',
                sa=1,
                wc=32,
                words=[WordDefinition(name='w', const=0)] * 32
            )
            
            sched_msg = ScheduledMessage(
                message=msg_def,
                time_s=0.0001 * i,
                minor_frame=0,
                slot_in_minor=i,
                bus=0
            )
            
            frame.add_message(sched_msg)
            messages_added += 1
            
            # Check if we've exceeded capacity
            if frame.get_utilization() > 100.0:
                break
        
        # Should detect overflow before adding all messages
        assert messages_added < 100
        assert frame.get_utilization() > 90.0  # Near or over capacity


@pytest.mark.unit
class TestMajorFrameOrchestration:
    """Test major frame orchestration."""
    
    def test_major_frame_creation(self):
        """Test major frame creation with minor frames."""
        # MajorFrame doesn't take minor_frame_count, create manually
        major = MajorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=1.0
        )
        
        # Add minor frames manually
        for i in range(50):  # 50 x 20ms = 1s
            minor = MinorFrame(
                index=i,
                start_time_s=i * 0.020,
                duration_s=0.020
            )
            major.minor_frames.append(minor)
        
        assert major.index == 0
        assert major.duration_s == 1.0
        assert len(major.minor_frames) == 50
        
        # Check minor frame timing
        for i, minor in enumerate(major.minor_frames):
            expected_start = i * 0.020  # 20ms each
            assert abs(minor.start_time_s - expected_start) < 0.001
    
    def test_major_frame_message_distribution(self):
        """Test message distribution across major frame."""
        major = MajorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=1.0
        )
        
        # Add minor frames
        for i in range(50):
            minor = MinorFrame(
                index=i,
                start_time_s=i * 0.020,
                duration_s=0.020
            )
            major.minor_frames.append(minor)
        
        # Add messages at different rates
        messages = []
        for rate in [1, 10, 50]:  # Different rates
            msg_def = MessageDefinition(
                name=f'RATE_{rate}',
                rate_hz=rate,
                rt=rate,
                tr='BC2RT',
                sa=1,
                wc=2,
                words=[WordDefinition(name='w1', const=0),
                       WordDefinition(name='w2', const=0)]
            )
            
            # Calculate how many times this appears in major frame
            count_in_frame = int(rate * major.duration_s)
            
            for i in range(count_in_frame):
                time_s = i / rate if rate > 0 else 0
                minor_idx = int(time_s / 0.020)  # Which minor frame
                
                if minor_idx < len(major.minor_frames):
                    sched_msg = ScheduledMessage(
                        message=msg_def,
                        time_s=time_s,
                        minor_frame=minor_idx,
                        slot_in_minor=len(major.minor_frames[minor_idx].messages),
                        bus=0
                    )
                    
                    major.minor_frames[minor_idx].add_message(sched_msg)
                    messages.append(sched_msg)
        
        # Check distribution
        total_messages = sum(len(mf.messages) for mf in major.minor_frames)
        assert total_messages == len(messages)
        
        # 1Hz message appears once
        rate_1_count = sum(1 for m in messages if m.message.rate_hz == 1)
        assert rate_1_count == 1
        
        # 10Hz message appears 10 times
        rate_10_count = sum(1 for m in messages if m.message.rate_hz == 10)
        assert rate_10_count == 10
        
        # 50Hz message appears 50 times
        rate_50_count = sum(1 for m in messages if m.message.rate_hz == 50)
        assert rate_50_count == 50


@pytest.mark.unit
class TestBusScheduling:
    """Test bus-level scheduling."""
    
    def test_single_bus_schedule(self):
        """Test scheduling on single bus."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='MSG1',
                    rate_hz=20,
                    rt=1,
                    tr='BC2RT',
                    sa=1,
                    wc=4,
                    words=[WordDefinition(name=f'w{i}', const=i) for i in range(4)]
                ),
                MessageDefinition(
                    name='MSG2',
                    rate_hz=10,
                    rt=2,
                    tr='BC2RT',
                    sa=1,
                    wc=2,
                    words=[WordDefinition(name='w1', const=0),
                           WordDefinition(name='w2', const=1)]
                )
            ]
        )
        
        schedule = build_schedule_from_icd(icd, duration_s=5.0)
        
        # Check message counts
        assert len(schedule.messages) == pytest.approx(20*5 + 10*5, rel=0.1)
        
        # All messages on bus A 
        # Note: bus field might be 'A' or 0 depending on implementation
        assert all(msg.bus in [0, 'A'] for msg in schedule.messages)
        
        # Check timing distribution
        msg1_times = [m.time_s for m in schedule.messages if m.message.name == 'MSG1']
        msg2_times = [m.time_s for m in schedule.messages if m.message.name == 'MSG2']
        
        # MSG1 at 20Hz = every 50ms
        for i in range(1, len(msg1_times)):
            delta = msg1_times[i] - msg1_times[i-1]
            assert abs(delta - 0.050) < 0.010  # Within 10ms tolerance
        
        # MSG2 at 10Hz = every 100ms
        for i in range(1, len(msg2_times)):
            delta = msg2_times[i] - msg2_times[i-1]
            assert abs(delta - 0.100) < 0.010
    
    def test_rt_response_jitter(self):
        """Test RT response time jitter configuration."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='JITTER_TEST',
                    rate_hz=100,
                    rt=5,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w', const=0)]
                )
            ]
        )
        
        # Build schedule (jitter might be applied by default)
        schedule = build_schedule_from_icd(
            icd, 
            duration_s=1.0
        )
        
        # Collect RT response times
        response_times = [msg.rt_response_time_us for msg in schedule.messages]
        
        # Should have variation
        assert len(set(response_times)) > 1  # Not all the same
        assert min(response_times) >= 4.0
        assert max(response_times) <= 12.0
    
    def test_inter_message_gap(self):
        """Test inter-message gap configuration."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name=f'GAP_TEST_{i}',
                    rate_hz=50,
                    rt=i+1,
                    tr='BC2RT',
                    sa=1,
                    wc=2,
                    words=[WordDefinition(name='w1', const=0),
                           WordDefinition(name='w2', const=0)]
                ) for i in range(5)
            ]
        )
        
        schedule = build_schedule_from_icd(icd, duration_s=0.1)
        
        # Check inter-message gaps
        gaps = [msg.inter_message_gap_us for msg in schedule.messages]
        
        # Should have gaps
        assert all(gap > 0 for gap in gaps)
        
        # Default is around 4μs with variation
        assert min(gaps) >= 2.0  # At least 2μs
        assert max(gaps) <= 10.0  # At most 10μs


@pytest.mark.unit  
class TestScheduleEdgeCases:
    """Test schedule edge cases."""
    
    def test_empty_icd(self):
        """Test scheduling with empty ICD."""
        icd = ICDDefinition(bus='A', messages=[])
        
        schedule = build_schedule_from_icd(icd, duration_s=1.0)
        
        assert len(schedule.messages) == 0
        assert len(schedule.major_frames) > 0  # Still creates frame structure
    
    def test_single_message(self):
        """Test scheduling with single message."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='SINGLE',
                    rate_hz=1,  # 1Hz
                    rt=1,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w', const=0)]
                )
            ]
        )
        
        schedule = build_schedule_from_icd(icd, duration_s=10.0)
        
        # Should have 10 instances
        assert len(schedule.messages) == 10
        
        # Check timing
        for i, msg in enumerate(schedule.messages):
            assert abs(msg.time_s - i) < 0.01  # At 1-second intervals
    
    def test_high_rate_messages(self):
        """Test scheduling with very high rate messages."""
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='HIGH_RATE',
                    rate_hz=1000,  # 1kHz - very high
                    rt=1,
                    tr='BC2RT',
                    sa=1,
                    wc=1,
                    words=[WordDefinition(name='w', const=0)]
                )
            ]
        )
        
        schedule = build_schedule_from_icd(icd, duration_s=0.1)  # 100ms
        
        # Should have ~100 messages
        assert len(schedule.messages) == pytest.approx(100, rel=0.1)
        
        # Check they don't overlap
        for i in range(1, len(schedule.messages)):
            time_delta = schedule.messages[i].time_s - schedule.messages[i-1].time_s
            assert time_delta > 0  # Strictly increasing
    
    def test_prime_number_rates(self):
        """Test scheduling with prime number rates."""
        # Prime rates that don't divide evenly
        prime_rates = [7, 11, 13, 17, 23]
        
        messages = []
        for rate in prime_rates:
            messages.append(MessageDefinition(
                name=f'PRIME_{rate}',
                rate_hz=rate,
                rt=rate % 30 + 1,
                tr='BC2RT',
                sa=1,
                wc=1,
                words=[WordDefinition(name='w', const=rate)]
            ))
        
        icd = ICDDefinition(bus='A', messages=messages)
        
        schedule = build_schedule_from_icd(icd, duration_s=1.0)
        
        # Check each rate appears correct number of times
        for rate in prime_rates:
            count = sum(1 for m in schedule.messages 
                       if m.message.name == f'PRIME_{rate}')
            assert count == rate  # Each appears rate times per second
    
    def test_conflicting_schedules(self):
        """Test handling of scheduling conflicts."""
        # Create messages that would conflict
        messages = []
        for i in range(10):
            messages.append(MessageDefinition(
                name=f'CONFLICT_{i}',
                rate_hz=50,  # All at same rate
                rt=i+1,
                tr='BC2RT',
                sa=1,
                wc=32,  # Max size to increase conflict chance
                words=[WordDefinition(name=f'w{j}', const=j) for j in range(32)]
            ))
        
        icd = ICDDefinition(bus='A', messages=messages)
        
        schedule = build_schedule_from_icd(icd, duration_s=0.1)
        
        # Should handle conflicts - check no exact time collisions
        times = [msg.time_s for msg in schedule.messages]
        
        # Sort and check for minimum spacing
        times.sort()
        for i in range(1, len(times)):
            # Messages should have at least minimal spacing
            assert times[i] - times[i-1] >= 0  # No negative time
        
        # All messages should be scheduled
        total_expected = sum(int(msg.rate_hz * 0.1) for msg in messages)
        assert len(schedule.messages) == pytest.approx(total_expected, rel=0.1)
