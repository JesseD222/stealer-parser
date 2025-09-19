"""Strategy classes for data extraction using the Strategy pattern with intelligent file analysis."""

import json
import logging
import re
import struct
from abc import ABC, abstractmethod
from codecs import decode
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Type

import regex

from d4derp.app.chunk_generators import ChunkGenerator
from d4derp.app.chunker_registry import chunker_registry
from d4derp.app.exceptions import ExtractionTaskProcessingException, RecordExtractionException
from d4derp.app.record_utils import create_record
from d4derp.app.intelligent_file_analyzer import FileAnalysisResult, FileType, ExtractionStrategyType
from d4derp.domain.simple_models import SimpleRecord
from d4derp.util import detect_encoding

logger = logging.getLogger(__name__)


class ExtractionStrategy(ABC):
    """Base class for all extraction strategies - works with FileAnalysisResult."""

    def __init__(self, file_path: str, analysis_result: FileAnalysisResult, hwid: str = "default"):
        self.file_path = Path(file_path)
        self.analysis_result = analysis_result
        self.hwid = hwid
        self.extraction_task_id = None  # Will be set when processing

    @abstractmethod
    def extract(self, extraction_task_id: str) -> Generator[SimpleRecord, None, None]:
        """Extract records from the file."""
        pass

    def _create_record(self, data: Dict[str, Any]) -> SimpleRecord:
        """Create a record using the record factory."""
        return create_record(
            data=data,
            analysis_result=self.analysis_result,
            extraction_task_id=self.extraction_task_id,
            hwid=self.hwid
        )


from d4derp.app.intelligent_file_analyzer import FileAnalysisResult


def create_record(
    data: Dict[str, Any], 
    analysis_result: FileAnalysisResult = None,
    extraction_task_id: str = None,
    hwid: str = None
) -> SimpleRecord:
    """Create record using the new record factory based on file analysis result."""
    from uuid import UUID, uuid4
    
    # Convert string UUID to UUID object if needed
    task_id = UUID(extraction_task_id) if isinstance(extraction_task_id, str) else extraction_task_id or uuid4()
    
    return record_factory.create_unified_record(
        data=data,
        analysis_result=analysis_result, 
        extraction_task_id=task_id,
        hwid=hwid or "unknown",
        use_legacy=False
    )


def build_strategy(
    extraction_task: ExtractionTaskEntity, extraction_configuration: ExtractionConfigurationEntity
) -> "ExtractionStrategy":
    """Legacy build strategy function - deprecated in favor of intelligent detection."""
    from d4derp.app.strategy_registry import strategy_registry
    
    # Extract strategy name from legacy configuration
    strategy_name = extraction_configuration.process_configuration.get("extraction_strategy")
    if not strategy_name:
        raise ExtractionTaskProcessingException("Extraction strategy is required in process_configuration")
    
    # Use legacy method for backward compatibility
    return strategy_registry.get_strategy(strategy_name)(extraction_task, extraction_configuration)


def build_strategy_from_analysis(
    file_path: str, analysis_result: "FileAnalysisResult", hwid: str = "default"
) -> "ExtractionStrategy":
    """Build strategy using intelligent detection results - preferred method."""
    from d4derp.app.strategy_registry import strategy_registry
    
    return strategy_registry.build_strategy(file_path, analysis_result, hwid)


