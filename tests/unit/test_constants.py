# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""Unit tests for constants and configuration validation."""

from packaging.version import parse as parse_version

from mzs_tools.core.constants import (
    DEFAULT_BASE_LAYERS,
    DEFAULT_EDITING_LAYERS,
    PROJECT_MIGRATION_STEPS,
    ProjectMigrationStep,
)


class TestConstants:
    """Test constants and configuration structures."""

    def test_default_base_layers_structure(self):
        """Test DEFAULT_BASE_LAYERS structure and required fields."""
        assert isinstance(DEFAULT_BASE_LAYERS, dict)
        assert len(DEFAULT_BASE_LAYERS) > 0

        for layer_name, layer_config in DEFAULT_BASE_LAYERS.items():
            assert isinstance(layer_name, str)
            assert isinstance(layer_config, dict)

            # Check required fields
            required_fields = ["role", "type", "layer_name", "qlr_path"]
            for field in required_fields:
                assert field in layer_config, f"Missing required field '{field}' in layer '{layer_name}'"

            # Validate field values
            assert layer_config["role"] == "base"
            assert isinstance(layer_config["type"], str)
            assert isinstance(layer_config["layer_name"], str)
            assert isinstance(layer_config["qlr_path"], str)

    def test_default_editing_layers_structure(self):
        """Test DEFAULT_EDITING_LAYERS structure and required fields."""
        assert isinstance(DEFAULT_EDITING_LAYERS, dict)
        assert len(DEFAULT_EDITING_LAYERS) > 0

        for layer_name, layer_config in DEFAULT_EDITING_LAYERS.items():
            assert isinstance(layer_name, str)
            assert isinstance(layer_config, dict)

            # Check required fields
            required_fields = ["role", "type", "layer_name", "qlr_path"]
            for field in required_fields:
                assert field in layer_config, f"Missing required field '{field}' in layer '{layer_name}'"

            # Validate field values
            assert layer_config["role"] == "editing"
            assert isinstance(layer_config["type"], str)
            assert isinstance(layer_config["layer_name"], str)
            assert isinstance(layer_config["qlr_path"], str)

    def test_layer_types_are_valid(self):
        """Test that layer types are valid."""
        valid_types = ["vector", "raster", "service_group", "wms", "wfs", "table", "group"]

        all_layers = {**DEFAULT_BASE_LAYERS, **DEFAULT_EDITING_LAYERS}

        for layer_name, layer_config in all_layers.items():
            layer_type = layer_config.get("type")
            assert layer_type in valid_types, f"Invalid layer type '{layer_type}' in layer '{layer_name}'"

    def test_qlr_paths_have_extension(self):
        """Test that QLR paths have the correct extension."""
        all_layers = {**DEFAULT_BASE_LAYERS, **DEFAULT_EDITING_LAYERS}

        for layer_name, layer_config in all_layers.items():
            qlr_path = layer_config.get("qlr_path", "")
            assert qlr_path.endswith(".qlr"), f"QLR path '{qlr_path}' in layer '{layer_name}' should end with .qlr"

    def test_layer_names_are_not_empty(self):
        """Test that layer names are not empty."""
        all_layers = {**DEFAULT_BASE_LAYERS, **DEFAULT_EDITING_LAYERS}

        for layer_name, layer_config in all_layers.items():
            display_name = layer_config.get("layer_name", "")
            assert len(display_name.strip()) > 0, f"Layer name is empty for layer '{layer_name}'"

    def test_value_relations_structure(self):
        """Test value relations structure in editing layers."""
        for layer_name, layer_config in DEFAULT_EDITING_LAYERS.items():
            if "value_relations" in layer_config:
                value_relations = layer_config["value_relations"]
                assert isinstance(value_relations, dict)

                for field_name, relation_config in value_relations.items():
                    assert isinstance(field_name, str)
                    assert isinstance(relation_config, dict)

                    # Check required fields for value relations
                    required_fields = ["relation_table", "relation_key", "relation_value"]
                    for field in required_fields:
                        assert field in relation_config, (
                            f"Missing field '{field}' in value relation '{field_name}' for layer '{layer_name}'"
                        )

    def test_specific_layers_exist(self):
        """Test that specific expected layers exist."""
        # Test base layers
        expected_base_layers = ["comune_progetto", "comuni", "basemap"]
        for layer in expected_base_layers:
            assert layer in DEFAULT_BASE_LAYERS, f"Expected base layer '{layer}' not found"

        # Test editing layers
        expected_editing_layers = ["tavole", "sito_puntuale"]
        for layer in expected_editing_layers:
            assert layer in DEFAULT_EDITING_LAYERS, f"Expected editing layer '{layer}' not found"

    def test_groups_are_string_or_none(self):
        """Test that group values are either string or None."""
        all_layers = {**DEFAULT_BASE_LAYERS, **DEFAULT_EDITING_LAYERS}

        for layer_name, layer_config in all_layers.items():
            group = layer_config.get("group")
            assert group is None or isinstance(group, str), f"Group in layer '{layer_name}' should be string or None"

    def test_geom_name_in_vector_layers(self):
        """Test that vector layers with geom_name have valid configuration."""
        all_layers = {**DEFAULT_BASE_LAYERS, **DEFAULT_EDITING_LAYERS}

        for layer_name, layer_config in all_layers.items():
            if layer_config.get("type") == "vector" and "geom_name" in layer_config:
                geom_name = layer_config["geom_name"]
                assert isinstance(geom_name, str)
                assert len(geom_name.strip()) > 0, f"Geometry name is empty for layer '{layer_name}'"


