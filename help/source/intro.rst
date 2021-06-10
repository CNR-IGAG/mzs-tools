Introduzione
============

Credits
-------

|logo_igag| |logo_cnr|

.. |logo_igag| image:: ../../img/IGAG-CMYK.png
    :width: 18%
    :target: https://www.igag.cnr.it

.. |logo_cnr| image:: ../../img/Logo\ CNR-2010-Quadrato-ITA-high.png
    :width: 30%

Il plugin viene sviluppato nell'ambito delle attività del 
`Laboratorio GIS del CNR-IGAG <https://www.igag.cnr.it/lista-laboratori/labgis/>`_

La microzonazione sismica in Italia
-----------------------------------

Dopo il terremoto in Abruzzo del 6 aprile 2009, è stato lanciato il "Piano nazionale per la prevenzione del rischio sismico" (legge 77/2009 art. 11) e sono state assegnate risorse sulla base dell'indice medio di rischio sismico dei territori per la realizzazione di studi di microzonazione sismica. Per la realizzazione di tali studi, il documento tecnico di riferimento è rappresentato dagli Indirizzi *"Gruppo di lavoro MS 2008. Indirizzi e criteri per la microzonazione sismica. Conferenza delle Regioni e delle Provincie autonome, 2008"* (di seguito ICMS2008). Per supportare i geologi e per facilitare e omogeneizzare l’elaborazione delle carte di microzonazione sismica (MS), sono stati predisposti gli *Standard di rappresentazione ed archiviazione informatica, versione 4.2, 2020* (di seguito Standard MS).

Questo documento costituisce il riferimento per la creazione di prodotti cartografici e per l'archiviazione delle informazioni utili per lo svolgimento degli studi.

Secondo gli “ICMS 2008” e gli “Standard MS”, le mappe da presentare negli studi di MS sono:

* la “Carta delle indagini”;
* la “Carta geologico-tecnica”;
* la “Carta delle microzone omogenee in prospettiva sismica”;
* la “Carta di microzonazione sismica”.

Attualmente gli Standard MS prevedono la creazione di un progetto per la microzonazione sismica basato su shapefile e tabelle in formato mdb, organizzati secondo una struttura predefinita.

Scopo del plugin MzSTools
-------------------------

Il plugin **MzS Tool** è stato realizzato per sfruttare le potenzialità dei software liberi QGIS e SQLite (SpatiaLite), e del linguaggio di programmazione Python, per lo sviluppo di un geodatabase leggero e veloce per l’archiviazione dei dati e la redazione delle mappe tematiche.