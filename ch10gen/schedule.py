"""
Schedule building for 1553 bus messages.

This module handles the scheduling and timing of MIL-STD-1553 messages within
Chapter 10 files. It implements a frame-based scheduling system that mimics
real avionics systems where messages are organized into major and minor frames.

Key components:
- ScheduledMessage: Individual message with timing information
- MinorFrame: 20ms frame containing multiple messages
- MajorFrame: 1 second frame containing 50 minor frames
- BusSchedule: Complete schedule for a 1553 bus

The scheduling system ensures proper timing coordination and realistic
message distribution patterns similar to actual flight test data.
"""

import math
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Import ICD definitions with fallback for different execution contexts
try:
    from .icd import ICDDefinition, MessageDefinition
except ImportError:
    from icd import ICDDefinition, MessageDefinition


@dataclass
class ScheduledMessage:
    """
    A message scheduled for a specific time.
    
    This represents a single MIL-STD-1553 message that has been scheduled
    for transmission at a specific time within the Chapter 10 file.
    """
    message: MessageDefinition  # The message definition from ICD
    time_s: float  # Time relative to start (seconds)
    minor_frame: int  # Which minor frame this belongs to (0-49)
    major_frame: int  # Which major frame this belongs to (0+)
    
    def __init__(self, message, time_s, major_frame, minor_frame, **kwargs):
        """Initialize ScheduledMessage with optional legacy parameters."""
        # Handle legacy parameter names
        if 'slot_in_minor' in kwargs:
            minor_frame = kwargs['slot_in_minor']
        
        self.message = message
        self.time_s = time_s
        self.major_frame = major_frame
        self.minor_frame = minor_frame
    
    def __repr__(self):
        return f"{self.message.name}@{self.time_s:.3f}s (MF{self.major_frame}:{self.minor_frame})"


@dataclass
class MinorFrame:
    """A minor frame containing scheduled messages."""
    index: int
    start_time_s: float
    duration_s: float
    messages: List[ScheduledMessage] = field(default_factory=list)
    
    def add_message(self, message: ScheduledMessage):
        """Add a message to this minor frame."""
        self.messages.append(message)
    
    def get_message_count(self) -> int:
        """Get the number of messages in this frame."""
        return len(self.messages)
    
    def get_utilization(self) -> float:
        """Get the utilization percentage of this minor frame."""
        if self.duration_s <= 0:
            return 0.0
        
        # Assume each message takes 1ms
        message_time = len(self.messages) * 0.001
        return (message_time / self.duration_s) * 100


@dataclass
class MajorFrame:
    """A major frame containing minor frames."""
    index: int
    start_time_s: float
    duration_s: float
    minor_frames: List[MinorFrame] = field(default_factory=list)
    
    def add_minor_frame(self, minor_frame: MinorFrame):
        """Add a minor frame to this major frame."""
        self.minor_frames.append(minor_frame)
    
    def get_message_count(self) -> int:
        """Get the total number of messages in this major frame."""
        return sum(mf.get_message_count() for mf in self.minor_frames)


