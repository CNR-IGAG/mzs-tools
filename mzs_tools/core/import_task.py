from qgis.core import QgsTask


class ImportTask(QgsTask):
    def __init__(self, description, duration):
        super().__init__(description, QgsTask.CanCancel)
        self.duration = duration
        self.total = 0
        self.iterations = 0
        self.exception = None

    def run(self):
        # Import data
        return True

    def finished(self, result):
        pass

    def cancel(self):
        pass
