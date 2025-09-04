"""Chapter 10 writer using PyChapter10."""

import struct
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO
from dataclasses import dataclass

try:
    from chapter10 import C10, Packet
    from chapter10.time import TimeF1
    from chapter10.ms1553 import MS1553F1
    from chapter10.message import MessageF0  # TMATS uses MessageF0
except ImportError:
    raise ImportError("PyChapter10 is required. Install with: pip install pychapter10")

try:
    from .utils.util_time import datetime_to_rtc, datetime_to_ipts
    from .schedule import BusSchedule, ScheduledMessage
    from .flight_profile import FlightProfile, FlightState
    from .icd import ICDDefinition, MessageDefinition, WordDefinition
    from .core.encode1553 import (
        build_command_word, build_status_word, bnr16, u16, i16, bcd, float32_split
    )
    from .utils.errors import MessageErrorInjector, ErrorType
    from .core.tmats import create_default_tmats
except ImportError:
    from utils.util_time import datetime_to_rtc, datetime_to_ipts
    from schedule import BusSchedule, ScheduledMessage
    from flight_profile import FlightProfile, FlightState
    from icd import ICDDefinition, MessageDefinition, WordDefinition
    from core.encode1553 import (
        build_command_word, build_status_word, bnr16, u16, i16, bcd, float32_split
    )
    from utils.errors import MessageErrorInjector, ErrorType
    from core.tmats import create_default_tmats


@dataclass
class Ch10WriterConfig:
    """Configuration for Chapter 10 writer."""
    time_channel_id: int = 0x001  # Time packets on Channel 1 (user-friendly)
    tmats_channel_id: int = 0x000  # TMATS on Channel 0 (required by standard)
    bus_a_channel_id: int = 0x002  # 1553 Bus A on Channel 2 (user-friendly)
    bus_b_channel_id: int = 0x003  # 1553 Bus B on Channel 3 (user-friendly)
    target_packet_bytes: int = 65536  # Standard packet size target
    time_packet_interval_s: float = 1.0  # 1 Hz time packets (required by standard)
    include_filler: bool = False


