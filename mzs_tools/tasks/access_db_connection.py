from ..__about__ import DIR_PLUGIN_ROOT
from ..plugin_utils.logging import MzSToolsLogger

EXT_LIBS_LOADED = True

try:
    import jaydebeapi
    import jpype
    import jpype.imports
    from jpype.types import *  # noqa: F403
except ImportError:
    EXT_LIBS_LOADED = False


class AccessDbConnection:
    def __init__(self, db_path: str, password: str = None):
        self.log = MzSToolsLogger().log

        if not EXT_LIBS_LOADED:
            raise ImportError("Required external libraries not loaded")

        self.driver = "net.ucanaccess.jdbc.UcanaccessDriver"
        self.url = f"jdbc:ucanaccess://{db_path}"
        self.options = {}
        if password:
            self.options["password"] = password
        self.classpath = DIR_PLUGIN_ROOT / "ext_libs" / "ucanaccess-5.1.2-uber.jar"
        self.connection = None
        self.cursor = None

    def open(self):
        try:
            if not jpype.isJVMStarted():
                self.log("Starting Java JVM")
                jpype.startJVM(classpath=self.classpath, convertStrings=False)
                self.log(f"JVM version: {jpype.getJVMVersion()}", log_level=4)

                from java.lang import System  # type: ignore

                self.log(f"JVM classpath: {System.getProperty('java.class.path')}", log_level=4)
        except Exception as e:
            self.log(f"Error starting JVM: {e} ", log_level=2)
            raise JVMError("Error starting JVM")

        # Connect to the database
        self.log("Opening Access Db connection", log_level=4)
        try:
            self.connection = jaydebeapi.connect(self.driver, self.url, self.options)
        except Exception as e:
            # can import only when the JVM is running
            from net.ucanaccess.exception import AuthenticationException  # type: ignore

            self.log(f"{e} - {e.getMessage()}", log_level=4)
            self.log(f"cause: {e.getCause()}", log_level=4)
            # self.log(f"getErrorCode: {e.getErrorCode()}", log_level=4)

            if isinstance(e.getCause(), AuthenticationException):
                raise MdbAuthError("Invalid password")

            raise e

        # Create a cursor
        self.cursor = self.connection.cursor()

        return True

    def close(self):
        self.log("Closing Access Db connection", log_level=4)
        # Close the cursor
        self.cursor.close()

        # Close the connection
        self.connection.close()

        # Shut down the JVM
        # jpype.shutdownJVM()

    def execute(self, query):
        # Execute the query
        self.cursor.execute(query)

        # Fetch the results
        return self.cursor.fetchall()

    def commit(self):
        # Commit the transaction
        self.connection.commit()

    def rollback(self):
        # Rollback the transaction
        self.connection.rollback()

    def get_sito_puntuale_data(self):
        field_names = [
            "pkey_spu",
            "ubicazione_prov",
            "ubicazione_com",
            "ID_SPU",
            "indirizzo",
            "coord_X",
            "coord_Y",
            "mod_identcoord",
            "desc_modcoord",
            "modo_quota",
            "data_sito",
            "note_sito",
            "quota_slm",
        ]
        query = """SELECT [pkey_spu], [ubicazione_prov], [ubicazione_com], ID_SPU, [indirizzo], [coord_X], [coord_Y],
                   [mod_identcoord], [desc_modcoord], [modo_quota], [data_sito], [note_sito], [quota_slm] FROM [Sito_Puntuale]"""
        data = self.execute(query)
        return {
            row[3]: {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_sito_lineare_data(self):
        field_names = [
            "pkey_sln",
            "ubicazione_prov",
            "ubicazione_com",
            "ID_SLN",
            "Acoord_X",
            "Acoord_Y",
            "Bcoord_X",
            "Bcoord_Y",
            "mod_identcoord",
            "desc_modcoord",
            "data_sito",
            "note_sito",
            "Aquota",
            "Bquota",
        ]
        query = """SELECT [pkey_sln], [ubicazione_prov], [ubicazione_com], ID_SLN, [Acoord_X], [Acoord_Y], [Bcoord_X],
                [Bcoord_Y], [mod_identcoord], [desc_modcoord], [data_sito], [note_sito], [Aquota], [Bquota] FROM
                [Sito_Lineare]"""
        data = self.execute(query)
        return {
            row[3]: {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_indagini_puntuali_data(self):
        field_names = [
            "pkey_spu",
            "pkey_indpu",
            "classe_ind",
            "tipo_ind",
            "ID_INDPU",
            "id_indpuex",
            "arch_ex",
            "note_ind",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "data_ind",
            "doc_pag",
            "doc_ind",
        ]
        query = """SELECT [pkey_spu], [pkey_indpu], [classe_ind], [tipo_ind], ID_INDPU, [id_indpuex], [arch_ex],
                   [note_ind], [prof_top], [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [data_ind],
                   [doc_pag], [doc_ind] FROM [Indagini_Puntuali]"""
        data = self.execute(query)
        return {
            (row[0], row[4]): {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_indagini_lineari_data(self):
        field_names = [
            "pkey_sln",
            "pkey_indln",
            "classe_ind",
            "tipo_ind",
            "ID_INDLN",
            "id_indlnex",
            "arch_ex",
            "note_indln",
            "data_ind",
            "doc_pag",
            "doc_ind",
        ]
        query = """SELECT [pkey_sln], [pkey_indln], [classe_ind], [tipo_ind], ID_INDLN, [id_indlnex], [arch_ex],
                [note_indln], [data_ind], [doc_pag], [doc_ind] FROM [Indagini_Lineari]"""
        data = self.execute(query)
        return {
            (row[0], row[4]): {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_parametri_puntuali_data(self):
        field_names = [
            "pkey_indpu",
            "pkey_parpu",
            "tipo_parpu",
            "ID_PARPU",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "valore",
            "attend_mis",
            "tab_curve",
            "note_par",
            "data_par",
        ]
        query = """SELECT [pkey_indpu], [pkey_parpu], [tipo_parpu], ID_PARPU, [prof_top], [prof_bot], [spessore],
                   [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [tab_curve], [note_par], [data_par]
                   FROM [Parametri_Puntuali]"""
        data = self.execute(query)
        return {
            (row[0], row[3]): {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_parametri_lineari_data(self):
        field_names = [
            "pkey_indln",
            "pkey_parln",
            "tipo_parln",
            "ID_PARLN",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "valore",
            "attend_mis",
            "note_par",
            "data_par",
        ]
        query = """SELECT [pkey_indln], [pkey_parln], [tipo_parln], ID_PARLN, [prof_top], [prof_bot], [spessore],
                [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [note_par], [data_par]
                   FROM [Parametri_Lineari]"""
        data = self.execute(query)
        return {
            (row[0], row[3]): {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def get_curve_data(self):
        field_names = [
            "pkey_parpu",
            "pkey_curve",
            "cond_curve",
            "varx",
            "vary",
        ]
        query = """SELECT [pkey_parpu], [pkey_curve], [cond_curve], [varx], [vary] FROM [Curve]"""
        data = self.execute(query)
        return {
            (row[0], row[1]): {
                field_name: str(value) if str(value) != "None" else "" for field_name, value in zip(field_names, row)
            }
            for row in data
        }

    def insert_siti_puntuali(self, data):
        """Insert 'sito_puntuale' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Sito_Puntuale] ([pkey_spu], ID_SPU, [ubicazione_prov], [ubicazione_com], [indirizzo],
                    [coord_X], [coord_Y], [mod_identcoord], [desc_modcoord], [quota_slm], [modo_quota], [data_sito],
                    [note_sito]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11] if row[11] else None,  # data_sito - no empty strings
                        row[12],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting sito {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_indagini_puntuali(self, data):
        """Insert 'indagini_puntuali' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Indagini_Puntuali] ([pkey_spu], [pkey_indpu], [classe_ind], [tipo_ind], ID_INDPU,
                    [id_indpuex], [arch_ex], [note_ind], [prof_top], [prof_bot], [spessore], [quota_slm_top],
                    [quota_slm_bot], [data_ind], [doc_pag], [doc_ind]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        row[13] if row[13] else None,  # data_ind - no empty strings
                        row[14],
                        row[15],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting indagine {row[4]}: {row} - {e}", log_level=2)
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def insert_parametri_puntuali(self, data):
        """Insert 'parametri_puntuali' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Parametri_Puntuali] ([pkey_indpu], [pkey_parpu], [tipo_parpu], ID_PARPU, [prof_top],
                    [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [tab_curve],
                    [note_par], [data_par]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        row[13] if row[13] else None,  # data_par - no empty strings
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting parametro {row[3]}: {row} - {e}", log_level=2)
                insert_errors.append((row[3], e))
                continue
        return insert_errors

    def insert_curve(self, data):
        """Insert 'curve' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Curve] ([pkey_parpu], [pkey_curve], [cond_curve], [varx], [vary]) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting curve {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_siti_lineari(self, data):
        """Insert 'sito_lineare' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Sito_Lineare] ([pkey_sln], ID_SLN, [ubicazione_prov], [ubicazione_com], [Acoord_X],
                    [Acoord_Y], [Bcoord_X], [Bcoord_Y], [mod_identcoord], [desc_modcoord], [Aquota], [Bquota], [data_sito],
                    [note_sito]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12] if row[12] else None,  # data_sito - no empty strings
                        row[13],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting sito {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_indagini_lineari(self, data):
        """Insert 'indagini_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Indagini_Lineari] ([pkey_sln], [pkey_indln], [classe_ind], [tipo_ind], ID_INDLN,
                    [id_indlnex], [arch_ex], [note_indln], [data_ind], [doc_pag], [doc_ind]) VALUES(?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8] if row[8] else None,  # data_sito - no empty strings
                        row[9],
                        row[10],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting indagine {row[4]}: {row} - {e}", log_level=2)
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def insert_parametri_lineari(self, data):
        """Insert 'parametri_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Parametri_Lineari] ([pkey_indln], [pkey_parln], [tipo_parln], ID_PARLN, [prof_top],
                    [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [note_par],
                    [data_par]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12] if row[12] else None,  # data_sito - no empty strings
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting parametro {row[3]}: {row} - {e}", log_level=2)
                insert_errors.append((row[3], e))
                continue
        return insert_errors

    def insert_metadata(self, data):
        """Insert 'metadata' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Metadati] (id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email,
                    resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email,
                    proprieta_dato_sito, data_dato, ruolo, desc_dato, formato, tipo_dato, contatto_dato_nome,
                    contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso,
                    vincoli_fruibilita, vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est,
                    estensione_sud, estensione_nord, formato_dati, distributore_dato_nome, distributore_dato_telefono,
                    distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato,
                    precisione, genealogia) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5] if row[5] else None,
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10] if row[10] else None,
                        row[11],
                        row[12],
                        row[13],
                        row[14],
                        row[15],
                        row[16],
                        row[17],
                        row[18],
                        row[19],
                        row[20],
                        row[21],
                        row[22],
                        row[23],
                        row[24],
                        row[25],
                        row[26],
                        row[27],
                        row[28],
                        row[29],
                        row[30],
                        row[31],
                        row[32],
                        row[33],
                        row[34],
                        row[35],
                        row[36],
                        row[37],
                        row[38],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting metadata {row[0]}: {row} - {e}", log_level=2)
                insert_errors.append((row[0], e))
                continue
        return insert_errors


class MdbAuthError(Exception):
    pass


class JVMError(Exception):
    pass
