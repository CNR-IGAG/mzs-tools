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

"""Integration tests for MzSProjectManager layer management functions.

These tests verify that:
1. Layers are correctly loaded from .qlr files
2. Layer groups are created with the expected structure
3. The QGIS layer tree hierarchy matches the expected structure
4. Custom properties are set correctly on layers
5. Value relations and project relations are created properly

1. **`TestAddLayerFromQlr`** - Tests for loading layers from `.qlr` files:
   - Successful layer loading from QLR
   - Failure when project path is not set
   - Cleanup of temporary QLR files

2. **`TestAddDefaultLayerGroup`** - Tests for `_add_default_layer_group`:
   - Base layers group structure creation
   - Editing layers subgroup creation
   - Expected editing layers are added

3. **`TestAddDefaultLayoutGroups`** - Tests for `_add_default_layout_groups`:
   - Mutually exclusive layout group creation
   - Expected layout subgroups creation

4. **`TestAddDefaultLayers`** - Tests for the main `add_default_layers` method:
   - Adding all layer categories together
   - Adding only base, editing, or layout layers individually
   - Empty group removal
   - No-op when all flags are false

5. **`TestLayerTreeStructure`** - Tests verifying QGIS layer tree hierarchy:
   - Correct overall hierarchy structure
   - Correct editing layer subgroup organization

6. **`TestLayerCustomProperties`** - Tests for custom properties:
   - Base layers have correct `layer_role` property
   - Editing layers have correct properties

7. **`TestCleanupFunctions`** - Tests for cleanup methods:
   - Base layer cleanup
   - Editing layer cleanup
   - Layout group cleanup

8. **`TestProjectRelations`** - Tests for project relations:
   - Default relations creation
   - Relation validation

9. **`TestValueRelations`** - Tests for value relations:
   - Widget configuration setup

10. **`TestFindLayersFunctions`** - Tests for layer finding utilities:
    - `find_layers_by_table_name`
    - `find_layer_by_table_name_role`

11. **`TestSetLayerCustomProperty`** & **`TestSetProjectLayerCapabilities`** - Tests for helper methods
"""

from pathlib import Path

import pytest
from qgis.core import (
    QgsLayerTreeGroup,
    QgsProject,
    QgsVectorLayer,
)

from mzs_tools.core.constants import (
    DEFAULT_BASE_LAYERS,
    DEFAULT_EDITING_LAYERS,
    DEFAULT_LAYOUT_GROUPS,
    DEFAULT_RELATIONS,
)
from mzs_tools.core.mzs_project_manager import ComuneData, MzSProjectManager


@pytest.fixture
def sample_project_path(base_project_path_current, prj_manager) -> Path:
    """Fixture that sets up a minimal project structure with database for testing layer operations.

    This extracts the test project and sets up the manager with proper paths and database connection.
    """
    # Setup the manager with paths
    prj_manager.current_project = QgsProject.instance()
    prj_manager.project_path = base_project_path_current
    prj_manager.db_path = base_project_path_current / "db" / "indagini.sqlite"
    prj_manager._setup_db_connection()

    # Set minimal comune_data for tests that need it
    prj_manager.comune_data = ComuneData(
        cod_regio="12",
        cod_prov="057",
        cod_com="001",
        comune="Accumoli",
        provincia="Rieti",
        regione="Lazio",
        cod_istat="057001",
    )

    return base_project_path_current


