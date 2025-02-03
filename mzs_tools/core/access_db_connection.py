from mzs_tools.__about__ import DIR_PLUGIN_ROOT
from mzs_tools.plugin_utils.logging import MzSToolsLogger

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
        self.log("Starting Java JVM")
        try:
            if not jpype.isJVMStarted():
                jpype.startJVM(classpath=self.classpath, convertStrings=False)
        except Exception as e:
            self.log(f"Error starting JVM: {e} ", log_level=2)
            raise e

        from java.lang import System  # type: ignore

        self.log(f"JVM version: {jpype.getJVMVersion()}")
        self.log(f"JVM classpath: {System.getProperty('java.class.path')}")

        # Connect to the database
        self.log("Opening Access Db connection")
        try:
            self.connection = jaydebeapi.connect(self.driver, self.url, self.options)
        except Exception as e:
            # can import only when the JVM is running
            # from net.ucanaccess.exception import AuthenticationException, UcanaccessSQLException

            self.log(f"{e} - {e.getMessage()}", log_level=1)
            self.log(f"cause: {e.getCause()}", log_level=4)
            # self.log(f"getErrorCode: {e.getErrorCode()}", log_level=4)

            raise e

        # Create a cursor
        self.cursor = self.connection.cursor()

        return True

    def close(self):
        self.log("Closing Access Db connection")
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
