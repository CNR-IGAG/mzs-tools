from qgis.core import QgsApplication, QgsProviderRegistry


def test_qgis_environment():
    """
    Test that the full QGIS environment is set up correctly by pytest-qgis
    or by other means. If this is the case, we should have access to some common
    data providers initialized by QgsApplication.initQgis()
    """
    # QgsApplication.setPrefixPath("/usr", True)
    print(f"\n\n{'*' * 80}")
    print("If this is failing, the QGIS Prefix Path might not be set correctly.")
    print("QGIS Prefix Path:", QgsApplication.prefixPath())
    print("Set QGIS_PREFIX_PATH environment variable with the correct QGIS install path.")
    print(f"{'*' * 80}\n\n")
    r = QgsProviderRegistry.instance()
    assert "spatialite" in r.providerList()  # this is absolutely required
    assert "ogr" in r.providerList()
    assert "gdal" in r.providerList()
    assert "postgres" in r.providerList()


# def test_qgis_environment_alt():
#     """
#     Test that the full QGIS environment is set up correctly (without pytest-qgis)
#     If this is the case, we should have access to some common
#     data providers initialized by QgsApplication.initQgis()
#     """
#     QgsApplication.setPrefixPath("/usr", True)
#     from qgis.testing import start_app
#     start_app()

#     from qgis.core import QgsProviderRegistry

#     r = QgsProviderRegistry.instance()
#     assert "spatialite" in r.providerList()
#     assert "ogr" in r.providerList()
#     assert "gdal" in r.providerList()
#     assert "postgres" in r.providerList()