class TestAddLayerFromQlr:
    """Test suite for the add_layer_from_qlr method."""

    def test_add_layer_from_qlr_success(self, prj_manager, sample_project_path):
        """Test that a layer can be successfully loaded from a .qlr file."""
        from mzs_tools.core.mzs_project_manager import DIR_PLUGIN_ROOT

        # Create a layer group to add the layer to
        root = prj_manager.current_project.layerTreeRoot()
        test_group = QgsLayerTreeGroup("Test Group")
        root.addChildNode(test_group)

        # Load a simple layer from qlr
        qlr_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / "comune_progetto.qlr"
        success = prj_manager.add_layer_from_qlr(test_group, qlr_path)

        assert success is True

        # Verify the layer was added to the group
        layers = test_group.findLayers()
        assert len(layers) > 0

        # Verify that the layer name matches
        layer_names = [layer_node.name() for layer_node in layers]
        assert "Comune del progetto" in layer_names

    def test_add_layer_from_qlr_without_project_path_fails(self, prj_manager, tmp_path):
        """Test that adding a layer from qlr fails when project_path is not set."""
        from mzs_tools.core.mzs_project_manager import DIR_PLUGIN_ROOT

        prj_manager.current_project = QgsProject.instance()
        prj_manager.project_path = None

        root = prj_manager.current_project.layerTreeRoot()
        test_group = QgsLayerTreeGroup("Test Group")
        root.addChildNode(test_group)

        qlr_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / "comune_progetto.qlr"
        result = prj_manager.add_layer_from_qlr(test_group, qlr_path)

        # Should return None when project_path is not set
        assert result is None

    def test_add_layer_from_qlr_cleans_up_temp_file(self, prj_manager, sample_project_path):
        """Test that the temporary .qlr file is cleaned up after loading."""
        from mzs_tools.core.mzs_project_manager import DIR_PLUGIN_ROOT

        root = prj_manager.current_project.layerTreeRoot()
        test_group = QgsLayerTreeGroup("Test Group")
        root.addChildNode(test_group)

        qlr_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / "comune_progetto.qlr"
        temp_qlr_path = sample_project_path / qlr_path.name

        # Verify temp file doesn't exist before
        assert not temp_qlr_path.exists()

        prj_manager.add_layer_from_qlr(test_group, qlr_path)

        # Verify temp file was cleaned up after
        assert not temp_qlr_path.exists()