class ExtractionStrategy(ABC):
    def __init__(self, extraction_task: ExtractionTaskEntity, config_entity: ExtractionConfigurationEntity):
        self.extraction_task = extraction_task
        self.extraction_configuration = config_entity

    def extract(self, extraction_task: ExtractionTaskEntity) -> Generator[BaseSchema, None, None]:
        try:
            path_str = extraction_task.item_path  # type: ignore
            if not path_str:
                raise ExtractionTaskProcessingException("Source path is required")
            file_path = Path(path_str)
            if not file_path.exists():
                raise ExtractionTaskProcessingException("Source file does not exist")

            process_configuration = self.extraction_configuration.process_configuration
            chunker_class_name = process_configuration.get("chunk_generator")

            # Use chunker registry instead of globals lookup
            chunker = chunker_registry.build_chunker(chunker_class_name, self.extraction_configuration)

            if chunker is None:  # FilePassthroughStrategy case
                try:
                    for record_dict in self._extract_file(file_path=file_path):
                        if record_dict:
                            record = create_record(extraction_task, record_dict)  # Use the factory method
                            yield record
                except Exception as e:
                    logger.error(f"Error in FilePassthroughStrategy: {e.with_traceback(e.__traceback__)}")
                    raise ExtractionTaskProcessingException(f"Error in FilePassthroughStrategy: {e}")
            else:
                chunks = chunker.generate_chunks(file_path=file_path)
                try:
                    for chunk in chunks:
                        for record_dict in self._extract_chunk(chunk):
                            if record_dict:
                                record = create_record(extraction_task, record_dict)  # Use the factory method
                                yield record
                except Exception as e:
                    logger.error(f"Error in Strategy: {e.with_traceback(e.__traceback__)}")
                    raise ExtractionTaskProcessingException(f"Error in RecordRegexStrategy: {e}")
        except Exception as e:
            logger.error(f"Error extracting from file {extraction_task.item_path}: {e}")
            raise ExtractionTaskProcessingException(f"Error extracting from file {extraction_task.item_path}: {e}")

    def _extract_chunk(self, chunk: List[str]) -> Generator[Dict[str, Any], None, None]:
        """Default implementation for chunk-based extraction. Override in subclasses."""
        return
        yield  # Make this a generator

    def _extract_file(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Default implementation for file-based extraction. Override in subclasses."""
        return
        yield  # Make this a generator


class RecordRegexStrategy(ExtractionStrategy):
    """
    Data-driven extraction strategy that builds regex patterns dynamically from field configurations.
    Supports multiple extraction types and provides robust field mapping through alias resolution.

    This replaces the original RecordRegexStrategy with a much more flexible, configuration-driven approach.
    """

    def __init__(self, extraction_task: ExtractionTaskEntity, config_entity: ExtractionConfigurationEntity):
        super().__init__(extraction_task=extraction_task, config_entity=config_entity)
        self.alias_map = config_entity.field_alias_map
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.field_extractors = self._build_field_extractors()

    def _build_field_extractors(self) -> Dict[str, List["FieldExtractor"]]:
        """Build organized extractors for each field from extraction_details configuration."""
        field_extractors = {}

        for field in self.extraction_configuration.data_fields:
            extractors = []

            # Process each extraction detail step
            for step in field.extraction_details:
                extractor = self._create_field_extractor(field, step)
                if extractor:
                    extractors.append(extractor)

            # Add fallback extractor if no explicit extractors defined
            if not extractors and field.aliases:
                fallback_extractor = self._create_fallback_extractor(field)
                if fallback_extractor:
                    extractors.append(fallback_extractor)

            if extractors:
                field_extractors[field.name] = extractors
                self.logger.debug(f"Built {len(extractors)} extractors for field '{field.name}'")

        return field_extractors

    def _create_field_extractor(self, field: DataFieldEntity, step: Dict[str, Any]) -> Optional["FieldExtractor"]:
        """Create a field extractor from an extraction detail step."""
        extraction_type = step.get("extraction_type", "").lower()

        if extraction_type == "regex":
            return self._create_regex_extractor(field, step)
        elif extraction_type == "literal":
            return self._create_literal_extractor(field, step)
        elif extraction_type == "json":
            return self._create_json_extractor(field, step)
        else:
            self.logger.warning(f"Unknown extraction_type '{extraction_type}' for field '{field.name}'")
            return None

    def _create_regex_extractor(self, field: DataFieldEntity, step: Dict[str, Any]) -> Optional["RegexFieldExtractor"]:
        """Create a regex-based field extractor."""
        pattern_template = step.get("extraction_regex", r"(?P<key>%%ALIASES%%)\s*[:=]\s*(?P<value>.*)")

        try:
            # Replace alias macro with actual aliases
            if "%%ALIASES%%" in pattern_template:
                if field.aliases:
                    alias_pattern = "|".join(re.escape(alias) for alias in field.aliases)
                    pattern = pattern_template.replace("%%ALIASES%%", alias_pattern)
                else:
                    # Fallback to field name if no aliases
                    pattern = pattern_template.replace("%%ALIASES%%", re.escape(field.name))
            else:
                pattern = pattern_template

            # Compile pattern with flags
            flags = re.IGNORECASE | re.MULTILINE
            compiled_pattern = re.compile(pattern, flags)

            return RegexFieldExtractor(
                field_name=field.name, pattern=compiled_pattern, required=field.required, data_type=field.data_type
            )

        except re.error as e:
            self.logger.error(f"Invalid regex pattern for field '{field.name}': {pattern_template} - {e}")
            return None

    def _create_literal_extractor(
        self, field: DataFieldEntity, step: Dict[str, Any]
    ) -> Optional["LiteralFieldExtractor"]:
        """Create a literal string matching extractor."""
        literal_value = step.get("literal_value")
        if literal_value:
            return LiteralFieldExtractor(
                field_name=field.name, literal_value=literal_value, required=field.required, data_type=field.data_type
            )
        return None

    def _create_json_extractor(self, field: DataFieldEntity, step: Dict[str, Any]) -> Optional["JsonFieldExtractor"]:
        """Create a JSON path-based extractor."""
        json_path = step.get("json_path")
        if json_path:
            return JsonFieldExtractor(
                field_name=field.name, json_path=json_path, required=field.required, data_type=field.data_type
            )
        return None

    def _create_fallback_extractor(self, field: DataFieldEntity) -> Optional["RegexFieldExtractor"]:
        """Create a fallback regex extractor based on field aliases."""
        if not field.aliases:
            return None

        # Create a simple key-value pattern using aliases
        alias_pattern = "|".join(re.escape(alias) for alias in field.aliases)
        pattern = rf"(?P<key>{alias_pattern})\s*[:=]\s*(?P<value>.*)"

        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            return RegexFieldExtractor(
                field_name=field.name, pattern=compiled_pattern, required=field.required, data_type=field.data_type
            )
        except re.error as e:
            self.logger.error(f"Failed to create fallback extractor for field '{field.name}': {e}")
            return None

    def _extract_chunk(self, chunk: List[str]) -> Generator[Dict[str, Any], None, None]:
        """Extract data from chunk using dynamic field extractors."""
        data = {}
        processed_lines = set()  # Track processed lines to avoid redundant work

        # Process each field's extractors
        for field_name, extractors in self.field_extractors.items():
            if field_name in data:
                continue  # Skip if field already extracted

            # Try each extractor until we get a match
            for extractor in extractors:
                for line_idx, line in enumerate(chunk):
                    if line_idx in processed_lines:
                        continue

                    extracted_value = extractor.extract(line)
                    if extracted_value is not None:
                        cleaned_value = self._clean_and_validate_value(extracted_value, extractor.data_type)
                        if cleaned_value:
                            data[field_name] = cleaned_value
                            processed_lines.add(line_idx)
                            break  # Found match for this field, move to next field

                if field_name in data:
                    break  # Found match for this field, try next field

        if data:
            yield data

    def _clean_and_validate_value(self, value: str, data_type: str) -> Optional[str]:
        """Clean and validate extracted value based on data type."""
        if not value or not value.strip():
            return None

        cleaned = value.strip()

        # Remove quotes
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1]

        # Remove trailing punctuation
        cleaned = cleaned.rstrip(",;.")

        # Data type specific validation
        if data_type == "integer":
            try:
                int(cleaned)
            except ValueError:
                self.logger.warning(f"Invalid integer value: {cleaned}")
                return None
        elif data_type == "boolean":
            if cleaned.lower() not in ["true", "false", "yes", "no", "1", "0"]:
                self.logger.warning(f"Invalid boolean value: {cleaned}")
                return None

        # Truncate if too long
        max_length = 255
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 15] + "~DATA_TRUNCATED"

        return cleaned


# Legacy alias for backward compatibility during transition
# Any code referencing DynamicRecordRegexStrategy will get the new RecordRegexStrategy
DynamicRecordRegexStrategy = RecordRegexStrategy  # type: ignore


class DynamicRecordRegexStrategy(ExtractionStrategy):
    """
    Data-driven extraction strategy that builds regex patterns dynamically from field configurations.
    Supports multiple extraction types and provides robust field mapping through alias resolution.
    """

    def __init__(self, extraction_task: ExtractionTaskEntity, config_entity: ExtractionConfigurationEntity):
        super().__init__(extraction_task=extraction_task, config_entity=config_entity)
        self.field_extractors = self._build_field_extractors()
        self.alias_map = config_entity.field_alias_map
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _build_field_extractors(self) -> Dict[str, List["FieldExtractor"]]:
        """Build organized extractors for each field from extraction_details configuration."""
        field_extractors = {}

        for field in self.extraction_configuration.data_fields:
            extractors = []

            # Process each extraction detail step
            for step in field.extraction_details:
                extractor = self._create_field_extractor(field, step)
                if extractor:
                    extractors.append(extractor)

            # Add fallback extractor if no explicit extractors defined
            if not extractors and field.aliases:
                fallback_extractor = self._create_fallback_extractor(field)
                if fallback_extractor:
                    extractors.append(fallback_extractor)

            if extractors:
                field_extractors[field.name] = extractors
                self.logger.debug(f"Built {len(extractors)} extractors for field '{field.name}'")

        return field_extractors

    def _create_field_extractor(self, field: "DataFieldEntity", step: Dict[str, Any]) -> Optional["FieldExtractor"]:
        """Create a field extractor from an extraction detail step."""
        extraction_type = step.get("extraction_type", "").lower()

        if extraction_type == "regex":
            return self._create_regex_extractor(field, step)
        elif extraction_type == "literal":
            return self._create_literal_extractor(field, step)
        elif extraction_type == "json":
            return self._create_json_extractor(field, step)
        else:
            self.logger.warning(f"Unknown extraction_type '{extraction_type}' for field '{field.name}'")
            return None

    def _create_regex_extractor(
        self, field: "DataFieldEntity", step: Dict[str, Any]
    ) -> Optional["RegexFieldExtractor"]:
        """Create a regex-based field extractor."""
        pattern_template = step.get("extraction_regex", r"(?P<key>%%ALIASES%%)\s*[:=]\s*(?P<value>.*)")

        try:
            # Replace alias macro with actual aliases
            if "%%ALIASES%%" in pattern_template:
                if field.aliases:
                    alias_pattern = "|".join(re.escape(alias) for alias in field.aliases)
                    pattern = pattern_template.replace("%%ALIASES%%", alias_pattern)
                else:
                    # Fallback to field name if no aliases
                    pattern = pattern_template.replace("%%ALIASES%%", re.escape(field.name))
            else:
                pattern = pattern_template

            # Compile pattern with flags
            flags = re.IGNORECASE | re.MULTILINE
            compiled_pattern = re.compile(pattern, flags)

            return RegexFieldExtractor(
                field_name=field.name, pattern=compiled_pattern, required=field.required, data_type=field.data_type
            )

        except re.error as e:
            self.logger.error(f"Invalid regex pattern for field '{field.name}': {pattern_template} - {e}")
            return None

    def _create_literal_extractor(
        self, field: "DataFieldEntity", step: Dict[str, Any]
    ) -> Optional["LiteralFieldExtractor"]:
        """Create a literal string matching extractor."""
        literal_value = step.get("literal_value")
        if literal_value:
            return LiteralFieldExtractor(
                field_name=field.name, literal_value=literal_value, required=field.required, data_type=field.data_type
            )
        return None

    def _create_json_extractor(self, field: "DataFieldEntity", step: Dict[str, Any]) -> Optional["JsonFieldExtractor"]:
        """Create a JSON path-based extractor."""
        json_path = step.get("json_path")
        if json_path:
            return JsonFieldExtractor(
                field_name=field.name, json_path=json_path, required=field.required, data_type=field.data_type
            )
        return None

    def _create_fallback_extractor(self, field: "DataFieldEntity") -> Optional["RegexFieldExtractor"]:
        """Create a fallback regex extractor based on field aliases."""
        if not field.aliases:
            return None

        # Create a simple key-value pattern using aliases
        alias_pattern = "|".join(re.escape(alias) for alias in field.aliases)
        pattern = rf"(?P<key>{alias_pattern})\s*[:=]\s*(?P<value>.*)"

        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            return RegexFieldExtractor(
                field_name=field.name, pattern=compiled_pattern, required=field.required, data_type=field.data_type
            )
        except re.error as e:
            self.logger.error(f"Failed to create fallback extractor for field '{field.name}': {e}")
            return None

    def _extract_chunk(self, chunk: List[str]) -> Generator[Dict[str, Any], None, None]:
        """Extract data from chunk using dynamic field extractors."""
        data = {}
        processed_lines = set()  # Track processed lines to avoid redundant work

        # Process each field's extractors
        for field_name, extractors in self.field_extractors.items():
            if field_name in data:
                continue  # Skip if field already extracted

            # Try each extractor until we get a match
            for extractor in extractors:
                for line_idx, line in enumerate(chunk):
                    if line_idx in processed_lines:
                        continue

                    extracted_value = extractor.extract(line)
                    if extracted_value is not None:
                        cleaned_value = self._clean_and_validate_value(extracted_value, extractor.data_type)
                        if cleaned_value:
                            data[field_name] = cleaned_value
                            processed_lines.add(line_idx)
                            break  # Found match for this field, move to next field

                if field_name in data:
                    break  # Found match for this field, try next field

        if data:
            yield data

    def _clean_and_validate_value(self, value: str, data_type: str) -> Optional[str]:
        """Clean and validate extracted value based on data type."""
        if not value or not value.strip():
            return None

        cleaned = value.strip()

        # Remove quotes
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1]

        # Remove trailing punctuation
        cleaned = cleaned.rstrip(",;.")

        # Data type specific validation
        if data_type == "integer":
            try:
                int(cleaned)
            except ValueError:
                self.logger.warning(f"Invalid integer value: {cleaned}")
                return None
        elif data_type == "boolean":
            if cleaned.lower() not in ["true", "false", "yes", "no", "1", "0"]:
                self.logger.warning(f"Invalid boolean value: {cleaned}")
                return None

        # Truncate if too long
        max_length = 255
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 15] + "~DATA_TRUNCATED"

        return cleaned


# Field Extractor Classes
class FieldExtractor:
    """Base class for field extractors."""

    def __init__(self, field_name: str, required: bool = False, data_type: str = "string"):
        self.field_name = field_name
        self.required = required
        self.data_type = data_type

    def extract(self, line: str) -> Optional[str]:
        """Extract value from line. Return None if no match."""
        raise NotImplementedError


class RegexFieldExtractor(FieldExtractor):
    """Regex-based field extractor."""

    def __init__(self, field_name: str, pattern: re.Pattern, required: bool = False, data_type: str = "string"):
        super().__init__(field_name, required, data_type)
        self.pattern = pattern

    def extract(self, line: str) -> Optional[str]:
        """Extract value using regex pattern."""
        match = self.pattern.search(line)
        if match:
            groups = match.groupdict()
            return groups.get("value", groups.get(self.field_name))
        return None


class LiteralFieldExtractor(FieldExtractor):
    """Literal string matching extractor."""

    def __init__(self, field_name: str, literal_value: str, required: bool = False, data_type: str = "string"):
        super().__init__(field_name, required, data_type)
        self.literal_value = literal_value

    def extract(self, line: str) -> Optional[str]:
        """Extract literal value if present in line."""
        if self.literal_value.lower() in line.lower():
            return self.literal_value
        return None


class JsonFieldExtractor(FieldExtractor):
    """JSON path-based extractor."""

    def __init__(self, field_name: str, json_path: str, required: bool = False, data_type: str = "string"):
        super().__init__(field_name, required, data_type)
        self.json_path = json_path

    def extract(self, line: str) -> Optional[str]:
        """Extract value from JSON line using path."""
        try:
            data = json.loads(line)
            # Simple JSON path implementation (can be enhanced)
            keys = self.json_path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return str(value) if value is not None else None
        except (json.JSONDecodeError, KeyError, AttributeError):
            return None


class CookieStrategy(ExtractionStrategy):
    """Enhanced cookie extraction strategy for Netscape cookie jar format.

    Parses standard 7-field TAB-delimited cookie format:
    domain, flag, path, secure, expiration, name, value
    """

    def _extract_chunk(self, chunk: List[str]) -> Generator[Dict[str, Any], None, None]:
        """Extract cookie data from chunk of lines in Netscape cookie jar format.

        Expected format per line: domain\tflag\tpath\tsecure\texpiration\tname\tvalue
        """
        for line in chunk:
            try:
                line = line.strip()
                if not line or line.startswith("#"):  # Skip comments and empty lines
                    continue

                parts = line.split("\t")
                if len(parts) != 7:
                    # Log malformed line but continue processing
                    logger.warning(f"Malformed cookie line with {len(parts)} fields (expected 7): {line[:100]}...")
                    continue

                # Extract fields in correct Netscape cookie jar order
                domain, flag, path, secure, expiration, name, value = parts

                # Build cookie data with proper field names and types
                cookie_data = {
                    "domain": domain,
                    "flag": self._parse_boolean(flag),
                    "path": path,
                    "secure": self._parse_boolean(secure),
                    "expiration": self._parse_timestamp(expiration),
                    "name": name,
                    "value": value,
                    "raw_data": line,  # Preserve original line for debugging
                }

                yield cookie_data

            except Exception as e:
                logger.error(f"Error parsing cookie line: {line[:100]}... - {e}")
                # Yield minimal data to avoid losing the record entirely
                yield {"raw_data": line, "parse_error": str(e), "domain": "", "name": "", "value": ""}

    def _parse_boolean(self, value: str) -> bool:
        """Convert TRUE/FALSE string to boolean."""
        return value.upper() == "TRUE"

    def _parse_timestamp(self, timestamp_str: str) -> int:
        """Convert UNIX timestamp string to integer, with error handling."""
        try:
            return int(timestamp_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid timestamp format: {timestamp_str}")
            return 0


class UserFileStrategy(ExtractionStrategy):
    """Enhanced user file strategy with intelligent context window extraction."""

    def _extract_file(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract content with intelligent context windows around target matches."""
        try:
            # Get targets and configuration from process_configuration
            targets = self.extraction_configuration.process_configuration.get("targets", [])
            config = self.extraction_configuration.process_configuration

            # Configuration options
            default_context_window = config.get("default_context_window", 150)
            max_matches_per_target = config.get("max_matches_per_target", 10)
            max_file_size = config.get("max_file_size", 1024 * 1024)  # 1MB default
            smart_boundaries = config.get("smart_boundaries", True)

            # Get file basic info
            encoding = detect_encoding(file_path)
            file_size = file_path.stat().st_size

            # Skip if file is too large
            if file_size > max_file_size:
                yield {
                    "file_path": file_path.as_posix(),
                    "file_size": file_size,
                    "encoding": encoding,
                    "status": "skipped_too_large",
                    "max_size_limit": max_file_size,
                    "total_matches": 0,
                    "matches": [],
                }
                return

            # Read file content
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                file_content = f.read()

            # Initialize result structure
            result = {
                "file_path": file_path.as_posix(),
                "file_size": file_size,
                "encoding": encoding,
                "content_length": len(file_content),
                "total_matches": 0,
                "targets_found": [],
                "matches": [],
            }

            # Process each target
            for target_config in targets:
                matches = self._find_target_matches(
                    content=file_content,
                    target_config=target_config,
                    default_context_window=default_context_window,
                    max_matches=max_matches_per_target,
                    smart_boundaries=smart_boundaries,
                )

                if matches:
                    result["targets_found"].append(self._get_target_identifier(target_config))
                    result["matches"].extend(matches)

            result["total_matches"] = len(result["matches"])

            # If no matches, provide basic file info
            if result["total_matches"] == 0:
                result["status"] = "no_matches_found"
            else:
                result["status"] = "matches_found"
                # Sort matches by position for consistent output
                result["matches"].sort(key=lambda x: x.get("position", 0))

            yield result

        except Exception as e:
            logger.error(f"Error processing user file {file_path}: {e}")
            yield {
                "file_path": file_path.as_posix(),
                "extraction_error": str(e),
                "status": "error",
                "total_matches": 0,
                "matches": [],
            }

    def _find_target_matches(
        self, content: str, target_config: Dict, default_context_window: int, max_matches: int, smart_boundaries: bool
    ) -> List[Dict[str, Any]]:
        """Find matches for a specific target configuration."""
        matches = []

        # Determine target type and pattern
        if isinstance(target_config, str):
            # Legacy format: simple regex string
            target_type = "regex"
            pattern = target_config
            context_window = default_context_window
            case_sensitive = False
        elif isinstance(target_config, dict):
            # New enhanced format
            target_type = target_config.get("type", "regex")
            context_window = target_config.get("context_window", default_context_window)
            case_sensitive = target_config.get("case_sensitive", False)

            # Extract the appropriate pattern based on target type
            if target_type == "regex":
                pattern = target_config.get("pattern", "")
            elif target_type == "keywords":
                pattern = target_config.get("keywords", [])
            elif target_type == "phrase":
                pattern = target_config.get("phrase", "")
            else:
                pattern = target_config.get("pattern", "")
        else:
            logger.warning(f"Invalid target configuration: {target_config}")
            return matches

        # Validate pattern exists
        if not pattern:
            logger.warning(f"No pattern found for target type {target_type}")
            return matches

        try:
            if target_type == "regex" and isinstance(pattern, str):
                matches = self._find_regex_matches(
                    content, pattern, context_window, max_matches, smart_boundaries, case_sensitive
                )
            elif target_type == "keywords" and isinstance(pattern, list):
                matches = self._find_keyword_matches(
                    content, pattern, context_window, max_matches, smart_boundaries, case_sensitive, target_config
                )
            elif target_type == "phrase" and isinstance(pattern, str):
                matches = self._find_phrase_matches(
                    content, pattern, context_window, max_matches, smart_boundaries, case_sensitive
                )
            else:
                logger.warning(f"Invalid pattern type for target type {target_type}: {type(pattern)}")

        except Exception as e:
            logger.error(f"Error finding matches for target {pattern}: {e}")

        # Add target metadata to each match
        for match in matches:
            match["target_config"] = target_config
            match["target_type"] = target_type

        return matches

    def _find_regex_matches(
        self,
        content: str,
        pattern: str,
        context_window: int,
        max_matches: int,
        smart_boundaries: bool,
        case_sensitive: bool,
    ) -> List[Dict[str, Any]]:
        """Find regex pattern matches with context extraction."""
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            regex_pattern = re.compile(pattern, flags)

            for match_obj in regex_pattern.finditer(content):
                if len(matches) >= max_matches:
                    break

                match_data = self._extract_match_context(
                    content=content,
                    match_start=match_obj.start(),
                    match_end=match_obj.end(),
                    match_text=match_obj.group(0),
                    context_window=context_window,
                    smart_boundaries=smart_boundaries,
                )

                match_data.update(
                    {
                        "target": pattern,
                        "match_groups": match_obj.groups() if match_obj.groups() else [],
                        "match_groupdict": match_obj.groupdict() if match_obj.groupdict() else {},
                    }
                )

                matches.append(match_data)

        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")

        return matches

    def _find_keyword_matches(
        self,
        content: str,
        keywords: List[str],
        context_window: int,
        max_matches: int,
        smart_boundaries: bool,
        case_sensitive: bool,
        target_config: Dict,
    ) -> List[Dict[str, Any]]:
        """Find keyword matches with context extraction."""
        matches = []
        word_boundaries = target_config.get("word_boundaries", True)

        # Convert keywords to regex patterns
        for keyword in keywords:
            if len(matches) >= max_matches:
                break

            # Escape special regex characters
            escaped_keyword = re.escape(keyword)

            # Add word boundaries if requested
            if word_boundaries:
                pattern = r"\b" + escaped_keyword + r"\b"
            else:
                pattern = escaped_keyword

            # Find matches for this keyword
            keyword_matches = self._find_regex_matches(
                content, pattern, context_window, max_matches - len(matches), smart_boundaries, case_sensitive
            )

            # Update target info for keyword matches
            for match in keyword_matches:
                match["target"] = keyword
                match["keyword"] = keyword

            matches.extend(keyword_matches)

        return matches

    def _find_phrase_matches(
        self,
        content: str,
        phrase: str,
        context_window: int,
        max_matches: int,
        smart_boundaries: bool,
        case_sensitive: bool,
    ) -> List[Dict[str, Any]]:
        """Find phrase matches with context extraction."""
        # Convert phrase to regex pattern
        escaped_phrase = re.escape(phrase)
        # Replace spaces with flexible whitespace pattern
        pattern = re.sub(r"\\ ", r"\\s+", escaped_phrase)

        matches = self._find_regex_matches(
            content, pattern, context_window, max_matches, smart_boundaries, case_sensitive
        )

        # Update target info for phrase matches
        for match in matches:
            match["target"] = phrase
            match["phrase"] = phrase

        return matches

    def _extract_match_context(
        self,
        content: str,
        match_start: int,
        match_end: int,
        match_text: str,
        context_window: int,
        smart_boundaries: bool,
    ) -> Dict[str, Any]:
        """Extract context around a match with intelligent boundary detection."""
        content_length = len(content)

        # Calculate basic window boundaries
        context_start = max(0, match_start - context_window // 2)
        context_end = min(content_length, match_end + context_window // 2)

        # Apply smart boundary detection
        if smart_boundaries:
            context_start, context_end = self._adjust_boundaries(
                content, context_start, context_end, match_start, match_end
            )

        # Extract context sections
        context_before = content[context_start:match_start]
        context_after = content[match_end:context_end]
        full_context = content[context_start:context_end]

        # Calculate line number
        line_number = content[:match_start].count("\n") + 1

        # Calculate relative position within context
        relative_position = match_start - context_start

        return {
            "match_text": match_text,
            "context_before": context_before,
            "context_after": context_after,
            "full_context": full_context,
            "position": match_start,
            "line_number": line_number,
            "context_start": context_start,
            "context_end": context_end,
            "relative_position": relative_position,
            "context_length": len(full_context),
        }

    def _adjust_boundaries(
        self, content: str, start: int, end: int, match_start: int, match_end: int
    ) -> Tuple[int, int]:
        """Adjust context boundaries to respect sentence/paragraph boundaries."""
        # Look for sentence boundaries (. ! ?) followed by whitespace
        sentence_pattern = re.compile(r"[.!?]\s+")

        # Adjust start boundary - look backwards for sentence start
        search_start = max(0, start - 50)  # Look back up to 50 chars more
        before_text = content[search_start:match_start]

        # Find sentence boundaries before the match
        sentence_matches = list(sentence_pattern.finditer(before_text))
        if sentence_matches:
            # Use the last sentence boundary before the match
            last_boundary = sentence_matches[-1].end() + search_start
            if last_boundary > start:
                start = last_boundary

        # Adjust end boundary - look forwards for sentence end
        search_end = min(len(content), end + 50)  # Look ahead up to 50 chars more
        after_text = content[match_end:search_end]

        # Find first sentence boundary after the match
        sentence_match = sentence_pattern.search(after_text)
        if sentence_match:
            boundary_pos = sentence_match.end() + match_end
            if boundary_pos < end + 50:  # Don't extend too far
                end = boundary_pos

        # Fallback: look for paragraph boundaries (double newlines)
        if start == max(0, match_start - 100):  # If no sentence boundary found
            para_start = content.rfind("\n\n", 0, match_start)
            if para_start != -1 and para_start > start - 100:
                start = para_start + 2

        if end == min(len(content), match_end + 100):  # If no sentence boundary found
            para_end = content.find("\n\n", match_end)
            if para_end != -1 and para_end < end + 100:
                end = para_end

        return start, end

    def _get_target_identifier(self, target_config: Dict) -> str:
        """Get a string identifier for the target configuration."""
        if isinstance(target_config, str):
            return target_config
        elif isinstance(target_config, dict):
            return (
                target_config.get("pattern")
                or str(target_config.get("keywords"))
                or target_config.get("phrase")
                or str(target_config)
            )
        else:
            return str(target_config)


# ============================================================================
# Enhanced Multi-Wallet Vault Extraction System
# ============================================================================


class WalletExtractor(ABC):
    """Base class for wallet-specific extractors."""

    @abstractmethod
    def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        pass

    @abstractmethod
    def extract_vault_data(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract vault data from the file."""
        pass

    @abstractmethod
    def get_wallet_type(self) -> str:
        """Return the wallet type identifier."""
        pass


class MetaMaskExtractor(WalletExtractor):
    """Extractor for MetaMask browser extension wallet data."""

    def can_extract(self, file_path: Path) -> bool:
        """Check if file is a MetaMask LevelDB file with vault data."""
        try:
            # Check for LevelDB file extensions
            if not file_path.suffix.lower() in [".ldb", ".log"] and "MANIFEST" not in file_path.name:
                return False

            # Check file content for MetaMask vault indicators
            if file_path.suffix.lower() == ".ldb":
                filebytes = file_path.read_bytes()
                encoding = detect_encoding(file_path)
                data = decode(filebytes, encoding, "ignore")
                return "salt" in data and ("wallet" in data or "vault" in data)

            return True  # Other LevelDB files might be part of MetaMask
        except Exception:
            return False

    def extract_vault_data(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract MetaMask vault data using the original logic."""
        try:
            filebytes = file_path.read_bytes()
            encoding = detect_encoding(file_path)
            data = decode(filebytes, encoding, "ignore").replace("\\", "")

            if "salt" in data:
                # Find last wallet entry (most recent, valid wallet)
                start = 0
                for match in re.finditer("wallet", data):
                    start = match.start()

                wallet_data_trimmed = data[start:]
                wallet_data_start = wallet_data_trimmed.find("data")
                wallet_data_trimmed = wallet_data_trimmed[wallet_data_start - 2 :]
                wallet_data_end = wallet_data_trimmed.find("}")
                wallet_data = wallet_data_trimmed[: wallet_data_end + 1]

                if wallet_data:
                    dat = json.loads(wallet_data)
                    yield {
                        "wallet_type": self.get_wallet_type(),
                        "vault_data": dat,
                        "source_file": str(file_path),
                        "extraction_method": "metamask_leveldb",
                    }
        except Exception as e:
            logger.error(f"Error extracting MetaMask data from {file_path}: {e}")
            yield {"wallet_type": self.get_wallet_type(), "extraction_error": str(e), "source_file": str(file_path)}

    def get_wallet_type(self) -> str:
        return "metamask"


class BitcoinCoreExtractor(WalletExtractor):
    """Extractor for Bitcoin Core wallet.dat files."""

    def can_extract(self, file_path: Path) -> bool:
        """Check if file is a Bitcoin Core wallet.dat file."""
        try:
            if file_path.name.lower() != "wallet.dat":
                return False

            # Check for Berkeley DB magic bytes
            with open(file_path, "rb") as f:
                magic = f.read(12)
                # Berkeley DB magic numbers
                return (
                    magic[:4] == b"\x00\x05\x31\x62" or magic[:8] == b"SQLite format 3\x00"  # BDB
                )  # SQLite (newer versions)
        except Exception:
            return False

    def extract_vault_data(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract Bitcoin Core wallet data."""
        try:
            file_size = file_path.stat().st_size
            with open(file_path, "rb") as f:
                magic = f.read(12)
                f.seek(0)

                # Basic wallet information
                wallet_data = {
                    "wallet_type": self.get_wallet_type(),
                    "source_file": str(file_path),
                    "file_size": file_size,
                    "extraction_method": "bitcoin_core_wallet",
                }

                # Detect format
                if magic[:8] == b"SQLite format 3\x00":
                    wallet_data["format"] = "sqlite"
                    wallet_data["note"] = "SQLite format wallet (Bitcoin Core 0.21+)"
                elif magic[:4] == b"\x00\x05\x31\x62":
                    wallet_data["format"] = "berkeley_db"
                    wallet_data["note"] = "Berkeley DB format wallet"
                else:
                    wallet_data["format"] = "unknown"
                    wallet_data["note"] = "Unknown wallet format"

                # For now, just extract basic info - full wallet parsing would need Berkeley DB/SQLite libraries
                wallet_data["status"] = "detected_but_encrypted"
                wallet_data["requires_password"] = True

                yield wallet_data

        except Exception as e:
            logger.error(f"Error extracting Bitcoin Core wallet from {file_path}: {e}")
            yield {"wallet_type": self.get_wallet_type(), "extraction_error": str(e), "source_file": str(file_path)}

    def get_wallet_type(self) -> str:
        return "bitcoin_core"


class EthereumKeystoreExtractor(WalletExtractor):
    """Extractor for Ethereum keystore JSON files."""

    def can_extract(self, file_path: Path) -> bool:
        """Check if file is an Ethereum keystore file."""
        try:
            if not file_path.suffix.lower() == ".json":
                return False

            with open(file_path, "r") as f:
                data = json.load(f)
                # Check for keystore structure
                return ("crypto" in data and "version" in data) or ("Crypto" in data and "version" in data)
        except Exception:
            return False

    def extract_vault_data(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract Ethereum keystore data."""
        try:
            with open(file_path, "r") as f:
                keystore_data = json.load(f)

            yield {
                "wallet_type": self.get_wallet_type(),
                "source_file": str(file_path),
                "extraction_method": "ethereum_keystore",
                "keystore_version": keystore_data.get("version"),
                "address": keystore_data.get("address"),
                "crypto_params": {
                    "cipher": keystore_data.get("crypto", {}).get("cipher")
                    or keystore_data.get("Crypto", {}).get("cipher"),
                    "kdf": keystore_data.get("crypto", {}).get("kdf") or keystore_data.get("Crypto", {}).get("kdf"),
                },
                "vault_data": keystore_data,
                "requires_password": True,
            }

        except Exception as e:
            logger.error(f"Error extracting Ethereum keystore from {file_path}: {e}")
            yield {"wallet_type": self.get_wallet_type(), "extraction_error": str(e), "source_file": str(file_path)}

    def get_wallet_type(self) -> str:
        return "ethereum_keystore"


class ElectrumExtractor(WalletExtractor):
    """Extractor for Electrum wallet files."""

    def can_extract(self, file_path: Path) -> bool:
        """Check if file is an Electrum wallet file."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                # Check for Electrum wallet structure
                return "seed_version" in data or "wallet_type" in data
        except Exception:
            return False

    def extract_vault_data(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract Electrum wallet data."""
        try:
            with open(file_path, "r") as f:
                wallet_data = json.load(f)

            yield {
                "wallet_type": self.get_wallet_type(),
                "source_file": str(file_path),
                "extraction_method": "electrum_wallet",
                "seed_version": wallet_data.get("seed_version"),
                "wallet_type_detail": wallet_data.get("wallet_type"),
                "use_encryption": wallet_data.get("use_encryption", False),
                "vault_data": wallet_data,
                "requires_password": wallet_data.get("use_encryption", False),
            }

        except Exception as e:
            logger.error(f"Error extracting Electrum wallet from {file_path}: {e}")
            yield {"wallet_type": self.get_wallet_type(), "extraction_error": str(e), "source_file": str(file_path)}

    def get_wallet_type(self) -> str:
        return "electrum"


class WalletDetector:
    """Detects wallet types and routes to appropriate extractors."""

    def __init__(self):
        self.extractors = [
            MetaMaskExtractor(),
            BitcoinCoreExtractor(),
            EthereumKeystoreExtractor(),
            ElectrumExtractor(),
        ]

    def detect_wallet_types(self, file_path: Path) -> List[WalletExtractor]:
        """Detect all possible wallet types for a file."""
        compatible_extractors = []
        for extractor in self.extractors:
            try:
                if extractor.can_extract(file_path):
                    compatible_extractors.append(extractor)
            except Exception as e:
                logger.debug(f"Error checking {extractor.get_wallet_type()} for {file_path}: {e}")
        return compatible_extractors

    def get_best_extractor(self, file_path: Path) -> Optional[WalletExtractor]:
        """Get the most appropriate extractor for a file."""
        compatible = self.detect_wallet_types(file_path)
        if not compatible:
            return None

        # Priority order: MetaMask, Bitcoin Core, Ethereum Keystore, Electrum
        priority_order = ["metamask", "bitcoin_core", "ethereum_keystore", "electrum"]
        for wallet_type in priority_order:
            for extractor in compatible:
                if extractor.get_wallet_type() == wallet_type:
                    return extractor

        return compatible[0]  # Return first available if no priority match


class VaultStrategy(ExtractionStrategy):
    """Enhanced vault extraction strategy supporting multiple wallet types."""

    def __init__(self, extraction_task: ExtractionTaskEntity, config_entity: ExtractionConfigurationEntity):
        super().__init__(extraction_task=extraction_task, config_entity=config_entity)
        self.wallet_detector = WalletDetector()

        # Legacy regex patterns for backward compatibility (commented out in original)
        # self.regex: List[regex.Pattern] = [
        #     regex.compile(pattern, flags=regex.IGNORECASE)
        #     for pattern in [
        #         r"{\\\"data\\\":\\\"(?P<data>.+?)\\\",\\\"iv\\\":\\\"(?P<iv>.+?)\\\",\\\"salt\\\":\\\"(?P<salt>.+?)\\\"}",
        #         r"{\\\"encrypted\\\":\\\"(?P<data>.+?)\\\",\\\"nonce\\\":\\\"(?P<iv>.+?)\\\",\\\"kdf\\\":\\\"pbkdf2\\\",\\\"salt\\\":\\\"(?P<salt>.+?)\\\",\\\"iterations\\\":10000,\\\"digest\\\":\\\"sha256\\\"}",
        #         r"{\\\"ct\\\":\\\"(?P<data>.+?)\\\",\\\"iv\\\":\\\"(?P<iv>.+?)\\\",\\\"s\\\":\\\"(?P<salt>.+?)\\\"}",
        #     ]
        # ]

    def _extract_file(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """Extract vault data using multi-wallet detection and extraction."""
        try:
            # Attempt to detect and extract using new multi-wallet system
            detected_extractors = self.wallet_detector.detect_wallet_types(file_path)

            if detected_extractors:
                logger.info(f"Detected {len(detected_extractors)} wallet type(s) for {file_path}")

                # Try each compatible extractor
                extraction_success = False
                for extractor in detected_extractors:
                    try:
                        logger.info(f"Attempting extraction with {extractor.get_wallet_type()} extractor")
                        for vault_data in extractor.extract_vault_data(file_path):
                            if vault_data:
                                extraction_success = True
                                yield vault_data
                    except Exception as e:
                        logger.warning(f"Extraction failed with {extractor.get_wallet_type()}: {e}")
                        continue

                if extraction_success:
                    return

            # Fallback to legacy MetaMask extraction for backward compatibility
            logger.info(f"No specific wallet type detected, attempting legacy extraction for {file_path}")
            legacy_result = self._legacy_metamask_extraction(file_path)
            if legacy_result:
                yield legacy_result
            else:
                # If no extraction worked, yield basic file info
                yield {
                    "wallet_type": "unknown",
                    "source_file": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "extraction_method": "unknown",
                    "status": "no_vault_data_found",
                    "note": "File detected but no vault data could be extracted",
                }

        except Exception as e:
            logger.error(f"Error in VaultStrategy extraction for {file_path}: {e}")
            yield {
                "wallet_type": "error",
                "source_file": str(file_path),
                "extraction_error": str(e),
                "extraction_method": "vault_strategy",
            }

    def _legacy_metamask_extraction(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Legacy MetaMask extraction logic for backward compatibility."""
        try:
            filebytes = file_path.read_bytes()
            encoding = detect_encoding(file_path)
            data = decode(filebytes, encoding, "ignore").replace("\\", "")
            start = 0

            if "salt" in data:
                # Find last wallet entry (Will be valid, most recent, wallet)
                for match in re.finditer("wallet", data):
                    start = match.start()
                    continue
                wallet_data_trimmed = data[start:]
                wallet_data_start = wallet_data_trimmed.find("data")
                wallet_data_trimmed = wallet_data_trimmed[wallet_data_start - 2 :]
                wallet_data_end = wallet_data_trimmed.find("}")
                wallet_data = wallet_data_trimmed[: wallet_data_end + 1]

                if wallet_data:
                    dat = json.loads(wallet_data)
                    return {
                        "wallet_type": "metamask_legacy",
                        "vault_data": dat,
                        "source_file": str(file_path),
                        "extraction_method": "legacy_metamask",
                    }
            return None
        except Exception as e:
            logger.debug(f"Legacy extraction failed for {file_path}: {e}")
            return None
