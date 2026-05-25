"""Honeypot YAML Loader and Registry.

Loads honeypot definitions from YAML files and maintains
a registry of available honeypots.
"""

from core.observability.logging import get_logger
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError

from .honeypot_definition import HoneypotDefinition, HoneypotDefinitionFile
from .models import HoneypotProtocol

logger = get_logger(__name__)


class HoneypotLoadError(Exception):
    """Error loading honeypot definition."""

    pass


class HoneypotRegistry:
    """Registry for loaded honeypot definitions.

    Manages loading, validation, and access to honeypot definitions
    from YAML files.
    """

    def __init__(self, honeypots_dir: Optional[Path] = None):
        """Initialize the registry.

        Args:
            honeypots_dir: Directory containing YAML definition files.
                           Defaults to 'honeypots/' relative to this module.
        """
        if honeypots_dir is None:
            honeypots_dir = Path(__file__).parent / "honeypots"
        self.honeypots_dir = honeypots_dir
        self._definitions: Dict[str, HoneypotDefinitionFile] = {}
        self._load_errors: Dict[str, str] = {}

    async def load_all(self) -> int:
        """Load all YAML files from definitions directory.

        Returns:
            Number of successfully loaded definitions.
        """
        if not self.honeypots_dir.exists():
            logger.warning(f"Honeypots directory not found: {self.honeypots_dir}")
            self.honeypots_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created honeypots directory: {self.honeypots_dir}")
            return 0

        loaded_count = 0
        yaml_files = list(self.honeypots_dir.glob("*.yaml")) + list(
            self.honeypots_dir.glob("*.yml")
        )

        if not yaml_files:
            logger.info(f"No YAML files found in {self.honeypots_dir}")
            return 0

        for yaml_file in yaml_files:
            try:
                definition = await self._load_file(yaml_file)
                if definition:
                    self._definitions[definition.definition.id] = definition
                    loaded_count += 1
                    logger.info(
                        f"Loaded honeypot definition: {definition.definition.id} "
                        f"({definition.definition.name})"
                    )
            except HoneypotLoadError as e:
                self._load_errors[yaml_file.name] = str(e)
                logger.error(f"Failed to load {yaml_file.name}: {e}")

        logger.info(
            f"Loaded {loaded_count} honeypot definitions from {self.honeypots_dir}"
        )
        return loaded_count

    async def _load_file(self, file_path: Path) -> HoneypotDefinitionFile:
        """Load a single YAML file.

        Args:
            file_path: Path to the YAML file.

        Returns:
            Loaded definition with metadata.

        Raises:
            HoneypotLoadError: If file cannot be loaded or validated.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise HoneypotLoadError(f"Empty YAML file: {file_path}")

            # Validate against schema
            definition = HoneypotDefinition.model_validate(data)

            # Check for ID conflicts
            if definition.id in self._definitions:
                raise HoneypotLoadError(
                    f"Duplicate honeypot ID '{definition.id}' "
                    f"(already loaded from {self._definitions[definition.id].source_file})"
                )

            return HoneypotDefinitionFile(definition=definition, source_file=file_path)

        except yaml.YAMLError as e:
            raise HoneypotLoadError(f"Invalid YAML syntax: {e}")
        except ValidationError as e:
            raise HoneypotLoadError(f"Schema validation failed: {e}")
        except Exception as e:
            raise HoneypotLoadError(f"Unexpected error: {e}")

    def reload(self, honeypot_id: str) -> bool:
        """Reload a specific honeypot definition.

        Args:
            honeypot_id: ID of the honeypot to reload.

        Returns:
            True if reload was successful.
        """
        if honeypot_id not in self._definitions:
            return False

        source_file = self._definitions[honeypot_id].source_file
        try:
            # Remove from registry first
            del self._definitions[honeypot_id]
            # Re-load
            import asyncio

            definition = asyncio.get_event_loop().run_until_complete(
                self._load_file(source_file)
            )
            self._definitions[definition.definition.id] = definition
            logger.info(f"Reloaded honeypot definition: {honeypot_id}")
            return True
        except HoneypotLoadError as e:
            logger.error(f"Failed to reload {honeypot_id}: {e}")
            return False

    def get(self, honeypot_id: str) -> Optional[HoneypotDefinition]:
        """Get specific honeypot by ID.

        Args:
            honeypot_id: The honeypot identifier.

        Returns:
            HoneypotDefinition if found, None otherwise.
        """
        if honeypot_id in self._definitions:
            return self._definitions[honeypot_id].definition
        return None

    def list_all(self) -> List[HoneypotDefinition]:
        """List all loaded honeypots.

        Returns:
            List of all honeypot definitions.
        """
        return [df.definition for df in self._definitions.values()]

    def list_enabled(self) -> List[HoneypotDefinition]:
        """List all enabled honeypots.

        Returns:
            List of enabled honeypot definitions.
        """
        return [
            df.definition for df in self._definitions.values() if df.definition.enabled
        ]

    def get_by_protocol(
        self, protocol: str | HoneypotProtocol
    ) -> List[HoneypotDefinition]:
        """Get honeypots by protocol type.

        Args:
            protocol: Protocol to filter by (e.g., 'ssh', 'http', 'tcp').

        Returns:
            List of matching honeypot definitions.
        """
        if isinstance(protocol, str):
            protocol = HoneypotProtocol(protocol)

        return [
            df.definition
            for df in self._definitions.values()
            if df.definition.protocol == protocol
        ]

    def get_by_port(self, port: int) -> Optional[HoneypotDefinition]:
        """Get honeypot listening on a specific port.

        Args:
            port: Port number to search for.

        Returns:
            HoneypotDefinition if found, None otherwise.
        """
        for df in self._definitions.values():
            if df.definition.port == port:
                return df.definition
        return None

    def get_by_tag(self, tag: str) -> List[HoneypotDefinition]:
        """Get honeypots with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of matching honeypot definitions.
        """
        return [
            df.definition
            for df in self._definitions.values()
            if tag in df.definition.tags
        ]

    @property
    def count(self) -> int:
        """Get number of loaded definitions."""
        return len(self._definitions)

    @property
    def enabled_count(self) -> int:
        """Get number of enabled definitions."""
        return len([df for df in self._definitions.values() if df.definition.enabled])

    @property
    def load_errors(self) -> Dict[str, str]:
        """Get any errors encountered during loading."""
        return self._load_errors.copy()

    def get_summary(self) -> Dict[str, int]:
        """Get summary of loaded honeypots by protocol.

        Returns:
            Dict mapping protocol names to counts.
        """
        summary: Dict[str, int] = {}
        for df in self._definitions.values():
            proto = df.definition.protocol.value
            summary[proto] = summary.get(proto, 0) + 1
        return summary


# Global registry instance
_registry: Optional[HoneypotRegistry] = None


def get_registry() -> HoneypotRegistry:
    """Get or create the global honeypot registry.

    Returns:
        The global HoneypotRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = HoneypotRegistry()
    return _registry


async def initialize_registry(honeypots_dir: Optional[Path] = None) -> HoneypotRegistry:
    """Initialize and load the honeypot registry.

    Args:
        honeypots_dir: Optional custom directory for YAML files.

    Returns:
        Initialized registry with loaded definitions.
    """
    global _registry
    _registry = HoneypotRegistry(honeypots_dir)
    await _registry.load_all()
    return _registry