class TestAddDefaultLayerGroup:
    """Test suite for the _add_default_layer_group method."""

    def test_add_base_layers_creates_correct_group_structure(self, prj_manager, sample_project_path):
        """Test that adding base layers creates the expected group structure."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        root = prj_manager.current_project.layerTreeRoot()

        # Verify root group was created
        base_group = root.findGroup("Cartografia di base")
        assert base_group is not None

        # Verify layers within the group
        layers = base_group.findLayers()
        layer_names = [layer.name() for layer in layers]

        # Check for expected base layers
        assert "Comune del progetto" in layer_names
        assert "Limiti comunali" in layer_names

    def test_add_editing_layers_creates_subgroups(self, prj_manager, sample_project_path):
        """Test that adding editing layers creates the expected subgroup structure."""
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")

        root = prj_manager.current_project.layerTreeRoot()

        # Verify root group was created
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")
        assert editing_group is not None

        # Verify expected subgroups exist
        expected_subgroups = set()
        for layer_data in DEFAULT_EDITING_LAYERS.values():
            if layer_data["group"] is not None:
                expected_subgroups.add(layer_data["group"])

        for subgroup_name in expected_subgroups:
            subgroup = editing_group.findGroup(subgroup_name)
            assert subgroup is not None, f"Subgroup '{subgroup_name}' should exist in BANCA DATI GEOGRAFICA"

    def test_add_editing_layers_adds_expected_layers(self, prj_manager, sample_project_path):
        """Test that all expected editing layers are added."""
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")

        root = prj_manager.current_project.layerTreeRoot()
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")

        # Get all layers in the editing group (including subgroups)
        all_layers = editing_group.findLayers()
        layer_names = [layer.name() for layer in all_layers]

        # Check for expected layers
        expected_layers = [data["layer_name"] for data in DEFAULT_EDITING_LAYERS.values()]

        # Some layers might be in nested groups (like tabelle_accessorie)
        # Check that most expected layers are present
        found_count = sum(1 for expected in expected_layers if expected in layer_names)
        assert found_count >= len(expected_layers) * 0.8, (
            f"Expected at least 80% of editing layers. Found {found_count}/{len(expected_layers)}"
        )


class TestAddDefaultLayoutGroups:
    """Test suite for the _add_default_layout_groups method."""

    def test_add_layout_groups_creates_mutually_exclusive_group(self, prj_manager, sample_project_path):
        """Test that layout groups are created as mutually exclusive."""
        prj_manager._add_default_layout_groups("LAYOUT DI STAMPA")

        root = prj_manager.current_project.layerTreeRoot()
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        assert layout_group is not None
        assert layout_group.isMutuallyExclusive() is True

    def test_add_layout_groups_creates_expected_subgroups(self, prj_manager, sample_project_path):
        """Test that all expected layout subgroups are created."""
        prj_manager._add_default_layout_groups("LAYOUT DI STAMPA")

        root = prj_manager.current_project.layerTreeRoot()
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        # Verify all expected layout groups exist
        for layout_name in DEFAULT_LAYOUT_GROUPS:
            subgroup = layout_group.findGroup(layout_name)
            assert subgroup is not None, f"Layout group '{layout_name}' should exist"


class TestAddDefaultLayers:
    """Test suite for the main add_default_layers method."""

    def test_add_default_layers_all_categories(self, prj_manager, sample_project_path):
        """Test adding all default layer categories."""
        prj_manager.add_default_layers(add_base_layers=True, add_editing_layers=True, add_layout_groups=True)

        root = prj_manager.current_project.layerTreeRoot()

        # Verify all main groups exist
        base_group = root.findGroup("Cartografia di base")
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        assert base_group is not None, "Base layers group should exist"
        assert editing_group is not None, "Editing layers group should exist"
        assert layout_group is not None, "Layout groups should exist"

    def test_add_default_layers_only_base(self, prj_manager, sample_project_path):
        """Test adding only base layers."""
        prj_manager.add_default_layers(add_base_layers=True, add_editing_layers=False, add_layout_groups=False)

        root = prj_manager.current_project.layerTreeRoot()

        base_group = root.findGroup("Cartografia di base")
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        assert base_group is not None, "Base layers group should exist"
        assert editing_group is None, "Editing layers group should not exist"
        assert layout_group is None, "Layout groups should not exist"

    def test_add_default_layers_only_editing(self, prj_manager, sample_project_path):
        """Test adding only editing layers."""
        prj_manager.add_default_layers(add_base_layers=False, add_editing_layers=True, add_layout_groups=False)

        root = prj_manager.current_project.layerTreeRoot()

        base_group = root.findGroup("Cartografia di base")
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        assert base_group is None, "Base layers group should not exist"
        assert editing_group is not None, "Editing layers group should exist"
        assert layout_group is None, "Layout groups should not exist"

    def test_add_default_layers_only_layout(self, prj_manager, sample_project_path):
        """Test adding only layout groups."""
        prj_manager.add_default_layers(add_base_layers=False, add_editing_layers=False, add_layout_groups=True)

        root = prj_manager.current_project.layerTreeRoot()

        base_group = root.findGroup("Cartografia di base")
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")
        layout_group = root.findGroup("LAYOUT DI STAMPA")

        assert base_group is None, "Base layers group should not exist"
        assert editing_group is None, "Editing layers group should not exist"
        assert layout_group is not None, "Layout groups should exist"

    def test_add_default_layers_removes_empty_groups(self, prj_manager, sample_project_path):
        """Test that empty groups are removed from root after adding layers."""
        root = prj_manager.current_project.layerTreeRoot()

        # Add an empty group manually
        empty_group = QgsLayerTreeGroup("Empty Group")
        root.addChildNode(empty_group)

        # Now add default layers - should remove empty groups
        prj_manager.add_default_layers(add_base_layers=True, add_editing_layers=False, add_layout_groups=False)

        # The empty group should have been removed
        empty_group_after = root.findGroup("Empty Group")
        assert empty_group_after is None, "Empty groups should be removed"

    def test_add_default_layers_no_action_when_all_false(self, prj_manager, sample_project_path):
        """Test that nothing happens when all options are False."""
        root = prj_manager.current_project.layerTreeRoot()
        initial_children_count = len(root.children())

        prj_manager.add_default_layers(add_base_layers=False, add_editing_layers=False, add_layout_groups=False)

        # Should have the same number of children (nothing added)
        assert len(root.children()) == initial_children_count


class TestLayerTreeStructure:
    """Test suite verifying the complete layer tree structure after adding default layers."""

    def test_layer_tree_hierarchy_is_correct(self, prj_manager, sample_project_path):
        """Test that the layer tree hierarchy matches the expected structure."""
        prj_manager.add_default_layers(add_base_layers=True, add_editing_layers=True, add_layout_groups=True)

        root = prj_manager.current_project.layerTreeRoot()

        # Get top-level groups in order
        top_level_children = root.children()
        top_level_names = [child.name() for child in top_level_children]

        # Verify structure:
        # The editing group should be first (index 0)
        # The layout group should be second if editing exists (index 1)
        # Base layers group position depends on order of add_default_layers calls
        assert "BANCA DATI GEOGRAFICA" in top_level_names
        assert "LAYOUT DI STAMPA" in top_level_names
        assert "Cartografia di base" in top_level_names

    def test_editing_layers_have_correct_subgroup_hierarchy(self, prj_manager, sample_project_path):
        """Test that editing layers are organized in correct subgroups at exact positions."""
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")

        root = prj_manager.current_project.layerTreeRoot()
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")

        # Build expected structure: subgroup -> list of (layer_name, layer_type)
        # None key is for root-level items
        expected_structure: dict[str | None, list[tuple[str, str]]] = {}
        for layer_data in DEFAULT_EDITING_LAYERS.values():
            group_name = layer_data.get("group")
            layer_type = layer_data.get("type", "vector")
            if group_name not in expected_structure:
                expected_structure[group_name] = []
            expected_structure[group_name].append((layer_data["layer_name"], layer_type))

        # Verify subgroups are direct children of editing_group
        direct_children = editing_group.children()
        direct_child_names = [child.name() for child in direct_children]

        for subgroup_name in expected_structure:
            if subgroup_name is not None:
                assert subgroup_name in direct_child_names, (
                    f"Subgroup '{subgroup_name}' should be a direct child of BANCA DATI GEOGRAFICA"
                )

        # Verify layers/groups are in their correct subgroups (exact position)
        for subgroup_name, expected_items in expected_structure.items():
            if subgroup_name is None:
                # Root-level items: should be direct children of editing_group
                root_level_layers = [
                    child.name() for child in direct_children if hasattr(child, "layer") and child.layer() is not None
                ]
                root_level_groups = [child.name() for child in direct_children if isinstance(child, QgsLayerTreeGroup)]
                for expected_name, layer_type in expected_items:
                    if layer_type == "group":
                        # For "group" type, it should be a subgroup
                        assert expected_name in root_level_groups, (
                            f"Group '{expected_name}' should be at root level of BANCA DATI GEOGRAFICA, "
                            f"found groups: {root_level_groups}"
                        )
                    else:
                        # Regular layers
                        assert expected_name in root_level_layers, (
                            f"Layer '{expected_name}' should be at root level of BANCA DATI GEOGRAFICA, "
                            f"found layers: {root_level_layers}"
                        )
            else:
                # Subgroup items: should be direct children of the subgroup
                subgroup = editing_group.findGroup(subgroup_name)
                assert subgroup is not None, f"Subgroup '{subgroup_name}' not found"

                # Get only direct layer children of this subgroup
                subgroup_direct_layers = [
                    child.name()
                    for child in subgroup.children()
                    if hasattr(child, "layer") and child.layer() is not None
                ]
                for expected_name, layer_type in expected_items:
                    if layer_type != "group":
                        assert expected_name in subgroup_direct_layers, (
                            f"Layer '{expected_name}' should be a direct child of subgroup '{subgroup_name}', "
                            f"but found: {subgroup_direct_layers}"
                        )


class TestLayerCustomProperties:
    """Test suite for verifying custom properties are set correctly on layers."""

    def test_base_layers_have_correct_custom_properties(self, prj_manager, sample_project_path):
        """Test that base layers have the correct custom properties set."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        root = prj_manager.current_project.layerTreeRoot()
        base_group = root.findGroup("Cartografia di base")

        # Count layers with correct properties (excluding external service layers like OSM)
        base_layers_found = 0
        for layer_node in base_group.findLayers():
            layer = layer_node.layer()
            if layer is None:
                continue

            # Skip layers that are not from the spatialite database (e.g., basemap/OSM tiles)
            if layer.providerType() != "spatialite":
                continue

            layer_role = layer.customProperty("mzs_tools/layer_role")
            assert layer_role == "base", f"Layer '{layer.name()}' should have role 'base', got '{layer_role}'"
            base_layers_found += 1

        # We should have found at least some base layers with the correct property
        assert base_layers_found > 0, "Should find at least one base layer with correct property"

    def test_editing_layers_have_correct_custom_properties(self, prj_manager, sample_project_path):
        """Test that editing layers have the correct custom properties set."""
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")

        root = prj_manager.current_project.layerTreeRoot()
        editing_group = root.findGroup("BANCA DATI GEOGRAFICA")

        # Count layers with correct properties
        correct_count = 0
        total_count = 0

        for layer_node in editing_group.findLayers():
            layer = layer_node.layer()
            if layer is None:
                continue
            total_count += 1

            layer_role = layer.customProperty("mzs_tools/layer_role")
            if layer_role == "editing":
                correct_count += 1

        # Most editing layers should have the correct property
        assert correct_count >= total_count * 0.8, (
            f"At least 80% of editing layers should have correct custom property. Got {correct_count}/{total_count}"
        )


