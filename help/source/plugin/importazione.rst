.. _importazione:

Importazione dati da un progetto standard
-----------------------------------------

.. |ico1| image:: ../../../mzs_tools/resources/icons/ico_nuovo_progetto.png
  :height: 25

.. |ico2| image:: ../../../mzs_tools/resources/icons/ico_importa.png
  :height: 25

Nel caso in cui il nuovo studio di MS costituisca il proseguimento o approfondimento di uno studio già esistente - ad
esempio quando il nuovo studio tratti un approfondimento di livello 3 precedentemente non effettuato - è possibile
importare i dati già esistenti, e procedere successivamente alle integrazioni.

.. warning:: E\' consigliabile effettuare l'importazione di dati preesistenti all'interno di un **progetto MzSTools vuoto o appena
   creato** per lo stesso comune oggetto di studio.

   E\' possibile effettuare l'importazione all'interno di un progetto in cui siano già presenti altri dati, ma in questo caso **gli
   ID numerici dei dati importati risulteranno diversi rispetto ai dati originali**.

   Inoltre il progetto dal quale effettuare l'importazione deve essere basato sugli **standard versione 4 o
   successive** e deve utlizzare il formato **shapefile** per i dati vettoriali, mentre il database delle indagini può
   essere in formato **Microsoft Access** (“CdI_tabelle.mdb”), in formato **SQLite** (“CdI_tabelle.sqlite”) o in tabelle
   esportate in formato **CSV**.

.. image:: ../img/importazione.png
  :width: 420
  :align: center

In particolare, lo strumento è in grado di trasferire in modo automatico nella nuova struttura del plugin:

* i dati provenienti dagli **shapefile** e dal **database “CdI_tabelle”** del vecchio progetto;
* i **documenti** (ad esempio le carte in formato ``.pdf`` e i file degli spettri elastici di risposta in formato
  ``.txt``) presenti nelle cartelle accessorie del vecchio progetto.

.. Note:: Per l’importazione dei dati dal database Access è necessario che siano state installate correttamente le dipendenze del
   plugin, come descritto nella guida di installazione.

Al termine delle operazioni, il tool genera un **report testuale** contenente l’esito dell’importazione, all’interno
della cartella di progetto ``/allegati/log``.

Esportazione dei dati da Microsoft Access
"""""""""""""""""""""""""""""""""""""""""

Nel caso in cui non sia possibile accedere direttamente al database Access tramite il plugin, è possibile effettuare
l'importazione dei dati in modo indiretto, utilizzando Microsoft Access per esportare le tabelle del database in
formato CSV e successivamente effettuare l'importazione utilizzando l'opzione ``Tabelle esportate in formato CSV`` per
selezionare la cartella contenente i file ``.txt`` o ``.csv`` esportati.

Le tabelle da esportare da “CdI_Tabelle.mdb” sono:

* “Sito_Puntuale”;
* “Sito_Lineare”;
* “Indagini_Puntuali”;
* “Indagini_Lineari”;
* “Parametri_Puntuali”;
* “Parametri_Lineari”;
* “Curve”.

.. image:: ../img/tabelle_access.png
  :width: 540
  :align: center

La procedura da eseguire per esportare le suddette tabelle in formato ``.txt``, è la seguente:

1. aprire la cartella principale del progetto da importare;

2. entrare nella cartella “Indagini” e aprire il “CdI_Tabelle.mdb” con Microsoft Access (versione Microsoft Office 2013
   e successive);

3. selezionare una delle tabelle da esportare, premere il pulsante destro del mouse e selezionare **Esporta - File di
   testo**;

.. image:: ../img/esportazione_access.png
  :width: 540
  :align: center

4. si aprirà la finestra “Esporta – File di testo” dove verrà richiesto di selezionare la directory di salvataggio e il
   nome del file TXT di output. Lasciare invariato il nome di default del file (nell’esempio “Sito_Puntuale.txt”) e
   selezionare la cartella di destinazione. Lasciare inalterate le altre opzioni e premere il pulsante “OK”;

.. image:: ../img/esportazione2_access.png
  :width: 540
  :align: center

5. si aprirà la finestra “Esportazione guidata testo”:

   a. nel primo step, spuntare la voce “Delimitato” e premere il pulsante “Avanti”;

      .. image:: ../img/esportazione3_access.png
        :width: 540
        :align: center

   b. nel secondo step, scegliere “Punto e virgola” all’interno del “Delimitatore campo”, spuntare la voce “Includi
      nomi di campo nella prima riga” e controllare che in “Qualificatore testo” siano selezionate le doppie
      virgolette. Premere il pulsante “Avanzate”;

      .. image:: ../img/esportazione4_access.png
        :width: 540
        :align: center

   c. si aprirà la finestra “Avanzate…”. Alla voce “Separatore decimale”, immettere “.” (punto). Premere il pulsante
      “OK”;

      .. image:: ../img/esportazione5_access.png
        :width: 540
        :align: center

   d. Si tornerà alla finestra “Esportazione guidata testo”. Premere il pulsante “Avanti”;

   e. nel terzo step, verrà visualizzata nuovamente la directory di output. Premere il pulsante “Fine”;

      .. image:: ../img/esportazione6_access.png
        :width: 540
        :align: center

6. ripetere le operazioni 4 e 5 per tutte le tabelle elencate precedentemente.