# ---------------------------------------------------------------------------
# Helper function extracted from MzSProjectManager._get_incremental_migration_flags
# tested here as pure Python (no QGIS dependency)
# ---------------------------------------------------------------------------


def _compute_migration_flags(old_version: str, steps) -> dict:
    """Pure-Python replica of MzSProjectManager._get_incremental_migration_flags."""
    flags = {"add_base_layers": False, "add_editing_layers": False, "add_layout_groups": False}
    parsed_old = parse_version(old_version)
    for step in steps:
        if parsed_old < parse_version(step.version):
            flags["add_base_layers"] = flags["add_base_layers"] or step.add_base_layers
            flags["add_editing_layers"] = flags["add_editing_layers"] or step.add_editing_layers
            flags["add_layout_groups"] = flags["add_layout_groups"] or step.add_layout_groups
    return flags


class TestProjectMigrationSteps:
    """Tests for the PROJECT_MIGRATION_STEPS registry and migration flag logic."""

    def test_steps_are_ordered_ascending(self):
        """Migration steps must be ordered from oldest to newest version."""
        versions = [parse_version(s.version) for s in PROJECT_MIGRATION_STEPS]
        assert versions == sorted(versions), "PROJECT_MIGRATION_STEPS must be ordered by version ascending"

    def test_steps_have_at_least_one_flag(self):
        """Every migration step must set at least one add_* flag."""
        for step in PROJECT_MIGRATION_STEPS:
            assert step.add_base_layers or step.add_editing_layers or step.add_layout_groups, (
                f"Step '{step.version}' sets no flags — it would be a no-op"
            )

    def test_flags_for_version_2_0_0(self):
        """Project at 2.0.0 should get editing + layout update (both steps apply)."""
        flags = _compute_migration_flags("2.0.0", PROJECT_MIGRATION_STEPS)
        assert flags["add_base_layers"] is False
        assert flags["add_editing_layers"] is True
        assert flags["add_layout_groups"] is True

    def test_flags_for_version_2_0_1(self):
        """Project at 2.0.1 should get layout-only update (only 2.0.2 step applies)."""
        flags = _compute_migration_flags("2.0.1", PROJECT_MIGRATION_STEPS)
        assert flags["add_base_layers"] is False
        assert flags["add_editing_layers"] is False
        assert flags["add_layout_groups"] is True

    def test_flags_for_version_2_0_2(self):
        """Project at 2.0.2 should require no update (no steps apply)."""
        flags = _compute_migration_flags("2.0.2", PROJECT_MIGRATION_STEPS)
        assert not any(flags.values()), "No migration should be needed for version 2.0.2"

    def test_flags_for_current_version_no_action(self):
        """A project at the latest registered version should require no update."""
        latest_threshold = max(parse_version(s.version) for s in PROJECT_MIGRATION_STEPS)
        flags = _compute_migration_flags(str(latest_threshold), PROJECT_MIGRATION_STEPS)
        assert not any(flags.values()), "No migration should be needed for the latest threshold version"

    def test_custom_steps_union_of_flags(self):
        """Flag union: two applicable steps should OR their flags correctly."""
        custom_steps = [
            ProjectMigrationStep(version="1.0.0", description="base only", add_base_layers=True),
            ProjectMigrationStep(version="2.0.0", description="editing only", add_editing_layers=True),
        ]
        flags = _compute_migration_flags("0.9.0", custom_steps)
        assert flags["add_base_layers"] is True
        assert flags["add_editing_layers"] is True
        assert flags["add_layout_groups"] is False

    def test_custom_steps_partial_match(self):
        """Only steps with version > old_version contribute their flags."""
        custom_steps = [
            ProjectMigrationStep(version="1.0.0", description="base only", add_base_layers=True),
            ProjectMigrationStep(version="2.0.0", description="editing only", add_editing_layers=True),
        ]
        flags = _compute_migration_flags("1.5.0", custom_steps)
        assert flags["add_base_layers"] is False
        assert flags["add_editing_layers"] is True
        assert flags["add_layout_groups"] is False

    def test_semantic_version_comparison_not_lexicographic(self):
        """parse_version must handle '2.0.10' > '2.0.9' correctly (not lexicographic)."""
        custom_steps = [
            ProjectMigrationStep(version="2.0.10", description="layout update", add_layout_groups=True),
        ]
        # 2.0.9 < 2.0.10 → step should apply
        flags_old = _compute_migration_flags("2.0.9", custom_steps)
        assert flags_old["add_layout_groups"] is True

        # 2.0.10 is NOT < 2.0.10 → step should NOT apply
        flags_exact = _compute_migration_flags("2.0.10", custom_steps)
        assert flags_exact["add_layout_groups"] is False