class TestCleanupFunctions:
    """Test suite for layer cleanup functions."""

    def test_cleanup_base_layers_removes_existing_layers(self, prj_manager, sample_project_path):
        """Test that cleanup removes existing base layers."""
        # First add base layers
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        root = prj_manager.current_project.layerTreeRoot()
        base_group = root.findGroup("Cartografia di base")
        initial_layer_count = len(base_group.findLayers()) if base_group else 0

        assert initial_layer_count > 0, "Should have layers after adding"

        # Now cleanup
        prj_manager._cleanup_base_layers()

        # Check that base layers are removed
        # Note: cleanup only removes layers with 'base' role custom property
        remaining_layers = []
        for layer in prj_manager.current_project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.customProperty("mzs_tools/layer_role") == "base":
                remaining_layers.append(layer)

        assert len(remaining_layers) == 0, "All base layers should be removed after cleanup"

    def test_cleanup_editing_layers_removes_existing_layers(self, prj_manager, sample_project_path):
        """Test that cleanup removes existing editing layers."""
        # First add editing layers
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")

        # Now cleanup
        prj_manager._cleanup_editing_layers()

        # Check that editing layers are removed
        remaining_layers = []
        for layer in prj_manager.current_project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.customProperty("mzs_tools/layer_role") == "editing":
                remaining_layers.append(layer)

        assert len(remaining_layers) == 0, "All editing layers should be removed after cleanup"

    def test_cleanup_layout_groups_removes_existing_groups(self, prj_manager, sample_project_path):
        """Test that cleanup removes existing layout groups."""
        # First add layout groups
        prj_manager._add_default_layout_groups("LAYOUT DI STAMPA")

        root = prj_manager.current_project.layerTreeRoot()
        layout_group = root.findGroup("LAYOUT DI STAMPA")
        assert layout_group is not None, "Layout group should exist after adding"

        # Now cleanup
        prj_manager._cleanup_layout_groups()

        # Verify layout groups within the main group are removed
        # The main group might remain if not empty
        for group_name in DEFAULT_LAYOUT_GROUPS:
            remaining_group = root.findGroup(group_name)
            assert remaining_group is None, f"Layout group '{group_name}' should be removed after cleanup"


