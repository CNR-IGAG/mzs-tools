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

import logging
import os
import shutil

from qgis.core import QgsProject, QgsTask, QgsVectorLayer, QgsWkbTypes, edit

from ..__about__ import DEBUG_MODE
from ..core.mzs_project_manager import MzSProjectManager


class ImportShapefileTask(QgsTask):
    def __init__(
        self,
        proj_paths: dict,
        shapefile_name: str,
    ):
        super().__init__(f"Import shapefile {shapefile_name}", QgsTask.Flag.CanCancel)

        self.iterations = 0
        self.exception = None

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.import_data")

        self.prj_manager = MzSProjectManager.instance()

        self.proj_paths = proj_paths
        self.shapefile_name = shapefile_name

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        if DEBUG_MODE:
            self.logger.warning(f"\n{'#' * 50}\n# Running in DEBUG mode! Data will be DESTROYED! #\n{'#' * 50}")

        self.iterations = 0

        try:
            shapefile_path = self.proj_paths[self.shapefile_name]["path"]
            db_table_name = self.proj_paths[self.shapefile_name]["table"]
            dest_layer_id = self.prj_manager.find_layer_by_table_name_role(db_table_name, "editing")
            dest_layer = self.prj_manager.current_project.mapLayer(dest_layer_id)

            if self.shapefile_name in ["MS23-Stab.shp", "MS23-Instab.shp"]:
                # copy spettri files to the project folder
                spettri_path = self.proj_paths["Spettri"]["path"]
                if spettri_path and spettri_path.exists():
                    shutil.copytree(
                        spettri_path, self.prj_manager.project_path / "Allegati" / "Spettri", dirs_exist_ok=True
                    )

            source_layer = QgsVectorLayer(str(shapefile_path), self.shapefile_name, "ogr")
            common_fields = self.attribute_adaptor(dest_layer, source_layer)
            source_features = source_layer.getFeatures()
            result = self.insert_features(source_features, dest_layer, common_fields)
        except Exception as e:
            self.exception = e
            return False

        return result

    def finished(self, result):
        if result:
            self.logger.info(f"Task {self.description()} completed with {self.iterations} iterations")
        else:
            if self.exception is None:
                self.logger.warning(f"Task {self.description()} was canceled")
            else:
                self.logger.error(f"Task {self.description()} failed: {self.exception}")
                raise self.exception

    def cancel(self):
        self.logger.warning(f"Task {self.description()} was cancelled")
        super().cancel()

    def attribute_adaptor(self, targetLayer, sourceLayer):
        # Create case-insensitive mapping dictionaries
        targetLayerFieldsMap = {}  # lowercase -> actual name
        sourceLayerFieldsMap = {}  # lowercase -> actual name
        primaryKeyList = []

        for index in targetLayer.dataProvider().pkAttributeIndexes():
            primaryKeyList.append(targetLayer.dataProvider().fields().at(index).name())

        for field in sourceLayer.dataProvider().fields().toList():
            sourceLayerFieldsMap[field.name().lower()] = field.name()

        for field in targetLayer.dataProvider().fields().toList():
            targetLayerFieldsMap[field.name().lower()] = field.name()

        # Find common fields (case-insensitive) and exclude primary keys
        primaryKeyListLower = [pk.lower() for pk in primaryKeyList]
        commonFieldsLower = set(sourceLayerFieldsMap.keys()) & set(targetLayerFieldsMap.keys())
        commonFieldsLower = commonFieldsLower - set(primaryKeyListLower)

        # Return a dict mapping source field names to target field names
        commonFields = {
            sourceLayerFieldsMap[field_lower]: targetLayerFieldsMap[field_lower] for field_lower in commonFieldsLower
        }

        return commonFields

    def attribute_fill(self, qgsFeature, targetLayer, commonFields):
        featureFields = {}

        # Build a mapping of source field names (case-insensitive) for special field handling
        for field in qgsFeature.fields().toList():
            field_name_lower = field.name().lower()

            # Handle special field name mappings (case-insensitive)
            if field_name_lower == "desc_modco":
                featureFields["desc_modcoord"] = qgsFeature[field.name()]
            elif field_name_lower == "mod_identc":
                featureFields["mod_identcoord"] = qgsFeature[field.name()]
            elif field_name_lower == "ub_prov":
                featureFields["ubicazione_prov"] = qgsFeature[field.name()]
            elif field_name_lower == "ub_com":
                featureFields["ubicazione_com"] = qgsFeature[field.name()]
            else:
                featureFields[field.name()] = qgsFeature[field.name()]

        qgsFeature.setFields(targetLayer.dataProvider().fields())
        if commonFields:
            # commonFields is now a dict: {source_field_name: target_field_name}
            for source_field, target_field in commonFields.items():
                qgsFeature[target_field] = featureFields[source_field]

        return qgsFeature

    def insert_features(self, source_features, dest_layer: QgsVectorLayer, common_fields):
        feature_list = []

        self.logger.info(f"Inserting features from {self.shapefile_name} to {dest_layer.name()}")

        features_are_3d = False
        for feature in source_features:
            geometry = feature.geometry()

            # Skip features with no geometry
            if geometry.isNull():
                self.logger.warning(f"Feature ID {feature.id()} has no geometry, skipping feature.")
                continue

            # Discard polygons with area < 1
            if geometry.type() == QgsWkbTypes.GeometryType.PolygonGeometry:
                if geometry.area() < 1:
                    self.logger.warning(
                        f"Polygon with area < 1 detected in feature ID {feature.id()}, skipping feature."
                    )
                    continue

            # Drop Z values if present
            if geometry.get().is3D():
                if not features_are_3d:
                    features_are_3d = True
                    self.logger.warning(f"3D features detected in {self.shapefile_name}! Z values will be dropped.")
                geometry.get().dropZValue()
                feature.setGeometry(geometry)

            # Check if geometry is valid
            if not geometry.isGeosValid():
                validation_errors = geometry.validateGeometry()
                # Try to repair the geometry
                self.logger.warning(
                    f"Invalid geometry detected in feature ID {feature.id()} - {validation_errors}, attempting to repair..."
                )
                fixed_geometry = geometry.makeValid()

                # Check if the repair was successful
                if not fixed_geometry.isGeosValid():
                    self.logger.error(f"Could not repair geometry for feature ID {feature.id()}, skipping feature.")
                    continue

                # Replace with the fixed geometry
                if geometry.type() != fixed_geometry.type():
                    self.logger.warning(
                        f"Geometry type changed from {geometry.type()} to {fixed_geometry.type()} for feature ID {feature.id()}, skipping feature."
                    )
                    continue
                self.logger.info(f"Successfully repaired geometry for feature ID {feature.id()}")
                feature.setGeometry(fixed_geometry)

            # set spettri field with relative path
            try:
                if self.shapefile_name in ["MS23-Stab.shp", "MS23-Instab.shp"]:
                    if "SPETTRI" in feature.attributeMap() and feature["SPETTRI"]:
                        feature["SPETTRI"] = f"./Allegati/Spettri/{feature['SPETTRI']}"
            except Exception as e:
                self.logger.warning(f"Error setting SPETTRI field for feature {feature}: {e}")

            modifiedFeature = self.attribute_fill(feature, dest_layer, common_fields)
            feature_list.append(modifiedFeature)

        if dest_layer.isEditable():
            self.logger.warning(f"Layer {dest_layer.name()} is in editing mode! Committing changes...")
            dest_layer.commitChanges()

        proj = self.prj_manager.current_project
        # save current intersection mode
        intersection_mode = proj.avoidIntersectionsMode()

        if DEBUG_MODE:
            self.logger.warning(f"{'#' * 15} Truncating layer {dest_layer.name()}!")
            # TODO: causes random QGIS crashes
            dest_layer.dataProvider().truncate()

        if os.getenv("TESTING_MODE") == "1":
            # When running tests, use addFeatures to avoid issues with edit context manager
            dest_layer.dataProvider().addFeatures(feature_list)
            self.iterations = len(feature_list)
            self.logger.warning(f"Inserting {len(feature_list)} features in TESTING_MODE with data provider")
        else:
            # Use edit context manager to enable cancelling task and rollback on failure
            with edit(dest_layer):
                # set AllowIntersections and disable digitizing geometry checks
                proj.setAvoidIntersectionsMode(QgsProject.AvoidIntersectionsMode.AllowIntersections)

                geom_checks = dest_layer.geometryOptions().geometryChecks()
                if geom_checks:
                    dest_layer.geometryOptions().setGeometryChecks([])

                for f in feature_list:
                    self.iterations += 1
                    self.logger.debug(f"Inserting feature {self.iterations}/{len(feature_list)}")
                    dest_layer.addFeature(f)
                    if self.isCanceled():
                        return False

            # restore intersection mode and digitizing geometry checks
            if intersection_mode is not None:
                proj.setAvoidIntersectionsMode(intersection_mode)
            if geom_checks:
                dest_layer.geometryOptions().setGeometryChecks(geom_checks)

        return True
