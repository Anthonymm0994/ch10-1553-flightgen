"""
CLI entry point for ch10gen.

This module provides the command-line interface for generating IRIG 106 Chapter 10 files
with MIL-STD-1553 bus data. It handles multiple import strategies to work in different
execution contexts (package, direct, or installed).
"""

import sys
import click
import yaml
import random
from pathlib import Path
from datetime import datetime, timezone

# Import strategy: Try multiple approaches to handle different execution contexts
# This is necessary because the module can be run as:
# 1. python -m ch10gen (package execution)
# 2. python ch10gen/__main__.py (direct execution)
# 3. ch10gen (installed package)
try:
    # Package execution (python -m ch10gen)
    from .icd import load_icd, validate_icd_file
    from .flight_profile import FlightProfile
    from .schedule import build_schedule_from_icd
    from .ch10_writer import write_ch10_file, Ch10WriterConfig
    from .config import get_config
    from .validate import validate_file
    from .utils.errors import create_error_config_from_dict, MessageErrorInjector
except ImportError:
    # Direct execution (python ch10gen/__main__.py) or packaged execution
    try:
        from icd import load_icd, validate_icd_file
        from flight_profile import FlightProfile
        from schedule import build_schedule_from_icd
        from ch10_writer import write_ch10_file, Ch10WriterConfig
        from config import get_config
        from validate import validate_file
        from utils.errors import create_error_config_from_dict, MessageErrorInjector
    except ImportError:
        # Try importing from ch10gen package (installed package execution)
        from ch10gen.icd import load_icd, validate_icd_file
        from ch10gen.flight_profile import FlightProfile
        from ch10gen.schedule import build_schedule_from_icd
        from ch10gen.ch10_writer import write_ch10_file, Ch10WriterConfig
        from ch10gen.config import get_config
        from ch10gen.validate import validate_file
        from ch10gen.utils.errors import create_error_config_from_dict, MessageErrorInjector


@click.group()
@click.version_option(version='1.0.0', prog_name='ch10gen')
def cli():
    """ch10-1553-flightgen - Generate realistic CH10 files with 1553 flight test data."""
    pass


@cli.command()
@click.option('--scenario', '-s', type=click.Path(exists=True), required=True,
              help='Path to scenario YAML file')
@click.option('--icd', '-i', type=click.Path(exists=True), required=True,
              help='    ')
@click.option('--out', '-o', type=click.Path(), required=True,
              help='Output CH10 file path')
@click.option('--writer', type=click.Choice(['irig106', 'pyc10']), default='irig106',
              help='Writer backend: irig106 (spec-compliant) or pyc10 (compatibility)')
@click.option('--start', type=str, default=None,
              help='Start time (ISO format, default: now)')
@click.option('--duration', type=float, default=None,
              help='Duration in seconds (overrides scenario)')
@click.option('--rate-hz', type=float, default=None,
              help='Base sample rate Hz (default: from scenario)')
@click.option('--packet-bytes', type=int, default=65536,
              help='Target packet size in bytes')
@click.option('--seed', type=int, default=None,
              help='Random seed for reproducibility')
@click.option('--err.parity', 'err_parity', type=float, default=0.0,
              help='Parity error percentage')
@click.option('--err.late', 'err_late', type=float, default=0.0,
              help='Late response percentage')
@click.option('--err.no-response', 'err_no_response', type=float, default=0.0,
              help='No response percentage')
@click.option('--jitter-ms', type=float, default=0.0,
              help='Timestamp jitter in milliseconds')
@click.option('--dry-run', is_flag=True,
              help='Preview without writing file')
@click.option('--zero-jitter', is_flag=True,
              help='Disable all timing jitter (for tests)')
@click.option('--verbose', '-v', is_flag=True,
              help='Verbose output')