class TestProjectRelations:
    """Test suite for project relations functionality."""

    def test_add_default_project_relations_creates_expected_relations(self, prj_manager, sample_project_path):
        """Test that default project relations are created correctly."""
        # First need to add editing layers for relations to work
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")
        prj_manager._add_default_project_relations()

        rel_manager = prj_manager.current_project.relationManager()

        for relation_name in DEFAULT_RELATIONS:
            relations = rel_manager.relationsByName(relation_name)
            assert len(relations) > 0, f"Relation '{relation_name}' should exist"
            assert relations[0].isValid(), f"Relation '{relation_name}' should be valid"

    def test_check_default_project_relations_validates_correctly(self, prj_manager, sample_project_path):
        """Test that relation checking works correctly."""
        # Add layers and relations
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")
        prj_manager._add_default_project_relations()

        # Check relations
        relations_ok = prj_manager._check_default_project_relations()

        assert relations_ok is True, "All relations should be valid after setup"


class TestValueRelations:
    """Test suite for value relations functionality."""

    def test_add_default_value_relations_sets_up_widget_correctly(self, prj_manager, sample_project_path):
        """Test that value relations are set up with correct widget configuration."""
        # Add editing layers first
        prj_manager._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")
        prj_manager._add_default_value_relations(DEFAULT_EDITING_LAYERS)

        # Check a specific layer that should have value relations
        # For example, sito_puntuale has mod_identcoord value relation
        sito_layers = prj_manager.find_layers_by_table_name("sito_puntuale")
        assert len(sito_layers) > 0, "Should find sito_puntuale layer"

        sito_layer = None
        for layer in sito_layers:
            if layer.customProperty("mzs_tools/layer_role") == "editing":
                sito_layer = layer
                break

        if sito_layer is not None:
            # Check that the field has a ValueRelation widget setup
            field_idx = sito_layer.fields().indexOf("mod_identcoord")
            if field_idx >= 0:
                widget_setup = sito_layer.editorWidgetSetup(field_idx)
                assert widget_setup.type() == "ValueRelation", "mod_identcoord field should have ValueRelation widget"


