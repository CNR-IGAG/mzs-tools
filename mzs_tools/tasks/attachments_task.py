import logging
import shutil

from qgis.core import QgsTask
from qgis.utils import spatialite_connect

from ..core.mzs_project_manager import MzSProjectManager


class AttachmentsTask(QgsTask):
    def __init__(self, prepend_ids: bool = True):
        super().__init__("Check, collect, consolidate indagini attachments", QgsTask.Flag.CanCancel)

        self.prepend_ids = prepend_ids

        self.iterations = 0
        self.exception = None

        # the logger is configured in attachment_task_manager
        self.logger = logging.getLogger("mzs_tools.tasks.attachment_manager")

        self.prj_manager = MzSProjectManager.instance()
        self.spatialite_db_connection = None

        self.total_attachments = 0

        # Configuration for each attachment type
        self.attachment_config = {
            "indagini_puntuali": {
                "query": """SELECT pkuid, id_spu, id_indpu, doc_ind FROM indagini_puntuali 
                          WHERE doc_ind IS NOT NULL AND doc_ind != ''""",
                "id_field": "id_indpu",
                "check_field": "id_spu",
                "file_field": "doc_ind",
                "dest_folder": "Documenti",
            },
            "parametri_puntuali": {
                "query": """SELECT pkuid, id_indpu, id_parpu, tab_curve FROM parametri_puntuali 
                          WHERE tab_curve IS NOT NULL AND tab_curve != ''""",
                "id_field": "id_parpu",
                "check_field": "id_parpu",
                "file_field": "tab_curve",
                "dest_folder": "Documenti",
            },
            "indagini_lineari": {
                "query": """SELECT pkuid, id_sln, id_indln, doc_ind FROM indagini_lineari 
                          WHERE doc_ind IS NOT NULL AND doc_ind != ''""",
                "id_field": "id_indln",
                "check_field": "id_sln",
                "file_field": "doc_ind",
                "dest_folder": "Documenti",
            },
            "instab_l23": {
                "query": """SELECT pkuid, ID_i, SPETTRI FROM instab_l23 
                          WHERE SPETTRI IS NOT NULL AND SPETTRI != ''""",
                "id_field": "ID_i",
                "check_field": None,
                "file_field": "SPETTRI",
                "dest_folder": "Spettri",
            },
            "stab_l23": {
                "query": """SELECT pkuid, ID_z, SPETTRI FROM stab_l23 
                          WHERE SPETTRI IS NOT NULL AND SPETTRI != ''""",
                "id_field": "ID_z",
                "check_field": None,
                "file_field": "SPETTRI",
                "dest_folder": "Spettri",
            },
        }

    def run(self):
        self.logger.info(f"{'#' * 15} Starting task {self.description()}")
        self.iterations = 0

        try:
            # Collect data from all attachment types
            attachment_data = {}
            self.total_attachments = 0

            # Retrieve data for all attachment types
            for table_name, config in self.attachment_config.items():
                data = self.get_attachments_data(table_name, config["query"])
                attachment_data[table_name] = data
                self.total_attachments += len(data)

            if self.total_attachments == 0:
                self.logger.info("No attachments to check. Task completed.")
                return True

            # Process each attachment type
            for table_name, config in self.attachment_config.items():
                self.logger.debug(f"Checking {table_name} attachments...")

                # Unpack configuration
                # id_field = config["id_field"]
                check_field = config["check_field"]
                file_field = config["file_field"]
                dest_folder = config["dest_folder"]

                # Get field indexes from the query results
                # id_index = 1 if id_field == "id_parpu" else 2  # Handle parametri_puntuali special case
                check_index = 1 if check_field else None
                file_index = 2 if file_field == "SPETTRI" else 3

                # Process all attachments for this type
                for row in attachment_data[table_name]:
                    pkuid = row[0]
                    id_value = row[1] if file_field == "SPETTRI" else row[2]
                    check_value = row[check_index] if check_index is not None else None
                    file_path = row[file_index]

                    # Process this attachment
                    try:
                        self.process_attachment(
                            table_name=table_name,
                            pkuid=pkuid,
                            id_value=id_value,
                            check_value=check_value if self.prepend_ids else None,
                            file_path=file_path,
                            dest_folder=dest_folder,
                        )
                    except Exception as e:
                        self.logger.error(f"Error processing attachment {file_path}: {e}")

                    # Update progress
                    self.iterations += 1
                    self.setProgress(self.iterations * 100 / self.total_attachments)
                    if self.isCanceled():
                        return False

        except Exception as e:
            self.exception = e
            return False

        finally:
            # close connections
            if self.spatialite_db_connection:
                self.logger.debug("Closing spatialite connection...")
                self.spatialite_db_connection.close()

        return True

    def process_attachment(self, table_name, pkuid, id_value, check_value, file_path, dest_folder):
        """Process a single attachment file"""
        self.logger.debug(f"Checking attachment {file_path} for {table_name} {id_value}...")

        # Get full path to the file
        file_full_path = self.prj_manager.project_path / file_path
        file_full_path = file_full_path.resolve()

        # Check if the file exists
        if not file_full_path.exists():
            self.logger.warning(f"Attachment {file_full_path} for {table_name} {id_value} does not exist!")
            return

        # Determine destination file name
        dest_file_name = file_full_path.name
        if check_value is not None and check_value not in file_full_path.name:
            dest_file_name = f"{id_value}_{file_full_path.name}"

        # Destination path
        dest_path = self.prj_manager.project_path / "Allegati" / dest_folder / dest_file_name

        # Check if file is already in the correct location
        if file_full_path == dest_path:
            self.logger.debug(f"Attachment {file_path} already in the correct folder")
            return

        # Move the file to the correct folder
        if dest_path.exists():
            self.logger.warning(
                f"Attachment {file_path} already exists in {dest_path.parent}, old file will be backed up"
            )
            # Backup the old file
            backup_folder = dest_path.parent / "backup"
            backup_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(dest_path, backup_folder)

        shutil.copy(file_full_path, dest_path)
        self.logger.info(f"Attachment {file_path} copied to {dest_path}")

        # Update the database
        relative_path = dest_path.relative_to(self.prj_manager.project_path)
        self.update_attachment_path(table_name, pkuid, relative_path)
        self.logger.info(f"Attachment path updated in the database to {relative_path}")

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
        self.logger.warning(f"Task {self.description()} was canceled")
        super().cancel()

    def get_spatialite_db_connection(self):
        if not self.spatialite_db_connection:
            self.spatialite_db_connection = spatialite_connect(str(self.prj_manager.db_path))
        return self.spatialite_db_connection

    def update_attachment_path(self, table_name, pkuid, new_path):
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()

            # Determine which field to update based on the table
            field_name = "doc_ind"  # Default for most tables
            if table_name == "parametri_puntuali":
                field_name = "tab_curve"
            elif table_name in ["instab_l23", "stab_l23"]:
                field_name = "SPETTRI"

            cursor.execute(f"""UPDATE {table_name} SET {field_name} = '{new_path}' WHERE pkuid = {pkuid}""")
            conn.commit()
            cursor.close()

    def get_attachments_data(self, table_name, query):
        """Get attachment data from database using the provided query"""
        with self.get_spatialite_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
        return data