class Ch10Writer:
    """Write Chapter 10 files with 1553 data."""
    
    def __init__(self, config: Ch10WriterConfig = None, writer_backend: str = 'pyc10'):
        """Initialize writer with configuration.
        
        Args:
            config: Writer configuration
            writer_backend: Backend to use ('irig106' or 'pyc10')
        """
        self.config = config or Ch10WriterConfig()
        self.writer_backend_name = writer_backend
        self.c10 = None
        self.start_time = None
        self.message_count = 0
        self.packet_count = 0
        
    def write_file(self, filepath: Path, schedule: BusSchedule,
                  flight_profile: FlightProfile,
                  icd: ICDDefinition,
                  error_injector: Optional[MessageErrorInjector] = None,
                  start_time: datetime = None,
                  scenario_name: str = "Demo Mission",
                  scenario_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Write complete Chapter 10 file.
        
        Args:
            filepath: Output file path
            schedule: Bus schedule with messages
            flight_profile: Flight profile generator
            icd: ICD definition
            error_injector: Optional error injector
            start_time: Start time (defaults to now)
            scenario_name: Scenario name for TMATS
        
        Returns:
            Statistics dictionary
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        
        self.start_time = start_time
        self.message_count = 0
        self.packet_count = 0
        self.last_ipts = 0  # Track last IPTS value for monotonicity
        
        # Initialize scenario manager if scenario provided with data generation config
        self.scenario_manager = None
        if scenario_config and (
            scenario_config.get('data_mode') == 'random' or 
            scenario_config.get('defaults', {}).get('data_mode') == 'random' or
            scenario_config.get('config', {}).get('default_mode') == 'random' or
            scenario_config.get('defaults', {}).get('data_mode') != 'flight'
        ):
            # Use scenario manager for random or non-flight data modes
            from .scenario_manager import ScenarioManager
            self.scenario_manager = ScenarioManager(scenario_config, icd)
        
        # Open file for binary writing
        filepath = Path(filepath)
        self.filepath = filepath
        self.file = open(filepath, 'wb')
        
        try:
            # Write TMATS as first packet
            self._write_tmats_packet(scenario_name, icd, schedule)
            
            # Write initial time packet (first dynamic packet, required by standard)
            self._write_time_packet(start_time)
            
            # Group messages into packets and write with continuous time packets
            self._write_1553_packets_with_time(schedule, flight_profile, icd, error_injector)
            
            # Write final time packet
            if schedule.messages:
                last_time_relative_s = schedule.messages[-1].time_s
                last_time_abs = datetime.fromtimestamp(start_time.timestamp() + last_time_relative_s, tz=start_time.tzinfo)
                self._write_time_packet(last_time_abs)
            
        finally:
            # Ensure file is closed
            if hasattr(self, 'file') and self.file:
                self.file.close()
        
        return {
            'total_packets': self.packet_count,
            'total_messages': self.message_count,
            'file_size_bytes': self.filepath.stat().st_size if self.filepath.exists() else 0,
            'duration_s': schedule.messages[-1].time_s if schedule.messages else 0
        }
    
    def _write_tmats_packet(self, scenario_name: str, icd: ICDDefinition,
                           schedule: BusSchedule) -> None:
        """Write TMATS packet."""
        # Get message names
        message_names = list(set(msg.name for msg in icd.messages))
        
        # Get schedule statistics
        stats = schedule.get_statistics()
        
        # Create TMATS content
        tmats_content = create_default_tmats(
            scenario_name=scenario_name,
            icd_messages=message_names,
            total_duration_s=stats.get('duration_s', 0),
            total_messages=stats.get('total_messages', 0)
        )
        
        # Create TMATS packet using MessageF0
        tmats_packet = MessageF0()
        tmats_packet.channel_id = self.config.tmats_channel_id
        tmats_packet.data_type = 0x01  # TMATS data type
        tmats_packet.rtc = 0  # First packet at time 0
        tmats_packet.body = tmats_content.encode('utf-8')
        
        # Write packet
        self.file.write(bytes(tmats_packet))
        self.packet_count += 1
    
    def _write_time_packet(self, timestamp: datetime) -> None:
        """Write Time Data, Format 1 packet (data_type = 0x11) with proper CSDW fields."""
        # Create TimeF1 packet with correct data type
        time_packet = TimeF1()
        time_packet.channel_id = self.config.time_channel_id
        time_packet.data_type = 0x11  # Time Data, Format 1 (IRIG-106 standard)
        
        # Ensure RTC is non-negative
        rtc_value = datetime_to_rtc(timestamp, self.start_time)
        time_packet.rtc = max(0, rtc_value)
        
        # Set proper CSDW fields for Time-F1 packets (eliminates "missing time_format" warnings)
        # SRC (bits 3-0): 0x1 = External time source (GPS)
        time_packet.time_source = 1  # External time source
        
        # FMT (bits 7-4): 0x0 = IRIG-B (most common for flight test)
        time_packet.time_format = 0  # IRIG-B format
        
        # DATE (bits 11-8): bit 9 = day-of-year vs month/year, bit 8 = leap year
        time_packet.leap_year = timestamp.year % 4 == 0
        
        # Set time values (IRIG-B format)
        time_packet.seconds = timestamp.second
        time_packet.minutes = timestamp.minute
        time_packet.hours = timestamp.hour
        time_packet.days = timestamp.timetuple().tm_yday
        
        # Write packet
        self.file.write(bytes(time_packet))
        self.packet_count += 1
    
    def _write_1553_packets_with_time(self, schedule: BusSchedule,
                                     flight_profile: FlightProfile,
                                     icd: ICDDefinition,
                                     error_injector: Optional[MessageErrorInjector]) -> None:
        """Write 1553 packets from schedule with continuous time packets at 1 Hz."""
        if not schedule.messages:
            return
            
        # Calculate total duration and time packet intervals
        total_duration_s = schedule.messages[-1].time_s
        time_interval_s = self.config.time_packet_interval_s
        
        # Generate time packet timestamps (1 Hz)
        time_timestamps = []
        current_time_s = 0.0
        while current_time_s <= total_duration_s:
            time_timestamps.append(current_time_s)
            current_time_s += time_interval_s
        
        # Merge 1553 messages and time packets in chronological order
        all_events = []
        
        # Add 1553 messages
        for sched_msg in schedule.messages:
            all_events.append(('1553', sched_msg))
        
        # Add time packets
        for time_s in time_timestamps:
            if time_s > 0:  # Skip initial time packet (already written)
                timestamp = datetime.fromtimestamp(self.start_time.timestamp() + time_s, tz=self.start_time.tzinfo)
                all_events.append(('time', timestamp))
        
        # Sort by time
        all_events.sort(key=lambda x: x[1].time_s if x[0] == '1553' else (x[1] - self.start_time).total_seconds())
        
        # Process events in order
        packet_messages = []
        packet_size = 0
        last_time_packet_s = 0.0
        
        for event_type, event_data in all_events:
            if event_type == 'time':
                # Write time packet
                self._write_time_packet(event_data)
                last_time_packet_s = (event_data - self.start_time).total_seconds()
            elif event_type == '1553':
                sched_msg = event_data
                
                # Estimate message size
                msg_size = 4 + 18 + (sched_msg.message.wc * 2)
                
                # Add message to current packet
                packet_messages.append(sched_msg)
                packet_size += msg_size
                
                # Check if we should flush packet (size or time-based)
                time_since_last_packet = sched_msg.time_s - last_time_packet_s
                should_flush = (len(packet_messages) >= 15 or  # Pack multiple messages per packet for realistic structure
                              packet_size > self.config.target_packet_bytes or
                              time_since_last_packet >= 0.1)  # 100ms time flush
                
                if should_flush:
                    self._write_1553_packet(packet_messages, flight_profile, icd, error_injector)
                    packet_messages = []
                    packet_size = 0
                    last_time_packet_s = sched_msg.time_s
        
        # Write remaining messages
        if packet_messages:
            self._write_1553_packet(packet_messages, flight_profile, icd, error_injector)
    
    def _write_1553_packets(self, schedule: BusSchedule,
                           flight_profile: FlightProfile,
                           icd: ICDDefinition,
                           error_injector: Optional[MessageErrorInjector]) -> None:
        """Write 1553 packets from schedule."""
        # Pack multiple messages per packet for realistic file structure
        # Reference file has ~45 messages per packet, we'll use a conservative 15
        MAX_MESSAGES_PER_PACKET = 15  # Multiple messages per packet for realistic structure
        
        # Group messages into packets based on target size
        packet_messages = []
        packet_size = 0
        
        for sched_msg in schedule.messages:
            # Estimate message size (CSDW + header + command + status + data words)
            # CSDW: 4 bytes + PyChapter10 format: 14 bytes header + 2 bytes command + 2 bytes status + (WC * 2) bytes data
            msg_size = 4 + 18 + (sched_msg.message.wc * 2)
            
            # Add message to current packet first
            packet_messages.append(sched_msg)
            packet_size += msg_size
            
            # Check if we should start a new packet (after adding the message)
            if (len(packet_messages) >= MAX_MESSAGES_PER_PACKET or 
                packet_size > self.config.target_packet_bytes):
                # Write current packet
                self._write_1553_packet(packet_messages, flight_profile, icd, error_injector)
                packet_messages = []
                packet_size = 0
        
        # Write remaining messages
        if packet_messages:
            self._write_1553_packet(packet_messages, flight_profile, icd, error_injector)
    
    def _write_1553_packet(self, messages: List[ScheduledMessage],
                          flight_profile: FlightProfile,
                          icd: ICDDefinition,
                          error_injector: Optional[MessageErrorInjector]) -> None:
        """Write a single 1553 packet containing multiple messages."""
        if not messages:
            return
        
        # Create 1553 F1 packet with messages
        packet = MS1553F1()
        
        # Set channel ID based on bus from ICD
        packet.channel_id = self.config.bus_a_channel_id if icd.bus == 'A' else self.config.bus_b_channel_id
        packet.data_type = 0x19  # MS1553 data type - required for proper packet identification
        
        # Set packet timestamp to first message time (relative to start)
        packet.rtc = int(messages[0].time_s * 1_000_000)  # Convert seconds to microseconds
        
        # Process each message
        for sched_msg in messages:
            msg_def = sched_msg.message
            msg_time_relative_s = sched_msg.time_s  # Already relative to start
            
            # Get flight state at message time
            flight_state = flight_profile.get_state_at_time(sched_msg.time_s)
            
            # Build message words
            command_word = build_command_word(
                rt=msg_def.rt,
                tr=msg_def.is_receive(),
                sa=msg_def.sa,
                wc=msg_def.wc
            )
            
            status_word = build_status_word(
                rt=msg_def.rt,
                message_error=False,
                instrumentation=False,
                service_request=False,
                broadcast_received=False,
                busy=False,
                subsystem_flag=False,
                dynamic_bus_control=False,
                terminal_flag=False
            )
            
            # Encode data words
            if self.scenario_manager:
                # Use scenario manager for data generation
                data_words = self.scenario_manager.generate_message_data(msg_def.name, msg_def)
            else:
                # Use traditional encoding
                data_words = self._encode_data_words(msg_def, flight_state)
            
            # Apply error injection if configured
            if error_injector:
                command_word, status_word, data_words, error_type = error_injector.inject_errors(
                    sched_msg.time_s, command_word, status_word, data_words
                )
            
            # Construct message data: command word, status word, then data words
            message_words = [command_word, status_word] + data_words
            # Convert words to bytes (little-endian 16-bit words)
            message_data = b''.join(struct.pack('<H', word) for word in message_words)
            
            # Create 1553 message and set data
            msg = packet.Message()
            msg.data = message_data
            msg.length = len(message_data)  # PyChapter10 doesn't calculate this automatically
            
            # Set message attributes (IPTS in nanoseconds from start)
            # Ensure IPTS is always strictly increasing to maintain monotonicity
            base_ipts = int(msg_time_relative_s * 1_000_000_000)
            msg.ipts = max(self.last_ipts + 1, base_ipts)
            self.last_ipts = msg.ipts
            
            # Set bus (0 for A, 1 for B)
            msg.bus = 0 if icd.bus == 'A' else 1
            
            # Add message to packet
            packet.append(msg)
            self.message_count += 1
        
        # Fix PyChapter10 bug: manually set CSDW message count
        packet.count = len(messages)
        
        # Write packet
        self.file.write(bytes(packet))
        self.packet_count += 1
    
    
    
    def _encode_data_words(self, msg_def: MessageDefinition, 
                          flight_state: Optional[FlightState]) -> List[int]:
        """Encode data words from flight state using ICD."""
        data_words = []
        
        for word_def in msg_def.words:
            if word_def.const is not None:
                # Constant value
                if word_def.encode == 'float32_split':
                    w1, w2 = float32_split(float(word_def.const), word_def.word_order or 'lsw_msw')
                    data_words.extend([w1, w2])
                else:
                    data_words.append(int(word_def.const) & 0xFFFF)
                    
            elif word_def.src and flight_state:
                # Get value from flight state
                value = self._get_value_from_source(word_def.src, flight_state)
                
                # Apply encoding
                if word_def.encode == 'bnr16':
                    encoded = bnr16(value, word_def.scale, word_def.offset,
                                   rounding=word_def.rounding)
                    data_words.append(encoded)
                    
                elif word_def.encode == 'u16':
                    encoded = u16(value, word_def.scale, word_def.offset)
                    data_words.append(encoded)
                    
                elif word_def.encode == 'i16':
                    encoded = i16(value, word_def.scale, word_def.offset)
                    data_words.append(encoded)
                    
                elif word_def.encode == 'bcd':
                    encoded = bcd(int(value))
                    data_words.append(encoded)
                    
                elif word_def.encode == 'float32_split':
                    w1, w2 = float32_split(value, word_def.word_order or 'lsw_msw')
                    data_words.extend([w1, w2])
                    
                else:
                    # Default to u16
                    data_words.append(int(value) & 0xFFFF)
            else:
                # No source or flight state, use zero
                if word_def.encode == 'float32_split':
                    data_words.extend([0, 0])
                else:
                    data_words.append(0)
        
        return data_words
    
    def _get_value_from_source(self, source: str, flight_state: FlightState) -> float:
        """Get value from source string (e.g., 'flight.altitude_ft')."""
        parts = source.split('.')
        
        if len(parts) >= 2:
            if parts[0] == 'flight':
                # Get from flight state
                attr_name = parts[1]
                if attr_name == 'airspeed_kt':
                    attr_name = 'airspeed_kts'  # Map kt -> kts
                return getattr(flight_state, attr_name, 0)
            elif parts[0] == 'derived':
                # Compute derived values
                if parts[1] == 'mach_x1000':
                    # Approximate mach from airspeed and altitude
                    # At sea level, mach 1 ≈ 661 knots
                    # Simple approximation, not accounting for temperature variations
                    mach = flight_state.airspeed_kts / 661.0
                    return mach * 1000
                elif parts[1] == 'status':
                    # Create status bits (example)
                    status = 0
                    if flight_state.altitude_ft > 10000:
                        status |= 1  # High altitude bit
                    if flight_state.airspeed_kts > 300:
                        status |= 2  # High speed bit
                    return status
        
        # Default to zero if source not recognized
        return 0.0
    
    def _build_test_schedule(self, icd: ICDDefinition, duration_s: float):
        """Build a test schedule for testing purposes."""
        from .schedule import BusSchedule, ScheduledMessage
        
        messages = []
        current_time = 0.0
        interval = 1.0 / icd.messages[0].rate_hz
        major_frame = 0
        minor_frame = 0
        
        while current_time <= duration_s:
            messages.append(ScheduledMessage(
                message=icd.messages[0],
                time_s=current_time,
                major_frame=major_frame,
                minor_frame=minor_frame
            ))
            current_time += interval
            minor_frame += 1
            if minor_frame >= 50:  # 50 minor frames per major frame
                minor_frame = 0
                major_frame += 1
        
        return BusSchedule(messages=messages)


def write_ch10_file(output_path: Path,
                   scenario: Dict[str, Any],
                   icd: ICDDefinition,
                   seed: Optional[int] = None,
                   writer_backend: str = 'irig106') -> Dict[str, Any]:
    """
    High-level function to write a Chapter 10 file.
    
    Args:
        output_path: Output file path
        scenario: Scenario configuration dictionary
        icd: ICD definition
        seed: Random seed for reproducibility
        writer_backend: Writer backend ('irig106' or 'pyc10')
    
    Returns:
        Statistics dictionary
    """
    # Parse scenario
    start_time = datetime.fromisoformat(scenario.get('start_time_utc', datetime.utcnow().isoformat()).replace('Z', '+00:00'))
    duration_s = scenario.get('duration_s', 600)
    profile_config = scenario.get('profile', {})
    bus_config = scenario.get('bus', {})
    
    # Pass scenario config to writer
    
    # Create flight profile
    flight_gen = FlightProfile()
    
    # Create simple waypoints for the duration
    num_waypoints = min(10, int(duration_s / 60) + 2)  # Waypoint every minute
    base_altitude = profile_config.get('base_altitude_ft', 2000)
    
    for i in range(num_waypoints):
        t = (i / (num_waypoints - 1)) * duration_s if num_waypoints > 1 else 0
        altitude = base_altitude + (500 * math.sin(i * math.pi / (num_waypoints - 1)))
        airspeed = 150 + (50 * math.sin(i * math.pi / (num_waypoints - 1)))
        heading = (i * 30) % 360
        flight_gen.add_waypoint(t, altitude, airspeed, heading, 37.7749, -122.4194)
    
    # Build schedule
    from .schedule import build_schedule_from_icd
    schedule = build_schedule_from_icd(
        icd=icd,
        duration_s=duration_s,
        jitter_ms=bus_config.get('jitter_ms', 0)
    )
    
    # Create error injector if configured
    error_injector = None
    if 'errors' in bus_config:
        from .utils.errors import create_error_config_from_dict
        error_config = create_error_config_from_dict(bus_config['errors'])
        error_injector = MessageErrorInjector(error_config)
    
    # Configure writer
    writer_config = Ch10WriterConfig()
    writer_config.target_packet_bytes = bus_config.get('packet_bytes_target', 65536)
    
    # Write file
    writer = Ch10Writer(writer_config, writer_backend=writer_backend)
    
    stats = writer.write_file(
        filepath=output_path,
        schedule=schedule,
        flight_profile=flight_gen,
        icd=icd,
        error_injector=error_injector,
        start_time=start_time,
        scenario_name=scenario.get('name', 'Demo Mission'),
        scenario_config=scenario
    )
    
    # Add error statistics if available
    if error_injector:
        stats['errors'] = error_injector.get_statistics()
    
    # Add backend info
    stats['backend'] = writer_backend
    
    # Generate JSON report next to the CH10 file
    from .report import generate_summary_report
    try:
        report_path = generate_summary_report(output_path, stats)
        stats['report_path'] = str(report_path)
    except Exception:
        pass  # Report generation is optional
    
    return stats