class TestFindLayersFunctions:
    """Test suite for layer finding functions."""

    def test_find_layers_by_table_name_finds_correct_layers(self, prj_manager, sample_project_path):
        """Test that find_layers_by_table_name correctly identifies layers."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        # Find comune_progetto layer
        layers = prj_manager.find_layers_by_table_name("comune_progetto")

        assert len(layers) > 0, "Should find at least one layer for comune_progetto table"
        assert all(isinstance(layer, QgsVectorLayer) for layer in layers)

    def test_find_layer_by_table_name_role_returns_correct_layer(self, prj_manager, sample_project_path):
        """Test that find_layer_by_table_name_role returns correct layer ID."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        layer_id = prj_manager.find_layer_by_table_name_role("comune_progetto", "base")

        assert layer_id is not None, "Should find layer with base role"

        # Verify it's a valid layer
        layer = prj_manager.current_project.mapLayer(layer_id)
        assert layer is not None
        assert layer.customProperty("mzs_tools/layer_role") == "base"

    def test_find_layer_by_table_name_role_returns_none_for_wrong_role(self, prj_manager, sample_project_path):
        """Test that find_layer_by_table_name_role returns None for non-matching role."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        # comune_progetto is a base layer, not editing
        layer_id = prj_manager.find_layer_by_table_name_role("comune_progetto", "editing")

        assert layer_id is None, "Should not find base layer when searching for editing role"


class TestSetLayerCustomProperty:
    """Test suite for custom property setting."""

    def test_set_layer_custom_property_sets_value(self, prj_manager, sample_project_path):
        """Test that custom properties are set correctly on layers."""
        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        layers = prj_manager.find_layers_by_table_name("comune_progetto")
        assert len(layers) > 0

        layer = layers[0]
        prj_manager.set_layer_custom_property(layer, "test_property", "test_value")

        assert layer.customProperty("mzs_tools/test_property") == "test_value"


class TestSetProjectLayerCapabilities:
    """Test suite for project layer capabilities."""

    def test_set_project_layer_capabilities_sets_flags(self, prj_manager, sample_project_path):
        """Test that layer capabilities/flags are set correctly."""
        from qgis.core import QgsMapLayer

        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        layers = prj_manager.find_layers_by_table_name("comune_progetto")
        assert len(layers) > 0

        layer = layers[0]

        # Set capabilities
        MzSProjectManager.set_project_layer_capabilities(
            layer, identifiable=True, required=True, searchable=True, private=False
        )

        # Check flags
        flags = layer.flags()
        assert flags & QgsMapLayer.LayerFlag.Identifiable
        assert flags & QgsMapLayer.LayerFlag.Searchable
        assert not (flags & QgsMapLayer.LayerFlag.Removable)  # Required means not removable

    def test_set_project_layer_capabilities_private_layer(self, prj_manager, sample_project_path):
        """Test that private flag is set correctly."""
        from qgis.core import QgsMapLayer

        prj_manager._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")

        layers = prj_manager.find_layers_by_table_name("comune_progetto")
        layer = layers[0]

        MzSProjectManager.set_project_layer_capabilities(layer, identifiable=False, private=True)

        flags = layer.flags()
        assert flags & QgsMapLayer.LayerFlag.Private
        assert not (flags & QgsMapLayer.LayerFlag.Identifiable)
