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

from mzs_tools.core.constants import (
    DEFAULT_BASE_LAYERS,
    DEFAULT_EDITING_LAYERS,
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