def build(scenario, icd, out, writer, start, duration, rate_hz, packet_bytes, seed,
         err_parity, err_late, err_no_response, jitter_ms, dry_run, zero_jitter, verbose):
    """Build CH10 file from scenario and ICD."""
    
    try:
        # Get merged config
        cli_args = {
            'writer': writer,
            'packet_bytes': packet_bytes,
            'dry_run': dry_run,
            'zero_jitter': zero_jitter,
            'verbose': verbose,
            'seed': seed
        }
        config = get_config(cli_args=cli_args, scenario_path=Path(scenario))
        
        # Print resolved config
        click.echo(f"[CONFIG] {config.summary()}")
        
        # Load scenario
        with open(scenario, 'r') as f:
            scenario_data = yaml.safe_load(f)
        
        if verbose:
            click.echo(f"Loaded scenario: {scenario_data.get('name', 'Unknown')}")
        
        # Load and validate ICD
        icd_def = load_icd(icd)
        
        if verbose:
            click.echo(f"Loaded ICD with {len(icd_def.messages)} messages")
            click.echo(f"  Bus: {icd_def.bus}")
            click.echo(f"  Total bandwidth: {icd_def.get_total_bandwidth_words_per_sec():.0f} words/sec")
        
        # Override scenario parameters if provided
        if start:
            scenario_data['start_time_utc'] = start
        if duration:
            scenario_data['duration_s'] = duration
        if seed:
            scenario_data['seed'] = seed
        
        # Set error injection if specified
        if err_parity or err_late or err_no_response:
            if 'bus' not in scenario_data:
                scenario_data['bus'] = {}
            if 'errors' not in scenario_data['bus']:
                scenario_data['bus']['errors'] = {}
            
            scenario_data['bus']['errors']['parity_percent'] = err_parity
            scenario_data['bus']['errors']['late_percent'] = err_late
            scenario_data['bus']['errors']['no_response_percent'] = err_no_response
        
        if jitter_ms:
            if 'bus' not in scenario_data:
                scenario_data['bus'] = {}
            scenario_data['bus']['jitter_ms'] = jitter_ms
        
        if packet_bytes != 65536:
            if 'bus' not in scenario_data:
                scenario_data['bus'] = {}
            scenario_data['bus']['packet_bytes_target'] = packet_bytes
        
        # Dry run - just show what would be done
        if dry_run:
            click.echo("\nDry run mode - no file will be written")
            click.echo(f"Would generate: {out}")
            
            # Generate and preview flight profile
            start_time = datetime.fromisoformat(
                scenario_data.get('start_time_utc', datetime.utcnow().isoformat()).replace('Z', '+00:00')
            )
            duration_s = scenario_data.get('duration_s', 600)
            
            flight_gen = FlightProfile()
            
            # Create simple waypoints for the duration
            import math
            num_waypoints = min(10, int(duration_s / 60) + 2)  # Waypoint every minute
            base_altitude = scenario_data.get('profile', {}).get('base_altitude_ft', 2000)
            
            for i in range(num_waypoints):
                t = (i / (num_waypoints - 1)) * duration_s if num_waypoints > 1 else 0
                altitude = base_altitude + (500 * math.sin(i * math.pi / (num_waypoints - 1)))
                airspeed = 150 + (50 * math.sin(i * math.pi / (num_waypoints - 1)))
                heading = (i * 30) % 360
                flight_gen.add_waypoint(t, altitude, airspeed, heading, 37.7749, -122.4194)
            
            # Show sample flight states
            click.echo("\nSample flight states:")
            sample_times = [0, duration_s/4, duration_s/2, 3*duration_s/4, duration_s-1]
            for t in sample_times:
                state = flight_gen.get_state_at_time(t)
                if state:
                    click.echo(f"  t={t:6.1f}s: Alt={state.altitude_ft:6.0f}ft, "
                             f"IAS={state.airspeed_kts:3.0f}kt, Hdg={state.heading_deg:3.0f}°")
            
            # Build and show schedule
            schedule = build_schedule_from_icd(
                icd=icd_def,
                duration_s=duration_s,
                jitter_ms=scenario_data.get('bus', {}).get('jitter_ms', 0)
            )
            
            stats = schedule.get_statistics()
            click.echo(f"\nSchedule statistics:")
            click.echo(f"  Total messages: {stats['total_messages']:,}")
            click.echo(f"  Message types: {stats['unique_messages']}")
            click.echo(f"  Average rate: {stats['average_rate_hz']:.1f} Hz")
            click.echo(f"  Bus utilization: {stats['bus_utilization_percent']:.1f}%")
            
            return
        
        # Create output directory if needed
        output_path = Path(out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate the file
        click.echo(f"Generating CH10 file: {output_path}")
        
        stats = write_ch10_file(
            output_path=output_path,
            scenario=scenario_data,
            icd=icd_def,
            seed=seed or scenario_data.get('seed'),
            writer_backend=writer
        )
        
        # Show statistics
        click.echo(f"\n[SUCCESS] CH10 file generated successfully!")
        click.echo(f"  Output location: {output_path.absolute()}")
        click.echo(f"  File size: {stats['file_size_bytes']:,} bytes")
        click.echo(f"  Total packets: {stats['total_packets']:,}")
        click.echo(f"  Total messages: {stats['total_messages']:,}")
        click.echo(f"  Duration: {stats['duration_s']:.1f} seconds")
        
        if 'errors' in stats:
            error_stats = stats['errors']
            if error_stats['total_errors'] > 0:
                click.echo(f"  Errors injected: {error_stats['total_errors']}")
        
        click.echo(f"\nFile is ready for use at: {output_path.absolute()}")
        
    except Exception as e:
        click.echo(f"\n[ERROR] Build failed: {e}", err=True)
        if hasattr(e, '__traceback__'):
            import traceback
            if verbose:
                click.echo(f"\nDetailed error information:", err=True)
                click.echo(f"{traceback.format_exc()}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed validation output')
@click.option('--external', is_flag=True,
              help='Run external c10-tools validation if available')
@click.option('--no-c10-tools', is_flag=True,
              help='Skip external c10-tools validation')
def validate(file, verbose, external, no_c10_tools):
    """Validate a CH10 file."""
    
    try:
        filepath = Path(file)
        click.echo(f"Validating: {filepath}")
        
        results = validate_file(
            filepath=filepath,
            verbose=verbose,
            use_c10_tools=external and not no_c10_tools
        )
        
        # Summary output if not verbose
        if not verbose:
            click.echo(f"\nValidation Results:")
            click.echo(f"  File size: {results['file_size_bytes']:,} bytes")
            click.echo(f"  Packets: {results['packet_count']:,}")
            click.echo(f"  TMATS: {'[PRESENT]' if results['tmats_present'] else '[MISSING]'}")
            click.echo(f"  Time packets: {results['time_packets']}")
            click.echo(f"  1553 packets: {results['1553_packets']}")
            click.echo(f"  1553 messages: {results['1553_messages']}")
            
            if 'message_rate_hz' in results:
                click.echo(f"  Message rate: {results['message_rate_hz']:.1f} Hz")
            
            if results['errors']:
                click.echo(f"\nERROR Errors: {len(results['errors'])}")
                for error in results['errors'][:5]:
                    click.echo(f"    - {error}")
            
            if results['warnings']:
                click.echo(f"\nWARNING  Warnings: {len(results['warnings'])}")
                for warning in results['warnings'][:5]:
                    click.echo(f"    - {warning}")
            
            if not results['errors']:
                click.echo(f"\n[SUCCESS] Validation PASSED")
                click.echo(f"File '{filepath.name}' is valid and ready for use")
            else:
                click.echo(f"\n[ERROR] Validation FAILED")
                click.echo(f"File '{filepath.name}' has {len(results['errors'])} validation errors")
                sys.exit(1)
        
    except Exception as e:
        click.echo(f"ERROR Error: {e}", err=True)
        sys.exit(1)





@cli.command()
@click.argument('icd', type=click.Path(exists=True))
def check_icd(icd):
    """Validate an ICD file."""
    
    try:
        filepath = Path(icd)
        click.echo(f"Checking ICD: {filepath}")
        
        validation_result = validate_icd_file(filepath)
        
        if not validation_result['valid']:
            click.echo(f"\nERROR ICD validation failed with {len(validation_result['errors'])} errors:")
            for error in validation_result['errors']:
                click.echo(f"  - {error}")
            sys.exit(1)
        else:
            # Load and show summary
            icd_def = load_icd(filepath)
            
            click.echo(f"\n[SUCCESS] ICD file '{filepath.name}' is valid!")
            click.echo(f"\nSummary:")
            click.echo(f"  Bus: {icd_def.bus}")
            click.echo(f"  Messages: {len(icd_def.messages)}")
            click.echo(f"  Total bandwidth: {icd_def.get_total_bandwidth_words_per_sec():.0f} words/sec")
            
            click.echo(f"\nMessage rates:")
            for rate in icd_def.get_unique_rates():
                messages = icd_def.get_messages_by_rate(rate)
                click.echo(f"  {rate:6.1f} Hz: {len(messages)} messages")
            
            click.echo(f"\nMessages:")
            for msg in icd_def.messages[:10]:  # Show first 10
                click.echo(f"  - {msg.name}: RT{msg.rt} SA{msg.sa} {msg.tr} WC{msg.wc} @ {msg.rate_hz}Hz")
            
            if len(icd_def.messages) > 10:
                click.echo(f"  ... and {len(icd_def.messages) - 10} more")
    
    except Exception as e:
        click.echo(f"\n[ERROR] ICD check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--channel', type=click.Choice(['1553A', '1553B', 'auto']), default='auto',
              help='Channel to inspect')
@click.option('--reader', type=click.Choice(['auto', 'pyc10', 'wire']), default='auto',
              help='Reader to use: auto (try pyc10 then wire), pyc10, or wire')
@click.option('--out', type=click.Path(), required=True,
              help='Output JSONL file path')
@click.option('--max-messages', type=int, default=100000,
              help='Maximum messages to process')
@click.option('--rt', type=int, default=None,
              help='Filter by RT address (0-31)')
@click.option('--sa', type=int, default=None,
              help='Filter by subaddress (0-31)')
@click.option('--errors-only', is_flag=True,
              help='Only output messages with errors')
def inspect(file, channel, reader, out, max_messages, rt, sa, errors_only):
    """Extract 1553 timeline from CH10 file."""
    try:
        try:
            from .inspector import write_timeline
        except ImportError:
            from ch10gen.inspector import write_timeline
        
        filepath = Path(file)
        output_path = Path(out)
        
        if not filepath.exists():
            click.echo(f"ERROR File not found: {filepath}", err=True)
            sys.exit(1)
        
        click.echo(f"Inspecting: {filepath}")
        click.echo(f"  Channel: {channel}")
        click.echo(f"  Reader: {reader}")
        if rt is not None:
            click.echo(f"  RT filter: {rt}")
        if sa is not None:
            click.echo(f"  SA filter: {sa}")
        if errors_only:
            click.echo(f"  Errors only: Yes")
        
        count = write_timeline(
            filepath, output_path, channel, max_messages, rt, sa, errors_only, reader
        )
        
        click.echo(f"\n[SUCCESS] Timeline written to {output_path}")
        click.echo(f"  Messages: {count:,}")
        
    except Exception as e:
        click.echo(f"ERROR Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--timeout-s', type=int, default=20,
              help='Timeout for external tools')
@click.option('--out', type=click.Path(),
              help='Output JSON file path')
def validate_external(file, timeout_s, out):
    """Run external validation tools if available."""
    try:
        try:
            from .validate import validate_external as run_validation
        except ImportError:
            from ch10gen.validate import validate_external as run_validation
        import json
        
        filepath = Path(file)
        
        if not filepath.exists():
            click.echo(f"ERROR File not found: {filepath}", err=True)
            sys.exit(1)
        
        click.echo(f"Running external validation: {filepath}")
        
        results = run_validation(filepath, timeout_s=timeout_s)
        
        # Save or print results
        if out:
            output_path = Path(out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            click.echo(f"\n[SUCCESS] Results saved to {output_path}")
        else:
            print(json.dumps(results, indent=2))
        
        # Summary
        detected = results['external']['detected']
        click.echo(f"\nDetected tools:")
        for tool, available in detected.items():
            status = '[AVAILABLE]' if available else '[MISSING]'
            click.echo(f"  {status} {tool}")
        
        if results['external']['notes']:
            click.echo(f"\nNotes:")
            for note in results['external']['notes']:
                click.echo(f"  - {note}")
        
    except Exception as e:
        click.echo(f"ERROR Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--channel', type=click.Choice(['1553A', '1553B']), default='1553A',
              help='Channel to export')
@click.option('--out', type=click.Path(), required=True,
              help='Output PCAP file path')
@click.option('--max-messages', type=int, default=100000,
              help='Maximum messages to export')
def export_pcap(file, channel, out, max_messages):
    """Export CH10 1553 data to PCAP format."""
    try:
        try:
            from .pcap_export import export_pcap as do_export
        except ImportError:
            from pcap_export import export_pcap as do_export
        
        filepath = Path(file)
        output_path = Path(out)
        
        if not filepath.exists():
            click.echo(f"ERROR File not found: {filepath}", err=True)
            sys.exit(1)
        
        click.echo(f"Exporting to PCAP: {filepath}")
        click.echo(f"  Channel: {channel}")
        click.echo(f"  Output: {output_path}")
        
        # Use auto reader for best results
        count = do_export(filepath, output_path, channel, max_messages, reader='auto')
        
        if count == 0:
            click.echo(f"ERROR No messages found to export", err=True)
            sys.exit(3)
        
        click.echo(f"\n[SUCCESS] PCAP exported: {output_path}")
        click.echo(f"  Packets: {count:,}")
        click.echo(f"  Size: {output_path.stat().st_size:,} bytes")
        
    except Exception as e:
        click.echo(f"ERROR Error: {e}", err=True)
        sys.exit(1)





@cli.command()
def selftest():
    """Run self-test to verify installation."""
    import time
    import tempfile
    from pathlib import Path
    
    start_time = time.time()
    errors = []
    reader_used = 'unknown'
    
    try:
        # Test 1: Build a 10s file
        click.echo("SELFTEST: Building test file (10s)...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "selftest.c10"
            
            # Build file
            try:
                from .ch10_writer import write_ch10_file
                from .icd import load_icd
            except ImportError:
                from ch10gen.ch10_writer import write_ch10_file
                from ch10gen.icd import load_icd
            
            icd = load_icd(Path("icd/test_icd.yaml"))
            stats = write_ch10_file(
                output_path=test_file,
                scenario={'duration_s': 10, 'bus': {}},
                icd=icd,
                seed=42,
                writer_backend='irig106'
            )
            
            if stats['total_messages'] < 200:
                errors.append(f"Too few messages built: {stats['total_messages']}")
            else:
                click.echo(f"  OK Built file with {stats['total_messages']} messages")
            
            # Test 2: Inspect the file with auto reader
            click.echo("SELFTEST: Inspecting file (auto reader)...")
            try:
                from .inspector import write_timeline
            except ImportError:
                from ch10gen.inspector import write_timeline
            
            timeline_file = Path(tmpdir) / "timeline.jsonl"
            count = write_timeline(
                test_file, timeline_file, channel='auto', max_messages=1000, reader='auto'
            )
            
            # Check which reader was used from output
            if count > 0:
                with open(timeline_file, 'r') as f:
                    # Count actual lines
                    actual_count = sum(1 for line in f)
                    if actual_count != count:
                        errors.append(f"Count mismatch: reported {count}, actual {actual_count}")
            
            if count < 200:
                errors.append(f"Too few messages in timeline: {count} (expected >= 200)")
            else:
                click.echo(f"  OK Extracted {count} messages")
            
            # Test 3: Export PCAP
            click.echo("SELFTEST: Exporting PCAP...")
            try:
                from .pcap_export import export_pcap
            except ImportError:
                from ch10gen.pcap_export import export_pcap
            
            pcap_file = Path(tmpdir) / "test.pcap"
            pcap_count = export_pcap(
                test_file, pcap_file, channel='1553A', max_messages=1000, reader='auto'
            )
            
            if pcap_file.stat().st_size <= 24:
                errors.append(f"PCAP too small: {pcap_file.stat().st_size} bytes")
            else:
                pcap_size = pcap_file.stat().st_size
                click.echo(f"  OK PCAP exported: {pcap_size:,} bytes")
            
            # Final summary
            channel_used = 'A'  # Default for test
            if not errors:
                click.echo(f"\nSELFTEST OK | rows={count} pcap={pcap_size} channel={channel_used} reader={reader_used}")
    
    except Exception as e:
        errors.append(f"Exception: {e}")
    
    elapsed = time.time() - start_time
    
    # Report results
    if elapsed > 30:
        errors.append(f"Runtime too long: {elapsed:.1f}s (expected < 30s)")
    
    if errors:
        click.echo(f"\nERROR SELFTEST FAILED (elapsed: {elapsed:.1f}s):")
        for error in errors:
            click.echo(f"  - {error}")
        sys.exit(1)
    else:
        sys.exit(0)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
