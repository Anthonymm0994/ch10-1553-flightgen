#!/usr/bin/env python3
"""
XML to YAML Converter for MIL-STD-1553 ICDs

Converts XML files containing MIL-STD-1553 message definitions to the project's
YAML ICD format. Focuses on extracting Field information from the XML structure.

Usage:
    python xml_to_yaml_converter.py input.xml [output.yaml]
    
If no output file is specified, creates output based on input filename.
"""

import xml.etree.ElementTree as ET
import yaml
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class XMLToYAMLConverter:
    """Converts XML MIL-STD-1553 message definitions to YAML ICD format."""
    
    def __init__(self):
        self.messages = []
        self.message_types = {}
        
    def parse_xml(self, xml_file: str) -> bool:
        """
        Parse XML file and extract message definitions.
        
        Args:
            xml_file: Path to XML file
            
        Returns:
            True if parsing successful, False otherwise
        """
        try:
            logger.info(f"Parsing XML file: {xml_file}")
            
            # Parse XML with error handling for malformed files
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
            except ET.ParseError as e:
                logger.error(f"XML parsing error: {e}")
                # Try to parse with more lenient parser
                try:
                    with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    # Remove any invalid characters and try again
                    content = ''.join(char for char in content if ord(char) < 128)
                    root = ET.fromstring(content)
                except Exception as e2:
                    logger.error(f"Failed to parse XML even with lenient parser: {e2}")
                    return False
            
            # Extract message types first
            self._extract_message_types(root)
            
            # Extract messages
            self._extract_messages(root)
            
            logger.info(f"Successfully parsed {len(self.messages)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return False
    
    def _extract_message_types(self, root: ET.Element):
        """Extract message type definitions."""
        message_types_elem = root.find('.//Message_Types')
        if message_types_elem is not None:
            for msg_type_elem in message_types_elem.findall('.//Message_Type'):
                name = msg_type_elem.get('Name', '')
                sub_address = msg_type_elem.get('SubAddress', '')
                msg_type = msg_type_elem.get('Type', '')
                
                if name:
                    self.message_types[name] = {
                        'sub_address': sub_address,
                        'type': msg_type
                    }
                    logger.debug(f"Found message type: {name}")
    
    def _extract_messages(self, root: ET.Element):
        """Extract message definitions from MIL1553_IDD_Messages section."""
        messages_elem = root.find('.//MIL1553_IDD_Messages')
        if messages_elem is None:
            logger.warning("No MIL1553_IDD_Messages section found")
            return
        
        for msg_elem in messages_elem.findall('.//Message'):
            try:
                message = self._parse_message_element(msg_elem)
                if message:
                    self.messages.append(message)
            except Exception as e:
                logger.warning(f"Failed to parse message element: {e}")
                continue
    
    def _parse_message_element(self, msg_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse individual message element."""
        try:
            # Extract basic message attributes
            name = msg_elem.get('Name', 'Unknown')
            sub_address = msg_elem.get('SubAddress', '0')
            msg_type = msg_elem.get('Type', '')
            multiplier = msg_elem.get('Multiplier', '1')
            message_length = msg_elem.get('MessageLength', '1')
            offset = msg_elem.get('Offset', '0')
            
            # Parse fields
            fields = self._parse_fields(msg_elem)
            
            if not fields:
                logger.warning(f"No fields found for message: {name}")
                return None
            
            # Create message structure
            message = {
                'name': name,
                'sub_address': int(sub_address) if sub_address.isdigit() else 0,
                'type': msg_type if msg_type else 'data',
                'multiplier': int(multiplier) if multiplier.isdigit() else 1,
                'message_length': int(message_length) if message_length.isdigit() else 1,
                'offset': int(offset) if offset.isdigit() else 0,
                'words': self._convert_fields_to_words(fields)
            }
            
            logger.debug(f"Parsed message: {name} with {len(fields)} fields")
            return message
            
        except Exception as e:
            logger.warning(f"Error parsing message element: {e}")
            return None
    
    def _parse_fields(self, msg_elem: ET.Element) -> List[Dict[str, Any]]:
        """Parse Fields section of a message."""
        fields = []
        fields_elem = msg_elem.find('.//Fields')
        
        if fields_elem is None:
            return fields
        
        for field_elem in fields_elem.findall('.//Field'):
            try:
                field = {
                    'name': field_elem.get('Name', 'Unknown'),
                    'word': int(field_elem.get('Word', '0')),
                    'mask': field_elem.get('Mask', ''),
                    'shift': field_elem.get('Shift', '')
                }
                
                # Convert mask and shift to integers if possible
                if field['mask'] and field['mask'].isdigit():
                    field['mask'] = int(field['mask'])
                if field['shift'] and field['shift'].isdigit():
                    field['shift'] = int(field['shift'])
                
                fields.append(field)
                
            except Exception as e:
                logger.warning(f"Error parsing field: {e}")
                continue
        
        return fields
    
    def _convert_fields_to_words(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert field definitions to word format for YAML."""
        words = {}
        
        for field in fields:
            word_num = field['word']
            
            if word_num not in words:
                words[word_num] = {
                    'type': 'u16',  # Default type
                    'fields': []
                }
            
            # Create field definition
            field_def = {
                'name': field['name'],
                'type': 'u16'  # Default type, could be enhanced with type detection
            }
            
            # Add mask and shift if present
            if field.get('mask'):
                field_def['mask'] = field['mask']
            if field.get('shift'):
                field_def['shift'] = field['shift']
            
            words[word_num]['fields'].append(field_def)
        
        # Convert to list format
        word_list = []
        for word_num in sorted(words.keys()):
            word_data = words[word_num]
            word_data['word'] = word_num
            word_list.append(word_data)
        
        return word_list
    
    def generate_yaml(self, output_file: str = None) -> bool:
        """
        Generate YAML output file.
        
        Args:
            output_file: Output file path (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.messages:
                logger.error("No messages to convert")
                return False
            
            # Create YAML structure
            yaml_data = {
                'name': 'Converted from XML',
                'bus': 'A',  # Default bus
                'description': f'Converted from XML with {len(self.messages)} messages',
                'messages': self.messages
            }
            
            # Determine output filename
            if not output_file:
                output_file = 'converted_icd.yaml'
            
            # Write YAML file
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Successfully generated YAML file: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating YAML: {e}")
            return False
    
    def print_summary(self):
        """Print summary of conversion results."""
        print(f"\nConversion Summary:")
        print(f"  Messages processed: {len(self.messages)}")
        print(f"  Message types found: {len(self.message_types)}")
        
        if self.messages:
            print(f"\nSample messages:")
            for i, msg in enumerate(self.messages[:3]):  # Show first 3
                print(f"  {i+1}. {msg['name']} (SubAddress: {msg['sub_address']}, Words: {len(msg['words'])})")
            
            if len(self.messages) > 3:
                print(f"  ... and {len(self.messages) - 3} more")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python xml_to_yaml_converter.py input.xml [output.yaml]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    # Create converter and process
    converter = XMLToYAMLConverter()
    
    if converter.parse_xml(input_file):
        if converter.generate_yaml(output_file):
            converter.print_summary()
            print(f"\nConversion completed successfully!")
        else:
            print("Error: Failed to generate YAML file")
            sys.exit(1)
    else:
        print("Error: Failed to parse XML file")
        sys.exit(1)


if __name__ == "__main__":
    main()
