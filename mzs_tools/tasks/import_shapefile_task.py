import logging
import shutil
from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from qgis.core import QgsProject, QgsTask, QgsVectorLayer, edit


class ImportShapefileTask(QgsTask):
    def __init__(
        self,
        proj_paths: dict,
        shapefile_name: str,
        debug: bool = False,
    ):
        super().__init__(f"Import shapefile {shapefile_name}", QgsTask.CanCancel)

        self.iterations = 0
        self.exception = None

        # self.log = MzSToolsLogger().log

        # the logger is configured in the import data dialog module
        self.logger = logging.getLogger("mzs_tools.tasks.import_data")

        self.prj_manager = MzSProjectManager.instance()

        self.proj_paths = proj_paths
        self.shapefile_name = shapefile_name

        self.debug = debug

    def run(self):
        self.logger.info(f"{'#'*15} Starting task {self.description()}")
        if self.debug:
            self.logger.warning(f"\n{'#'*50}\n# Running in DEBUG mode! Data will be DESTROYED! #\n{'#'*50}")

        self.iterations = 0

        try:
            shapefile_path = self.proj_paths[self.shapefile_name]["path"]
            db_table_name = self.proj_paths[self.shapefile_name]["table"]
            dest_layer_id = self.prj_manager.find_layer_by_table_name_role(db_table_name, "editing")
            dest_layer = self.prj_manager.current_project.mapLayer(dest_layer_id)

            if self.shapefile_name in ["MS23-Stab.shp", "MS23-Instab.shp"]:
                # copy spettri files to the project folder
                spettri_path = self.proj_paths["Spettri"]["path"]
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
        targetLayerFields = []
        sourceLayerFields = []
        primaryKeyList = []

        for index in targetLayer.dataProvider().pkAttributeIndexes():
            primaryKeyList.append(targetLayer.dataProvider().fields().at(index).name())

        for field in sourceLayer.dataProvider().fields().toList():
            sourceLayerFields.append(field.name())

        for field in targetLayer.dataProvider().fields().toList():
            targetLayerFields.append(field.name())

        commonFields = list(set(sourceLayerFields) & set(targetLayerFields))
        commonFields = list(set(commonFields) - set(primaryKeyList))

        return commonFields

    def attribute_fill(self, qgsFeature, targetLayer, commonFields):
        featureFields = {}

        for field in qgsFeature.fields().toList():
            if field.name() == "desc_modco":
                featureFields["desc_modcoord"] = qgsFeature[field.name()]
            elif field.name() == "mod_identc":
                featureFields["mod_identcoord"] = qgsFeature[field.name()]
            elif field.name() == "ub_prov":
                featureFields["ubicazione_prov"] = qgsFeature[field.name()]
            elif field.name() == "ub_com":
                featureFields["ubicazione_com"] = qgsFeature[field.name()]
            elif field.name() == "ID_SPU":
                featureFields["id_spu"] = qgsFeature[field.name()]
            elif field.name() == "ID_SLN":
                featureFields["id_sln"] = qgsFeature[field.name()]
            else:
                featureFields[field.name()] = qgsFeature[field.name()]

        qgsFeature.setFields(targetLayer.dataProvider().fields())
        if commonFields:
            for fieldName in commonFields:
                qgsFeature[fieldName] = featureFields[fieldName]

        return qgsFeature

    def insert_features(self, source_features, dest_layer: QgsVectorLayer, common_fields):
        feature_list = []

        self.logger.info(f"Inserting features from {self.shapefile_name} to {dest_layer.name()}")

        features_are_3d = False
        for feature in source_features:
            geometry = feature.geometry()
            if geometry.get().is3D():
                if not features_are_3d:
                    features_are_3d = True
                    self.logger.warning(f"3D features detected in {self.shapefile_name}! Z values will be dropped.")
                geometry.get().dropZValue()
                feature.setGeometry(geometry)

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

        if self.debug:
            self.logger.warning(f"{'#'*15} Truncating layer {dest_layer.name()}!")
            # TODO: causes random QGIS crashes
            dest_layer.dataProvider().truncate()

        with edit(dest_layer):
            # set AllowIntersections and disable digitizing geometry checks
            proj = self.prj_manager.current_project
            intersection_mode = proj.avoidIntersectionsMode()
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
        proj.setAvoidIntersectionsMode(intersection_mode)
        if geom_checks:
            dest_layer.geometryOptions().setGeometryChecks(geom_checks)

        return True
