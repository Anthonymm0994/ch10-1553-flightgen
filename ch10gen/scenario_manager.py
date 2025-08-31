"""
Scenario manager for handling field references and data generation.
Supports references within word, across words, and across messages.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from .data_generators import DataGeneratorManager, GeneratorFactory


class FieldReferenceResolver:
    """Resolves field references across messages, words, and fields."""
    
    @staticmethod
    def parse_reference(reference: str, current_message: str, current_word: int) -> Tuple[str, int, str]:
        """
        Parse a field reference and return (message, word, field).
        
        Reference formats:
        - "field1" -> same word
        - "word2.field1" -> same message, different word
        - "Message Name.field1" -> different message (searches all words)
        - "Message Name.word2.field1" -> specific message, word, field
        
        Args:
            reference: Field reference string
            current_message: Current message name
            current_word: Current word index
            
        Returns:
            Tuple of (message_name, word_index, field_name)
        """
        parts = reference.split('.')
        
        if len(parts) == 1:
            # Just field name - same word
            return (current_message, current_word, parts[0])
        
        elif len(parts) == 2:
            # Could be "word.field" or "Message.field"
            # Check if first part is a word reference (starts with "word")
            if parts[0].lower().startswith('word'):
                # Same message, different word
                try:
                    word_num = int(parts[0].replace('word', '').strip())
                    return (current_message, word_num, parts[1])
                except ValueError:
                    # Not a word number, treat as message name
                    return (parts[0], -1, parts[1])  # -1 means search all words
            else:
                # Different message
                return (parts[0], -1, parts[1])
        
        elif len(parts) >= 3:
            # Full path: Message.word.field or Message with spaces.word.field
            # Join all but last two as message name (handles spaces)
            if parts[-2].lower().startswith('word'):
                # Has word specification
                message_name = '.'.join(parts[:-2])
                try:
                    word_num = int(parts[-2].replace('word', '').strip())
                    field_name = parts[-1]
                    return (message_name, word_num, field_name)
                except ValueError:
                    # Not a valid word number, treat last part as field
                    message_name = '.'.join(parts[:-1])
                    return (message_name, -1, parts[-1])
            else:
                # No word specification
                message_name = '.'.join(parts[:-1])
                return (message_name, -1, parts[-1])
        
        else:
            raise ValueError(f"Invalid field reference: {reference}")
    
    @staticmethod
    def find_field_value(icd: Any, message_name: str, word_index: int, 
                        field_name: str, computed_values: Dict) -> Optional[Any]:
        """
        Find a field value from computed values.
        
        Args:
            icd: ICD definition
            message_name: Message name to search
            word_index: Word index (-1 for any)
            field_name: Field name to find
            computed_values: Already computed values
            
        Returns:
            Field value if found, None otherwise
        """
        # Check computed values
        if message_name in computed_values:
            msg_values = computed_values[message_name]
            
            if word_index >= 0:
                # Specific word requested
                word_key = f"word{word_index}"
                if word_key in msg_values and field_name in msg_values[word_key]:
                    return msg_values[word_key][field_name]
            else:
                # Search all words
                for word_key, word_values in msg_values.items():
                    if isinstance(word_values, dict) and field_name in word_values:
                        return word_values[field_name]
                
                # Also check message-level fields
                if field_name in msg_values:
                    return msg_values[field_name]
        
        return None


class ScenarioManager:
    """Manages scenario-based data generation with field references."""
    
    def __init__(self, scenario: Dict[str, Any], icd: Any):
        """
        Initialize scenario manager.
        
        Args:
            scenario: Scenario configuration
            icd: ICD definition
        """
        self.scenario = scenario
        self.icd = icd
        self.generator_manager = DataGeneratorManager()
        self.resolver = FieldReferenceResolver()
        self.computed_values = {}
        
        # Load generators from scenario
        self._load_generators()
    
    def _load_generators(self):
        """Load all generators from scenario configuration."""
        # Global default - check both 'config.default_mode' and 'defaults.data_mode'
        default_mode = (self.scenario.get('config', {}).get('default_mode') or 
                       self.scenario.get('defaults', {}).get('data_mode') or 
                       'random')
        
        # Process each message configuration
        messages_config = self.scenario.get('messages', {})
        
        for message in self.icd.messages:
            message_name = message.name
            message_config = messages_config.get(message_name, {})
            
            # Message-level default
            msg_default_mode = message_config.get('default_mode', default_mode)
            msg_default_config = message_config.get('default_config', {})
            
            # Process fields
            fields_config = message_config.get('fields', {})
            
            # Process each word
            for word_idx, word in enumerate(message.words):
                # Handle different word formats
                if hasattr(word, 'fields') and word.fields:
                    # Word with multiple fields
                    for field in word.fields:
                        self._create_field_generator(
                            message_name, word_idx, field.name,
                            fields_config.get(field.name),
                            msg_default_mode, msg_default_config
                        )
                else:
                    # Single field word
                    field_name = word.name if hasattr(word, 'name') else f"word{word_idx}"
                    self._create_field_generator(
                        message_name, word_idx, field_name,
                        fields_config.get(field_name),
                        msg_default_mode, msg_default_config
                    )
    
    def _create_field_generator(self, message_name: str, word_idx: int, 
                               field_name: str, field_config: Optional[Dict],
                               default_mode: str, default_config: Dict):
        """Create generator for a specific field."""
        # Build field path
        field_path = f"{message_name}.word{word_idx}.{field_name}"
        
        if field_config and isinstance(field_config, dict):
            # Use field-specific configuration
            config = field_config.copy()
            if 'mode' not in config:
                config['mode'] = default_mode
        else:
            # Use default configuration
            config = default_config.copy()
            config['mode'] = default_mode
        
        # Create generator
        generator = GeneratorFactory.create(config)
        self.generator_manager.generators[field_path] = generator
    
    def generate_message_data(self, message_name: str, message_def: Any) -> List[int]:
        """
        Generate data for all fields in a message.
        
        Args:
            message_name: Name of the message
            message_def: Message definition from ICD
            
        Returns:
            List of 16-bit words with generated data
        """
        # First pass: collect all field values (non-expressions)
        message_values = {}
        for word_idx, word_def in enumerate(message_def.words):
            if hasattr(word_def, 'fields') and word_def.fields:
                for field in word_def.fields:
                    field_path = f"{message_name}.word{word_idx}.{field.name}"
                    if field_path in self.generator_manager.generators:
                        gen = self.generator_manager.generators[field_path]
                        if not hasattr(gen, 'formula'):  # Not an expression
                            value = self._generate_field_value(message_name, word_idx, field.name, {})
                            if f"word{word_idx}" not in message_values:
                                message_values[f"word{word_idx}"] = {}
                            message_values[f"word{word_idx}"][field.name] = value
                            message_values[field.name] = value  # Also store at message level
            else:
                field_name = word_def.name if hasattr(word_def, 'name') else f"word{word_idx}"
                field_path = f"{message_name}.word{word_idx}.{field_name}"
                if field_path in self.generator_manager.generators:
                    gen = self.generator_manager.generators[field_path]
                    if not hasattr(gen, 'formula'):  # Not an expression
                        value = self._generate_field_value(message_name, word_idx, field_name, {})
                        if f"word{word_idx}" not in message_values:
                            message_values[f"word{word_idx}"] = {}
                        message_values[f"word{word_idx}"][field_name] = value
                        message_values[field_name] = value  # Also store at message level
        
        # Second pass: generate actual word data with expressions
        words_data = []
        for word_idx, word_def in enumerate(message_def.words):
            word_value = 0
            word_values = {}
            
            # Check if word has multiple fields (bitfields)
            if hasattr(word_def, 'fields') and word_def.fields:
                # Process each bitfield
                for field in word_def.fields:
                    # Generate value for this field
                    field_value = self._generate_field_value(
                        message_name, word_idx, field.name, message_values
                    )
                    
                    # Apply mask and shift if present
                    if hasattr(field, 'mask') and hasattr(field, 'shift'):
                        # Ensure value fits in mask
                        mask_bits = bin(field.mask).count('1')
                        max_val = (1 << mask_bits) - 1
                        field_value = int(field_value) & max_val
                        
                        # Apply to word
                        word_value |= (field_value << field.shift)
                    else:
                        word_value = int(field_value) & 0xFFFF
                    
                    word_values[field.name] = field_value
            else:
                # Single field word
                field_name = word_def.name if hasattr(word_def, 'name') else f"word{word_idx}"
                field_value = self._generate_field_value(
                    message_name, word_idx, field_name, message_values
                )
                word_value = int(field_value) & 0xFFFF
                word_values[field_name] = field_value
            
            words_data.append(word_value)
            message_values[f"word{word_idx}"] = word_values
        
        # Store computed values for cross-references
        self.computed_values[message_name] = message_values
        
        return words_data
    
    def _generate_field_value(self, message_name: str, word_idx: int, 
                             field_name: str, current_message_values: Dict) -> float:
        """Generate value for a specific field."""
        field_path = f"{message_name}.word{word_idx}.{field_name}"
        
        # Check if we have a generator for this field
        if field_path not in self.generator_manager.generators:
            # Use default random generator
            self.generator_manager.generators[field_path] = GeneratorFactory.create({'mode': 'random'})
        
        # Get generator
        generator = self.generator_manager.generators[field_path]
        
        # Handle expression generators specially
        if hasattr(generator, 'formula'):
            # Build context for expression evaluation
            context = self._build_expression_context(
                message_name, word_idx, field_name, current_message_values
            )
            return self._evaluate_expression(generator.formula, context)
        else:
            # Use standard generator
            from .data_generators import GenerationContext
            context = GenerationContext(
                time_seconds=self.generator_manager.get_elapsed_time(),
                message_count=self.generator_manager.get_message_count(message_name),
                message_name=message_name,
                field_name=field_name,
                field_values=current_message_values,
                all_values=self.computed_values,
                icd=self.icd
            )
            return generator.generate(context)
    
    def _build_expression_context(self, message_name: str, word_idx: int,
                                 field_name: str, current_message_values: Dict) -> Dict:
        """Build context for expression evaluation."""
        import math
        import random
        
        context = {
            # Math functions
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'abs': abs,
            'min': min,
            'max': max,
            'sqrt': math.sqrt,
            'pow': pow,
            'exp': math.exp,
            'log': math.log,
            'floor': math.floor,
            'ceil': math.ceil,
            'round': round,
            'int': int,
            'float': float,
            
            # Random functions
            'random': lambda min_val=0, max_val=1: random.uniform(min_val, max_val),
            'random_int': lambda min_val=0, max_val=100: random.randint(min_val, max_val),
            
            # Time and counters
            'time': self.generator_manager.get_elapsed_time(),
            'message_count': self.generator_manager.get_message_count(message_name),
        }
        
        # Add current message values
        context.update(current_message_values)
        
        # Add all computed values for cross-references
        for msg_name, msg_values in self.computed_values.items():
            # Handle spaces in names
            safe_name = msg_name.replace(' ', '_')
            context[safe_name] = msg_values
        
        return context
    
    def _evaluate_expression(self, formula: str, context: Dict) -> float:
        """
        Evaluate an expression with field references.
        
        Args:
            formula: Expression string
            context: Evaluation context
            
        Returns:
            Evaluated value
        """
        # First, resolve field references in the formula
        resolved_formula = self._resolve_references_in_formula(formula, context)
        
        # Now evaluate the resolved formula
        try:
            result = eval(resolved_formula, {"__builtins__": {}}, context)
            return float(result)
        except Exception as e:
            raise ValueError(f"Error evaluating expression '{formula}': {e}")
    
    def _resolve_references_in_formula(self, formula: str, context: Dict) -> str:
        """Resolve field references in formula to actual values."""
        # This is a simplified version - a full implementation would
        # properly parse and replace field references
        
        # For now, return formula as-is if it doesn't contain references
        # Full implementation would parse "Message Name.field" references
        return formula
