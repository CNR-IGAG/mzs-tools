About
"""""

Licenza
=======

Codice del Plugin
-----------------

Il plugin **MzS Tools** è rilasciato sotto la **GNU General Public License v3.0 o successiva (GPLv3)**.

Il testo completo della licenza è disponibile nel file `LICENSE
<https://github.com/CNR-IGAG/mzs-tools/blob/master/LICENSE>`_ del repository.

Documentazione
--------------

Questa documentazione è rilasciata con licenza `Creative Commons Attribution 4.0 International License (CC BY 4.0) <https://creativecommons.org/licenses/by/4.0/>`_.

.. image:: https://licensebuttons.net/l/by/4.0/88x31.png
   :target: https://creativecommons.org/licenses/by/4.0/
   :alt: CC BY 4.0

Per maggiori informazioni sulla CC BY 4.0, visita: `<https://creativecommons.org/licenses/by/4.0/>`_.

Changelog
=========

v2.0.6
    - Correzione per i campi interi convertiti in float negli shapefile esportati
    - Aggiornati i layer per i layout di stampa
    - Ristrutturazione dei test automatici

v2.0.5
    - Corretta la vista HVSR per gestire il caso di utilizzo della virgola come separatore decimale nel campo testuale "valore"
    - Nuovo strumento per controllare ed installare le librerie python richieste (in alternativa a QPIP) e rilevare
      l'installazione di Java
    - Nuova impostazione per memorizzare manualmente il percorso della Java JRE
    - Disabilitata la dipendenza del plugin da QPIP
    - Miglioramenti nella gestione del database
    - Miglioramenti nell'importazione ed esportazione dei dati

v2.0.4
    - Aggiornati alcuni layer e simbologie per i layout di stampa
    - Aggiornamento degli strumenti di sviluppo
    - Aggiornamenti per la compatibilità con PyQt6 (sperimentale)

v2.0.3
    - Sistemata la vista HVSR per i progetti creati con la versione 2.0.2, per i quali il template di database non
      includeva il cambiamento

v2.0.2
    - Risolti alcuni problemi di lentezza nel caricamento del progetto e di uso eccessivo di memoria causati
      dall'inserimento di un'immagine con risoluzione troppo elevata nei layout di stampa.
    - Aggiornata la vista dei valori HVSR in modo da includere i valori inseriti nella tabella non standard dedicata.
    - Corretto un simbolo SVG nella Carta Geologico-Tecnica e Carta delle MOPS

v2.0.1
    - Risoluzione di bug minori
    - Aggiornata la logica per la mappa HVSR tramite la creazione di una vista dedicata nel database

v2.0.0
    - Rinnovo generale del plugin
    - Miglioramento della gestione dei progetti e dei database
    - Accesso diretto e cross-platform ai database Microsoft Access ("CdI_Tabelle.mdb") per l'importazione ed
      esportazione dei dati (richiede l'installazione di Java JVM 64 bit e di librerie esterne gestite tramite il plugin
      per QGIS "QPIP")
    - Compatibilità preliminare con PyQt6

v1.9.4
    - Sistemati i layer per i layout di stampa

v1.9.3
    - Hotfix per la disconnessione dei segnali di editing
    - Sistemati i trigger delle tabelle stab, instab, isosub

v1.9.2
    - Introdotti alcuni elementi di compatibilità con le future versioni degli Standard MS
    - Unificati i layer "Zone stabili" e "Zone instabili" dei livelli 2-3, così come previsto dagli Standard MS
    - Nel progetto QGIS i layer gestiti dal plugin sono ora impostati come "richiesti", ed i layer per i layout di
      stampa sono impostati in sola lettura; l'utente viene avvisato nel caso in cui tenti di rinominare un layer
      richiesto
    - Semplificato e reso più efficiente lo strumento di creazione di un nuovo progetto
    - Aggiunto uno strumento per l'inserimento e la modifica dei metadati dello studio di MS
    - Sistemata e resa automatica l'impostazione dei controlli di editing topologico e sovrapposizione fra determinati
      layer, quali "Zone stabili" e "Zone instabili"
    - Aggiunto uno strumento di configurazione del plugin in cui è possibile attivare o disattivare l'impostazione
      automatica dei controlli di editing topologico e sovrapposizione fra i layer
    - Rimossi gli strumenti di editing dalla toolbar di MzS Tools (le impostazioni di editing topologico sono ora
      gestite automaticamente tramite gli strumenti di editing base di QGIS)
    - Rimosso lo strumento di copia delle feature fra i layer "Zone stabili" e "Zone instabili"
    - Risolti alcuni problemi con l'importazione e l'esportazione dei dati
    - Risolti diversi problemi minori

v1.9.1
    - Updated style expressions for MS level 2-3 layers

v1.9.0
    - Updated styles and print layouts
    - Improved compatibility with MS standard v4.2

v1.8.3
    - Updated styles and expressions in QGIS project
    - Updated and improved print layouts
    - Added available regional CTR WMS services
    - Fix potential problems in import process

v1.8.2
    - Experimental fixes for slow data import and export processes
    - Updated styles and expressions in QGIS project
    - Updated and improved print layouts

v1.8.1
    - Fix problem with version strings in project update

v1.8
    - QGIS project template improvements

v1.7
    - Update ISTAT administrative boundaries and codes to the `latest 2022 version <https://www.istat.it/it/archivio/222527>`_
    - Update styles for editing layers
    - Add QGIS action for punctual and linear surveys layers to directly search for available survey documents in the project folder

v1.6
    - Fix Python error in geotec editing
    - Update project template (snapping options, symbols)

v1.5
    - Ported to QGIS v3

v1.4
    -  Updated to new MS 4.2 standards;
    -  update project (fixed labels, update .py files, added new style);
    -  updated italian manual.

v1.3
    -  updated layout "CDI - Carta delle Indagini" (added legend);
    -  updated export shapefiles and "Export geodatabase to project folder" tool (to meet the standards);
    -  removed "Validate project" tool;
    -  fixed bug in log files;
    -  update project (fixed labels, update .py files);
    -  updated italian manual.

v1.2
    -  updated layouts ("Carta di Microzonazione Sismica (FA 0.1-0.5 s)", "Carta di Microzonazione Sismica (FA 0.4-0.8 s)", "Carta di Microzonazione Sismica (FA 0.7-1.1 s)");
    -  added "pkey" field in "Indagini" and "Parametri" tables;
    -  removed english manual.

v1.1
    -  modified the layout layer "CDI - Indagini puntuali";
    -  modified the layout layer "MOPS - HVSR";
    -  updated export database ("CdI_Tabelle.sqlite").

v1.0
    -  stable version;
    -  added a new video-guide ("Indagine stazione singola (HVSR)");
    -  update project (fixed labels and styles errors, update .py files);
    -  updated italian manuals.

v0.9
    -  update table "Indagine stazione singola (HVSR)", "freq.ui" mask and added a new layout ("Carta delle frequenze naturali dei terreni fr");
    -  update constraint "quota_slm_top_verify" and "quota_slm_bot_verify" in "indagini_puntuali", "parametri_puntuali" and "parametri_lineari" tables;
    -  moved export process to a separate thread;
    -  export progress shown in qgis interface;
    -  fixed bug in "siti_ind_param.py";
    -  update "New project" tool;
    -  added a new table ("metadati");
    -  added a new video-guide ("Indagine stazione singola (HVSR)");
    -  update project (in particular .ui, .py files);
    -  updated italian manuals.

v0.8
    -  fixed bug in "indagini_puntuali.py";
    -  update "siti_puntuali" and "siti_lineari" triggers;
    -  added a new table ("Indagine stazione singola (HVSR)") and a new layout ("Carta delle frequenze naturali dei terreni");
    -  update project (in particular .ui, .py files);
    -  changed update project process and removed "Update project" tool;
    -  updated italian manuals.

v0.7
    -  moved import process to a separate thread;
    -  import progress shown in qgis interface;
    -  fixed bug with empty numeric values in csv files during import;
    -  reimplemented import log file;
    -  added "Update project" tool;
    -  update project (in particular .ui, .py files);
    -  updated italian manuals.

v0.6
    -  video-guide additions;
    -  update project (in particular .ui, .py files);
    -  resolved bugs;
    -  updated italian manual.

v0.5
    -  improved "Add feature or record" tool;
    -  removed useless tool;
    -  update project (in particular .ui, .py files);
    -  resolved bugs;
    -  updated manuals.

v0.4
    -  initial relase.

Credits
=======

|logo_igag|

.. |logo_igag| image:: ../../mzs_tools/resources/img/logo_IGAG.png
    :width: 160px
    :target: https://www.igag.cnr.it

Il plugin viene sviluppato nell'ambito delle attività del
`Laboratorio GIS del CNR-IGAG <https://www.igag.cnr.it/lista-laboratori/labgis/>`_

**Contributors**

* Giuseppe Cosentino
* Francesco Pennica
* Emanuele Tarquini (v1.x)

**Special Thanks**

* Francesco Stigliano (MS projects support)
* Monia Coltella (MS standard support)
* Alessandro Pasotti (QGIS 3 port, v1.5)

**License**

This project is licensed under the **GPL-3.0 License**.

**Acknowledgements**

* External libraries:
    * `UCanAccess <https://github.com/spannm/ucanaccess>`_ (Apache-2.0 license)
    * `JayDeBeApi <https://github.com/baztian/jaydebeapi>`_ (LGPL-3.0 license)
* 'CNR' logo, 'IGAG' logo, 'LabGIS' logo, 'DPC' logo, 'Conferenza regioni e provincie autonome' logo and 'Regioni' logos belong to their respective owners who retain all rights in law;
* Italian administrative boundaries data by `Istituto Nazionale di Statistica (ISTAT) <https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/>`_ - CC BY 4.0 Deed;
