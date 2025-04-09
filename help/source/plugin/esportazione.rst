.. _esportazione:

Esportazione del progetto in una struttura standard
---------------------------------------------------

.. |ico3| image:: ../../../mzs_tools/resources/icons/ico_esporta.png
  :height: 25

La struttura di archiviazione generata dal plugin MzSTools non corrisponde esattamente a quella prevista dagli Standard
MS, in quanto è ottimizzata per l’utilizzo con QGIS. 

La generazione di una struttura conforme agli Standard deve quindi essere considerata come fase finale del flusso di
lavoro e può essere eseguita tramite l'apposito strumento di esportazione |ico3| presente sulla toolbar.

.. image:: ../img/esportazione.png
  :width: 450
  :align: center

La finestra di dialogo dello strumento richiede di selezionare la cartella in cui effettuare l’esportazione e il
formato di output per il database delle indagini. 

Al termine delle operazioni, il tool genera un **report testuale** contenente l’esito dell’esportazione del progetto,
all’interno della cartella di progetto ``/allegati/log``.
