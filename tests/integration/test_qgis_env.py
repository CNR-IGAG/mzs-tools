from qgis.core import QgsProviderRegistry


def test_qgis_environment():
    """
    Test that the full QGIS environment is set up correctly by pytest-qgis
    or by other means. If this is the case, we should have access to some common
    data providers initialized by QgsApplication.initQgis()
    """
    r = QgsProviderRegistry.instance()
    assert "ogr" in r.providerList()
    assert "gdal" in r.providerList()
    assert "postgres" in r.providerList()
