SOURCES = mzs_tools.py \
          core/mzs_project_manager.py \
          gui/dlg_create_project.py \
          gui/dlg_export_data.py \
          gui/dlg_fix_layers.py \
          gui/dlg_import_data.py \
          gui/dlg_info.py \
          gui/dlg_load_ogc_services.py \
          gui/dlg_manage_attachments.py \
          gui/dlg_metadata_edit.py \
          gui/dlg_settings.py \
          tasks/access_db_connection.py \
          tasks/attachments_task_manager.py \
          tasks/attachments_task.py \
          tasks/common_functions.py \
          tasks/export_project_files_task.py \
          tasks/export_siti_lineari_task.py \
          tasks/export_siti_puntuali_task.py \
          tasks/import_shapefile_task.py \
          tasks/import_siti_lineari_task.py \
          tasks/import_siti_puntuali_task.py

FORMS = gui/dlg_create_project.ui \
        gui/dlg_export_data.ui \
        gui/dlg_fix_layers.ui \
        gui/dlg_import_data.ui \
        gui/dlg_info.ui \
        gui/dlg_load_ogc_services.ui \
        gui/dlg_manage_attachments.ui \
        gui/dlg_metadata_edit.ui \
        gui/dlg_settings.ui
        

TRANSLATIONS = i18n/MzSTools_it.ts