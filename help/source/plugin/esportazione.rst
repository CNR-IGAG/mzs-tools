.. _esportazione:

Esportazione del progetto in una struttura standard
---------------------------------------------------

.. |ico3| image:: ../../../mzs_tools/resources/icons/ico_esporta.png
  :height: 25

La struttura di archiviazione generata dal plugin MzSTools non corrisponde esattamente a quella prevista dagli Standard MS, in quanto è ottimizzata per l’utilizzo con QGIS. 

La generazione di una struttura conforme agli Standard deve quindi essere considerata come fase finale del flusso di lavoro e può essere eseguita tramite l'apposito strumento di esportazione |ico3| presente sulla toolbar.

.. image:: ../img/esportazione.png
  :width: 450
  :align: center

|

La finestra di dialogo dello strumento richiede semplicemente di selezionare una cartella  in cui effettuare l’esportazione. Le principali operazioni effettuate dallo strumento consistono in:

* esportazione dal geodatabase SQLite/Spatialite dei dati georeferenziati e tabellari verso file in formato *shapefile* ed un database “CdI_tabelle.sqlite”, conformi agli Standard;
* copia dei file e documenti allegati presenti nella cartella “allegati”.   

Al termine delle operazioni, il tool genera un **report testuale**, contenente l’esito dell’esportazione del progetto, all’interno della cartella di progetto ``/allegati/log``. Il nome del report sarà caratterizzato dalla data e dall’ora di esecuzione del tool, e dalla la dicitura “export_log” (ad esempio ``2018-06-13_09-06-23_export_log.txt``).
