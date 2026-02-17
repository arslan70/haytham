"""MVP Specification Parser for the Story-to-Implementation Pipeline.

Parses enhanced MVP specification markdown into structured data
that can be used to initialize pipeline state.

Reference: ADR-001a: MVP Spec Enhancement
"""

import re
from dataclasses import dataclass, field

from .state_models import Ambiguity, Entity, EntityAttribute, EntityRelationship, Story


@dataclass
class ParsedMVPSpec:
    """Result of parsing an enhanced MVP specification."""

    project_name: str = ""
    project_description: str = ""
    entities: list[Entity] = field(default_factory=list)
    stories: list[Story] = field(default_factory=list)
    uncertainties: list[tuple[str, Ambiguity]] = field(
        default_factory=list
    )  # (story_id, ambiguity)
    raw_text: str = ""


class MVPSpecParser:
    """Parse enhanced MVP specification markdown.

    Expected input format (from MVP specification agent):

    ## DOMAIN MODEL
    ### E-001: User
    **Attributes:**
    - id: UUID (primary_key)
    - email: String (unique)
    ...

    ## STORY DEPENDENCY GRAPH
    ### S-001: Create Note
    **User Story:** As a user, I want to...
    **Priority:** P0
    **Depends On:** E-001, E-002
    ...

    ## UNCERTAINTY REGISTRY
    ### AMB-001: Search scope
    **Story:** S-003
    **Classification:** decision_required
    ...
    """

    # Regex patterns for parsing
    ENTITY_HEADER_PATTERN = re.compile(r"###\s*(E-\d{3}):\s*(.+)")
    STORY_HEADER_PATTERN = re.compile(r"###\s*(S-\d{3}):\s*(.+)")
    AMBIGUITY_HEADER_PATTERN = re.compile(r"###\s*AMB-\d{3}:\s*(.+)")
    ATTRIBUTE_PATTERN = re.compile(
        r"-\s*(\w+):\s*(\w+)(?:\s*\(([^)]+)\))?"
    )  # - name: Type (constraints)
    RELATIONSHIP_PATTERN = re.compile(
        r"-\s*(has_many|belongs_to|has_one):\s*(E-\d{3})(?:\s*\(([^)]+)\))?"
    )
    PIPELINE_COMPLETE_PATTERN = re.compile(r"PIPELINE_DATA_COMPLETE:\s*true", re.IGNORECASE)

    def parse(self, mvp_spec_text: str) -> ParsedMVPSpec:
        """Parse MVP spec and return structured data.

        Args:
            mvp_spec_text: Full markdown text of enhanced MVP specification

        Returns:
            ParsedMVPSpec with extracted entities, stories, and uncertainties
        """
        result = ParsedMVPSpec(raw_text=mvp_spec_text)

        # Extract project info from the beginning
        result.project_name, result.project_description = self._extract_project_info(mvp_spec_text)

        # Extract domain model
        result.entities = self._extract_domain_model(mvp_spec_text)

        # Extract stories
        result.stories = self._extract_stories(mvp_spec_text)

        # Extract uncertainties and attach to stories
        self._extract_and_attach_uncertainties(mvp_spec_text, result)

        return result

    def _extract_project_info(self, text: str) -> tuple[str, str]:
        """Extract project name and description.

        Looks for Core Value Statement or MVP Specification Summary.
        """
        # Try to find Core Value Statement
        core_value_match = re.search(r"\*\*Core Value Statement:\*\*\s*\n[-*]?\s*(.+)", text)
        if core_value_match:
            return "MVP Project", core_value_match.group(1).strip()

        # Try to find UNIQUE VALUE in summary
        unique_value_match = re.search(r"UNIQUE VALUE:\s*(.+)", text)
        if unique_value_match:
            return "MVP Project", unique_value_match.group(1).strip()

        # Default
        return "MVP Project", "Generated MVP specification"

    def _extract_domain_model(self, text: str) -> list[Entity]:
        """Extract entities from Domain Model section."""
        entities = []

        # Find DOMAIN MODEL section
        domain_section = self._extract_section(text, "DOMAIN MODEL")
        if not domain_section:
            return entities

        # Split into entity blocks
        entity_blocks = re.split(r"(?=###\s*E-\d{3}:)", domain_section)

        for block in entity_blocks:
            if not block.strip():
                continue

            # Parse entity header
            header_match = self.ENTITY_HEADER_PATTERN.search(block)
            if not header_match:
                continue

            entity_id = header_match.group(1)
            entity_name = header_match.group(2).strip()

            # Parse attributes
            attributes = self._parse_attributes(block)

            # Parse relationships
            relationships = self._parse_relationships(block)

            entity = Entity(
                id=entity_id,
                name=entity_name,
                status="planned",
                attributes=attributes,
                relationships=relationships,
            )
            entities.append(entity)

        return entities

    def _parse_attributes(self, block: str) -> list[EntityAttribute]:
        """Parse attributes from an entity block."""
        attributes = []

        # Find Attributes section within block
        attr_section = self._extract_subsection(block, "Attributes")
        if not attr_section:
            return attributes

        for match in self.ATTRIBUTE_PATTERN.finditer(attr_section):
            name = match.group(1)
            attr_type = match.group(2)
            constraints = match.group(3) or ""

            attr = EntityAttribute(
                name=name,
                type=attr_type,
                primary_key="primary_key" in constraints,
                unique="unique" in constraints,
            )

            # Check for foreign key
            fk_match = re.search(r"foreign_key\((E-\d{3})\)", constraints)
            if fk_match:
                attr.foreign_key = fk_match.group(1)

            attributes.append(attr)

        return attributes

    def _parse_relationships(self, block: str) -> list[EntityRelationship]:
        """Parse relationships from an entity block."""
        relationships = []

        # Find Relationships section within block
        rel_section = self._extract_subsection(block, "Relationships")
        if not rel_section:
            return relationships

        for match in self.RELATIONSHIP_PATTERN.finditer(rel_section):
            rel_type = match.group(1)
            target = match.group(2)
            fk_info = match.group(3)

            foreign_key = None
            if fk_info:
                # Extract foreign key if specified
                fk_match = re.search(r"(\w+_id)", fk_info)
                if fk_match:
                    foreign_key = fk_match.group(1)

            rel = EntityRelationship(type=rel_type, target=target, foreign_key=foreign_key)
            relationships.append(rel)

        return relationships

    def _extract_stories(self, text: str) -> list[Story]:
        """Extract stories from Story Dependency Graph section."""
        stories = []

        # Find STORY DEPENDENCY GRAPH section
        story_section = self._extract_section(text, "STORY DEPENDENCY GRAPH")
        if not story_section:
            return stories

        # Split into story blocks
        story_blocks = re.split(r"(?=###\s*S-\d{3}:)", story_section)

        for block in story_blocks:
            if not block.strip():
                continue

            # Parse story header
            header_match = self.STORY_HEADER_PATTERN.search(block)
            if not header_match:
                continue

            story_id = header_match.group(1)
            story_title = header_match.group(2).strip()

            # Parse user story
            user_story = self._extract_field(block, "User Story")

            # Parse priority
            priority = self._extract_field(block, "Priority") or "P0"

            # Parse dependencies
            depends_on_str = self._extract_field(block, "Depends On")
            depends_on = []
            if depends_on_str:
                # Extract E-XXX and S-XXX patterns
                depends_on = re.findall(r"[ES]-\d{3}", depends_on_str)

            # Parse acceptance criteria
            acceptance_criteria = self._extract_acceptance_criteria(block)

            story = Story(
                id=story_id,
                title=story_title,
                priority=priority,
                status="pending",
                user_story=user_story or f"As a user, I want to {story_title.lower()}",
                acceptance_criteria=acceptance_criteria,
                depends_on=depends_on,
            )
            stories.append(story)

        return stories

    def _extract_acceptance_criteria(self, block: str) -> list[str]:
        """Extract acceptance criteria from a story block."""
        criteria = []

        # Find Acceptance Criteria section
        ac_section = self._extract_subsection(block, "Acceptance Criteria")
        if not ac_section:
            return criteria

        # Match lines starting with - or - [ ]
        for line in ac_section.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                # Remove checkbox if present
                criterion = re.sub(r"^-\s*\[.\]\s*", "", line)
                criterion = re.sub(r"^-\s*", "", criterion)
                if criterion:
                    criteria.append(criterion)

        return criteria

    def _extract_and_attach_uncertainties(self, text: str, result: ParsedMVPSpec) -> None:
        """Extract uncertainties and attach to stories."""
        # Find UNCERTAINTY REGISTRY section
        uncertainty_section = self._extract_section(text, "UNCERTAINTY REGISTRY")
        if not uncertainty_section:
            return

        # Split into ambiguity blocks
        amb_blocks = re.split(r"(?=###\s*AMB-\d{3}:)", uncertainty_section)

        for block in amb_blocks:
            if not block.strip():
                continue

            # Parse ambiguity header
            header_match = self.AMBIGUITY_HEADER_PATTERN.search(block)
            if not header_match:
                continue

            question = header_match.group(1).strip()

            # Parse story reference
            story_id = self._extract_field(block, "Story")
            if story_id:
                story_id = story_id.strip()
                # Extract just the S-XXX part
                story_match = re.search(r"S-\d{3}", story_id)
                if story_match:
                    story_id = story_match.group(0)

            # Parse classification
            classification = self._extract_field(block, "Classification") or "decision_required"
            classification = classification.strip().lower().replace(" ", "_")

            # Parse options
            options = self._extract_options(block)

            # Parse default
            default = self._extract_field(block, "Default")

            ambiguity = Ambiguity(
                question=question,
                classification=classification,
                options=options,
                default=default,
                resolved=False,
            )

            # Attach to story if found
            if story_id:
                for story in result.stories:
                    if story.id == story_id:
                        story.ambiguities.append(ambiguity)
                        break

            result.uncertainties.append((story_id or "", ambiguity))

    def _extract_options(self, block: str) -> list[str]:
        """Extract options from an ambiguity block."""
        options = []

        # Find Options section
        options_section = self._extract_subsection(block, "Options")
        if not options_section:
            return options

        for line in options_section.split("\n"):
            line = line.strip()
            # Match "- Option A: description" or just "- description"
            if line.startswith("- "):
                option = line[2:].strip()
                # Remove "Option X: " prefix if present
                option = re.sub(r"^Option\s+\w+:\s*", "", option)
                if option:
                    options.append(option)

        return options

    def _extract_section(self, text: str, section_name: str) -> str | None:
        """Extract a top-level section (## heading) from text."""
        # Pattern to match section start
        pattern = rf"##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##\s+[^#]|\n---\s*\n|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_subsection(self, block: str, subsection_name: str) -> str | None:
        """Extract a subsection (**Name:**) from a block."""
        pattern = rf"\*\*{re.escape(subsection_name)}:\*\*\s*\n(.*?)(?=\n\*\*|\n###|\Z)"
        match = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_field(self, block: str, field_name: str) -> str | None:
        """Extract a single-line field (**Name:** value) from a block."""
        pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)"
        match = re.search(pattern, block, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def has_pipeline_data(self, text: str) -> bool:
        """Check if the MVP spec contains pipeline data sections."""
        return bool(self.PIPELINE_COMPLETE_PATTERN.search(text))

    def validate_completeness(self, text: str) -> list[str]:
        """Validate that required pipeline sections are present.

        Returns list of missing sections.
        """
        missing = []

        if not self._extract_section(text, "DOMAIN MODEL"):
            missing.append("DOMAIN MODEL section")

        if not self._extract_section(text, "STORY DEPENDENCY GRAPH"):
            missing.append("STORY DEPENDENCY GRAPH section")

        # UNCERTAINTY REGISTRY is optional (may have no uncertainties)

        if not self.has_pipeline_data(text):
            missing.append("PIPELINE_DATA_COMPLETE marker")

        return missing
