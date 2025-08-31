"""Simple tests for schedule module."""

from ch10gen.schedule import ScheduledMessage, MinorFrame
from ch10gen.icd import MessageDefinition


class TestScheduledMessage:
    """Test ScheduledMessage dataclass."""
    
    def test_scheduled_message_creation(self):
        """Test creating a scheduled message."""
        # Create a simple message definition
        msg = MessageDefinition(
            name="TEST_MSG",
            rt=1,
            tr=0,
            sa=1, 
            wc=16,
            rate_hz=10
        )
        
        # Create scheduled message
        sched = ScheduledMessage(
            message=msg,
            time_s=1.5,
            minor_frame=2,
            slot_in_minor=3,
            bus='A',
            retry_count=0
        )
        
        assert sched.message.name == "TEST_MSG"
        assert sched.time_s == 1.5
        assert sched.minor_frame == 2
        assert sched.slot_in_minor == 3
        assert sched.bus == 'A'
        assert sched.retry_count == 0
        
    def test_scheduled_message_repr(self):
        """Test scheduled message string representation."""
        msg = MessageDefinition(
            name="NAV_DATA",
            rt=2,
            tr=0,
            sa=5,
            wc=32,
            rate_hz=20
        )
        
        sched = ScheduledMessage(
            message=msg,
            time_s=0.05,
            minor_frame=0,
            slot_in_minor=1
        )
        
        repr_str = repr(sched)
        assert "NAV_DATA" in repr_str
        assert "0.050000" in repr_str
        assert "MF0" in repr_str
        assert "S1" in repr_str


class TestMinorFrame:
    """Test MinorFrame dataclass."""
    
    def test_minor_frame_creation(self):
        """Test creating a minor frame."""
        frame = MinorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=0.1
        )
        
        assert frame.index == 0
        assert frame.start_time_s == 0.0
        assert frame.duration_s == 0.1
        assert frame.messages == []  # Default empty list
        
    def test_minor_frame_with_messages(self):
        """Test minor frame with messages."""
        msg_def = MessageDefinition(
            name="TEST",
            rt=1,
            tr=0,
            sa=1,
            wc=1,
            rate_hz=10
        )
        
        sched_msg = ScheduledMessage(
            message=msg_def,
            time_s=0.05,
            minor_frame=0,
            slot_in_minor=0
        )
        
        frame = MinorFrame(
            index=0,
            start_time_s=0.0,
            duration_s=0.1,
            messages=[sched_msg]
        )
        
        assert len(frame.messages) == 1
        assert frame.messages[0] == sched_msg
