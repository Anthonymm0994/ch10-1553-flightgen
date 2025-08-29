#!/usr/bin/env python3
"""
YAML Examples Validation Script

This script validates all YAML examples in the documentation to ensure they are
syntactically correct and follow the expected schema structure.

Usage:
    python scripts/validate_yaml_examples.py

The script will:
1. Parse all YAML examples from the documentation
2. Validate basic YAML syntax
3. Check for required fields and structure
4. Report any validation errors
"""

import yaml
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class YAMLValidator:
    """Validates YAML examples against expected schemas."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.examples_tested = 0
        self.examples_passed = 0
        
    def validate_yaml_syntax(self, yaml_text: str, example_name: str) -> bool:
        """Validate basic YAML syntax."""
        try:
            yaml.safe_load(yaml_text)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"{example_name}: YAML syntax error - {e}")
            return False
    
    def validate_scenario_structure(self, data: Dict[str, Any], example_name: str) -> bool:
        """Validate scenario YAML structure."""
        required_fields = ['name', 'duration_s', 'profile']
        
        for field in required_fields:
            if field not in data:
                self.errors.append(f"{example_name}: Missing required field '{field}'")
                return False
        
        # Validate profile structure
        profile = data.get('profile', {})
        if 'segments' not in profile:
            self.errors.append(f"{example_name}: Profile missing 'segments' field")
            return False
        
        # Validate segments
        segments = profile.get('segments', [])
        if not segments:
            self.errors.append(f"{example_name}: Profile has no segments")
            return False
        
        # Check segment coverage
        total_duration = data.get('duration_s', 0)
        segment_coverage = 0
        
        for i, segment in enumerate(segments):
            segment_name = segment.get('name', f'segment_{i}')
            
            # Check required segment fields
            required_segment_fields = ['start_time_s', 'end_time_s', 'altitude_ft', 'airspeed_kt', 'heading_deg']
            for field in required_segment_fields:
                if field not in segment:
                    self.errors.append(f"{example_name}: Segment '{segment_name}' missing '{field}'")
                    return False
            
            # Check timing
            start_time = segment.get('start_time_s', 0)
            end_time = segment.get('end_time_s', 0)
            
            if start_time < 0 or end_time < 0:
                self.errors.append(f"{example_name}: Segment '{segment_name}' has negative timing")
                return False
            
            if start_time >= end_time:
                self.errors.append(f"{example_name}: Segment '{segment_name}' has invalid time range")
                return False
            
            segment_coverage += (end_time - start_time)
        
        # Check if segments cover the full duration (allow small tolerance)
        if abs(segment_coverage - total_duration) > 0.1:
            self.warnings.append(f"{example_name}: Segment coverage ({segment_coverage}s) doesn't match duration ({total_duration}s)")
        
        return True
    
    def validate_icd_structure(self, data: Dict[str, Any], example_name: str) -> bool:
        """Validate ICD YAML structure."""
        required_fields = ['bus', 'messages']
        
        for field in required_fields:
            if field not in data:
                self.errors.append(f"{example_name}: Missing required field '{field}'")
                return False
        
        # Validate bus field
        bus = data.get('bus')
        if bus not in ['A', 'B']:
            self.errors.append(f"{example_name}: Invalid bus value '{bus}' (must be 'A' or 'B')")
            return False
        
        # Validate messages
        messages = data.get('messages', [])
        if not messages:
            self.errors.append(f"{example_name}: ICD has no messages")
            return False
        
        for i, message in enumerate(messages):
            message_name = message.get('name', f'message_{i}')
            
            # Check required message fields
            required_message_fields = ['rate_hz', 'rt', 'tr', 'sa', 'wc', 'words']
            for field in required_message_fields:
                if field not in message:
                    self.errors.append(f"{example_name}: Message '{message_name}' missing '{field}'")
                    return False
            
            # Validate RT and SA ranges
            rt = message.get('rt')
            if not (1 <= rt <= 30):
                self.errors.append(f"{example_name}: Message '{message_name}' has invalid RT {rt} (must be 1-30)")
                return False
            
            sa = message.get('sa')
            if not (1 <= sa <= 31):
                self.errors.append(f"{example_name}: Message '{message_name}' has invalid SA {sa} (must be 1-31)")
                return False
            
            # Validate words
            words = message.get('words', [])
            wc = message.get('wc', 0)
            
            if len(words) != wc:
                self.errors.append(f"{example_name}: Message '{message_name}' word count mismatch: declared {wc}, actual {len(words)}")
                return False
            
            # Validate each word
            for j, word in enumerate(words):
                word_name = word.get('name', f'word_{j}')
                
                # Check encoding
                if 'encode' not in word:
                    self.errors.append(f"{example_name}: Word '{word_name}' in message '{message_name}' missing 'encode'")
                    return False
                
                # Check that either src or const is specified (but not both)
                has_src = 'src' in word
                has_const = 'const' in word
                
                if not (has_src or has_const):
                    self.errors.append(f"{example_name}: Word '{word_name}' in message '{message_name}' must have either 'src' or 'const'")
                    return False
                
                if has_src and has_const:
                    self.errors.append(f"{example_name}: Word '{word_name}' in message '{message_name}' cannot have both 'src' and 'const'")
                    return False
                
                # Check float32_split specific requirements
                if word.get('encode') == 'float32_split':
                    if 'word_order' not in word:
                        self.errors.append(f"{example_name}: Word '{word_name}' in message '{message_name}' missing 'word_order' for float32_split encoding")
                        return False
        
        return True
    

    
    def validate_config_structure(self, data: Dict[str, Any], example_name: str) -> bool:
        """Validate configuration YAML structure."""
        config = data.get('config', {})
        if not config:
            return True  # Config is optional
        
        if not isinstance(config, dict):
            self.errors.append(f"{example_name}: Config section must be a dictionary")
            return False
        
        # Validate timing section
        timing = config.get('timing', {})
        if timing:
            if 'pct_jitter' in timing:
                jitter = timing['pct_jitter']
                if not isinstance(jitter, (int, float)) or jitter < 0 or jitter > 100:
                    self.errors.append(f"{example_name}: Config timing 'pct_jitter' value {jitter} out of range [0, 100]")
                    return False
        
        # Validate writer section
        writer = config.get('writer', {})
        if writer:
            if 'backend' in writer:
                backend = writer['backend']
                valid_backends = ['pyc10', 'irig106']
                if backend not in valid_backends:
                    self.errors.append(f"{example_name}: Config writer 'backend' '{backend}' not in {valid_backends}")
                    return False
        
        return True
    
    def extract_yaml_examples(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract YAML examples from markdown file."""
        examples = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return examples
        
        # Find YAML code blocks
        yaml_pattern = r'```yaml\s*\n(.*?)\n```'
        matches = re.findall(yaml_pattern, content, re.DOTALL)
        
        for i, match in enumerate(matches):
            example_name = f"{file_path.stem}_example_{i+1}"
            yaml_text = match.strip()
            
            # Handle multi-document YAML (separated by ---)
            if '---' in yaml_text:
                # Split into individual documents
                documents = yaml_text.split('---')
                for j, doc in enumerate(documents):
                    doc = doc.strip()
                    if doc:  # Skip empty documents
                        doc_name = f"{example_name}_doc_{j+1}"
                        examples.append((doc_name, doc))
            else:
                examples.append((example_name, yaml_text))
        
        return examples
    
    def validate_example(self, example_name: str, yaml_text: str) -> bool:
        """Validate a single YAML example."""
        self.examples_tested += 1
        
        # Basic YAML syntax check
        if not self.validate_yaml_syntax(yaml_text, example_name):
            return False
        
        # Parse the YAML
        try:
            data = yaml.safe_load(yaml_text)
        except Exception as e:
            self.errors.append(f"{example_name}: Failed to parse YAML: {e}")
            return False
        
        # Determine the type and validate accordingly
        if 'messages' in data:
            # This is an ICD
            if not self.validate_icd_structure(data, example_name):
                return False
        elif 'profile' in data:
            # This is a scenario
            if not self.validate_scenario_structure(data, example_name):
                return False
            
            
            
            if not self.validate_config_structure(data, example_name):
                return False
        else:
            self.warnings.append(f"{example_name}: Unknown YAML structure type")
        
        self.examples_passed += 1
        return True
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate all examples in a markdown file."""
        logger.info(f"Validating examples in {file_path}")
        
        examples = self.extract_yaml_examples(file_path)
        if not examples:
            logger.warning(f"No YAML examples found in {file_path}")
            return True
        
        logger.info(f"Found {len(examples)} examples in {file_path}")
        
        all_valid = True
        for example_name, yaml_text in examples:
            if not self.validate_example(example_name, yaml_text):
                all_valid = False
        
        return all_valid
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("YAML EXAMPLES VALIDATION SUMMARY")
        print("="*60)
        
        print(f"Examples tested: {self.examples_tested}")
        print(f"Examples passed: {self.examples_passed}")
        print(f"Examples failed: {self.examples_tested - self.examples_passed}")
        
        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")
        
        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        if not self.errors:
            print("\n✅ All examples passed validation!")
            return True
        else:
            print(f"\n❌ {len(self.errors)} validation errors found")
            return False

def main():
    """Main validation function."""
    # Find documentation files
    docs_dir = Path("docs")
    if not docs_dir.exists():
        logger.error("docs/ directory not found")
        return 1
    
    # Files to validate
    files_to_validate = [
        docs_dir / "YAML_REFERENCE.md",
        docs_dir / "YAML_EXAMPLES.md"
    ]
    
    validator = YAMLValidator()
    
    for file_path in files_to_validate:
        if file_path.exists():
            if not validator.validate_file(file_path):
                logger.error(f"Validation failed for {file_path}")
        else:
            logger.warning(f"File not found: {file_path}")
    
    # Print summary
    success = validator.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