@dataclass
class BusSchedule:
    """Complete schedule for a 1553 bus."""
    messages: List[ScheduledMessage] = field(default_factory=list)
    major_frames: List[MajorFrame] = field(default_factory=list)
    minor_frames: List[MinorFrame] = field(default_factory=list)
    major_frame_duration_s: float = 1.0
    minor_frame_duration_s: float = 0.02
    minor_frames_per_major: int = 50
    
    def add_message(self, message: ScheduledMessage):
        """Add a scheduled message to the schedule."""
        self.messages.append(message)
    
    def add_major_frame(self, major_frame: MajorFrame):
        """Add a major frame to the schedule."""
        self.major_frames.append(major_frame)
    
    def add_minor_frame(self, minor_frame: MinorFrame):
        """Add a minor frame to the schedule."""
        self.minor_frames.append(minor_frame)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the schedule."""
        if not self.messages:
            return {
                'total_messages': 0,
                'total_duration_s': 0.0,
                'major_frames': 0,
                'minor_frames': 0,
                'unique_messages': 0,
                'average_rate_hz': 0.0,
                'bus_utilization_percent': 0.0
            }
        
        total_duration = max(msg.time_s for msg in self.messages)
        
        # Count unique message types
        unique_messages = len(set(msg.message.name for msg in self.messages))
        
        # Calculate average rate
        if total_duration > 0:
            average_rate_hz = len(self.messages) / total_duration
        else:
            average_rate_hz = 0.0
        
        # Calculate bus utilization (simplified - assume each message takes 1ms)
        total_message_time = len(self.messages) * 0.001  # 1ms per message
        bus_utilization_percent = (total_message_time / total_duration) * 100 if total_duration > 0 else 0.0
        
        return {
            'total_messages': len(self.messages),
            'total_duration_s': total_duration,
            'major_frames': len(self.major_frames),
            'minor_frames': len(self.minor_frames),
            'unique_messages': unique_messages,
            'average_rate_hz': average_rate_hz,
            'bus_utilization_percent': bus_utilization_percent
        }
    
    def sort_messages(self):
        """Sort messages by time."""
        self.messages.sort(key=lambda msg: msg.time_s)
    
    def build_schedule(self, icd, duration_s: float, jitter_ms: float = 0.0):
        """Build a complete schedule from ICD and duration.
        
        This method is a compatibility wrapper for tests that expect the old API.
        """
        # Clear existing schedule
        self.messages.clear()
        self.major_frames.clear()
        self.minor_frames.clear()
        
        # Simple scheduling: distribute messages evenly across duration
        if not icd.messages:
            return
        
        total_messages = sum(int(msg.rate_hz * duration_s) for msg in icd.messages)
        if total_messages == 0:
            return
        
        # Calculate timing
        time_step = duration_s / total_messages
        
        message_index = 0
        for msg_def in icd.messages:
            message_count = int(msg_def.rate_hz * duration_s)
            for i in range(message_count):
                time_s = message_index * time_step
                
                # Add jitter if specified
                if jitter_ms > 0:
                    jitter_s = random.uniform(-jitter_ms/1000, jitter_ms/1000)
                    time_s += jitter_s
                
                scheduled_msg = ScheduledMessage(
                    message=msg_def,
                    time_s=time_s,
                    major_frame=int(time_s / self.major_frame_duration_s),
                    minor_frame=int((time_s % self.major_frame_duration_s) / self.minor_frame_duration_s)
                )
                self.messages.append(scheduled_msg)
                message_index += 1
        
        # Sort by time
        self.sort_messages()
        
        # Build frames
        self._build_frames()
    
    def _build_frames(self):
        """Build major and minor frames from scheduled messages."""
        # Group messages by major frame
        major_frame_groups = {}
        for msg in self.messages:
            major_idx = msg.major_frame
            if major_idx not in major_frame_groups:
                major_frame_groups[major_idx] = []
            major_frame_groups[major_idx].append(msg)
        
        # Create major frames
        for major_idx, messages in major_frame_groups.items():
            major_frame = MajorFrame(
                index=major_idx,
                start_time_s=major_idx * self.major_frame_duration_s,
                duration_s=self.major_frame_duration_s
            )
            
            # Group messages by minor frame within major frame
            minor_frame_groups = {}
            for msg in messages:
                minor_idx = msg.minor_frame
                if minor_idx not in minor_frame_groups:
                    minor_frame_groups[minor_idx] = []
                minor_frame_groups[minor_idx].append(msg)
            
            # Create minor frames
            for minor_idx, minor_messages in minor_frame_groups.items():
                minor_frame = MinorFrame(
                    index=minor_idx,
                    start_time_s=major_frame.start_time_s + minor_idx * self.minor_frame_duration_s,
                    duration_s=self.minor_frame_duration_s
                )
                for msg in minor_messages:
                    minor_frame.add_message(msg)
                major_frame.add_minor_frame(minor_frame)
            
            self.add_major_frame(major_frame)
    
    def get_messages_in_window(self, start_time_s: float, end_time_s: float) -> List[ScheduledMessage]:
        """Get messages within a time window."""
        return [msg for msg in self.messages if start_time_s <= msg.time_s < end_time_s]
    
    def validate_schedule(self) -> List[str]:
        """Validate the schedule and return list of errors."""
        errors = []
        
        # Check for overlapping messages (simplified)
        for i, msg1 in enumerate(self.messages):
            for msg2 in self.messages[i+1:]:
                if abs(msg1.time_s - msg2.time_s) < 0.001:  # Within 1ms
                    errors.append(f"Messages {msg1.message.name} and {msg2.message.name} overlap at {msg1.time_s}s")
        
        return errors


def build_schedule_from_icd(
    icd: ICDDefinition,
    duration_s: float,
    major_frame_s: float = 1.0,
    minor_frame_s: float = 0.02,
    jitter_ms: float = 0.0
) -> BusSchedule:
    """
    Build a schedule from ICD definition.
    
    This is the main scheduling function that converts ICD message definitions
    into a timed schedule of 1553 messages. It implements a frame-based
    scheduling system that mimics real avionics systems.
    
    Args:
        icd: ICD definition containing message specifications
        duration_s: Total duration of the schedule (seconds)
        major_frame_s: Duration of each major frame (default 1.0s)
        minor_frame_s: Duration of each minor frame (default 0.02s = 20ms)
        jitter_ms: Random timing jitter to add (milliseconds)
    
    Returns:
        BusSchedule: Complete schedule with all messages timed
    """
    # Initialize schedule with frame timing parameters
    # Major frames are 1 second, minor frames are 20ms (50 minor frames per major)
    schedule = BusSchedule(
        major_frame_duration_s=major_frame_s,
        minor_frame_duration_s=minor_frame_s,
        minor_frames_per_major=int(major_frame_s / minor_frame_s)
    )
    
    # Calculate how many major frames we need for the duration
    num_major_frames = math.ceil(duration_s / major_frame_s)
    
    # Create major frames (1 second each)
    for mf_idx in range(num_major_frames):
        major_frame = MajorFrame(
            index=mf_idx,
            start_time_s=mf_idx * major_frame_s,
            duration_s=major_frame_s
        )
        schedule.add_major_frame(major_frame)
        
        # Create minor frames for this major frame (20ms each)
        for mmf_idx in range(schedule.minor_frames_per_major):
            minor_frame = MinorFrame(
                index=mmf_idx,
                start_time_s=major_frame.start_time_s + (mmf_idx * minor_frame_s),
                duration_s=minor_frame_s
            )
            major_frame.add_minor_frame(minor_frame)
            schedule.add_minor_frame(minor_frame)
    
    # Schedule messages based on their rates
    for message_def in icd.messages:
        # Calculate message intervals
        interval_s = 1.0 / message_def.rate_hz
        
        # Schedule messages throughout the duration
        current_time = 0.0
        while current_time < duration_s:
            # Determine which minor frame this message belongs to
            minor_frame_idx = int(current_time / minor_frame_s)
            major_frame_idx = int(current_time / major_frame_s)
            
            if minor_frame_idx < len(schedule.minor_frames):
                # Create scheduled message
                scheduled_msg = ScheduledMessage(
                    message=message_def,
                    time_s=current_time,
                    minor_frame=minor_frame_idx,
                    major_frame=major_frame_idx
                )
                
                # Add to schedule
                schedule.add_message(scheduled_msg)
                
                # Add to appropriate minor frame
                if minor_frame_idx < len(schedule.minor_frames):
                    schedule.minor_frames[minor_frame_idx].add_message(scheduled_msg)
            
            # Move to next message time
            current_time += interval_s
    
    # Sort messages by time
    schedule.sort_messages()
    
    return schedule
