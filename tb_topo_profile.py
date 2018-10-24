# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_topo_profile.py
# Author:	  Tarquini E.
# Created:	 19-10-2018
#-------------------------------------------------------------------------------

from __future__ import print_function
from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os, sys, webbrowser, math, json, urllib
import matplotlib.pyplot as plt


FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'tb_topo_profile.ui'))


class topo_profile(QtGui.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		"""Constructor."""
		super(topo_profile, self).__init__(parent)
		self.setupUi(self)
		self.plugin_dir = os.path.dirname(__file__)

	def profile(self):
		self.help_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/watch?v=4jQ9OacJ71w&t=4s'))
		self.coord_xa.clear()
		self.coord_ya.clear()
		self.coord_xb.clear()
		self.coord_yb.clear()
		self.coord_xa.setEnabled(False)
		self.coord_ya.setEnabled(False)
		self.coord_xb.setEnabled(False)
		self.coord_yb.setEnabled(False)
		self.dir_input.setEnabled(False)
		self.pushButton_in.setEnabled(False)
		self.group = QButtonGroup()
		self.group.addButton(self.radio_vertex_1)
		self.group.addButton(self.radio_vertex_2)
		self.group.setExclusive(False)
		self.radio_vertex_2.setChecked(False)
		self.radio_vertex_1.setChecked(False)
		self.group.setExclusive(True)
		self.alert_text.hide()
		self.button_box.setEnabled(False)
		self.coord_xa.textEdited.connect(lambda: self.update_num(self.coord_xa))
		self.coord_ya.textEdited.connect(lambda: self.update_num(self.coord_ya))
		self.coord_xb.textEdited.connect(lambda: self.update_num(self.coord_xb))
		self.coord_yb.textEdited.connect(lambda: self.update_num(self.coord_yb))
		self.coord_xa.textChanged.connect(self.disableButton)
		self.coord_ya.textChanged.connect(self.disableButton)
		self.coord_xb.textChanged.connect(self.disableButton)
		self.coord_yb.textChanged.connect(self.disableButton)
		self.radio_vertex_1.toggled.connect(self.radio_vertex_1_clicked)
		self.radio_vertex_2.toggled.connect(self.radio_vertex_2_clicked)

		self.show()
		result = self.exec_()
		if result:

			P1=[float(self.coord_xa.text()), float(self.coord_ya.text())]
			P2=[float(self.coord_xb.text()), float(self.coord_yb.text())]

			s=100
			interval_lat=(P2[0]-P1[0])/s
			interval_lon=(P2[1]-P1[1])/s

			lat0=P1[0]
			lon0=P1[1]

			lat_list=[lat0]
			lon_list=[lon0]

			for i in range(s):
				lat_step=lat0+interval_lat
				lon_step=lon0+interval_lon
				lon0=lon_step
				lat0=lat_step
				lat_list.append(lat_step)
				lon_list.append(lon_step)

			d_list=[]
			for j in range(len(lat_list)):
				lat_p=lat_list[j]
				lon_p=lon_list[j]
				dp=self.haversine(lat0,lon0,lat_p,lon_p)/1000
				d_list.append(dp)
			d_list_rev=d_list[::-1]

			d_ar=[{}]*len(lat_list)
			for i in range(len(lat_list)):
				d_ar[i]={"latitude":lat_list[i],"longitude":lon_list[i]}
			location={"locations":d_ar}
			json_data=json.dumps(location,skipkeys=int).encode('utf8')

			url="https://api.open-elevation.com/api/v1/lookup"
			response = urllib.request.Request(url,json_data,headers={'Content-Type': 'application/json'})
			fp=urllib.request.urlopen(response)

			res_byte=fp.read()
			res_str=res_byte.decode("utf8")
			js_str=json.loads(res_str)
			fp.close()

			response_len=len(js_str['results'])
			elev_list=[]
			for j in range(response_len):
				elev_list.append(js_str['results'][j]['elevation'])

			mean_elev=round((sum(elev_list)/len(elev_list)),3)
			min_elev=min(elev_list)
			max_elev=max(elev_list)
			distance=d_list_rev[-1]

			base_reg=0
			plt.figure(figsize=(10,4))
			plt.plot(d_list_rev,elev_list)
			plt.plot([0,distance],[min_elev,min_elev],'--g',label='min: '+str(min_elev)+' m')
			plt.plot([0,distance],[max_elev,max_elev],'--r',label='max: '+str(max_elev)+' m')
			plt.plot([0,distance],[mean_elev,mean_elev],'--y',label='ave: '+str(mean_elev)+' m')
			plt.fill_between(d_list_rev,elev_list,base_reg,alpha=0.1)
			plt.text(d_list_rev[0],elev_list[0],"P1")
			plt.text(d_list_rev[-1],elev_list[-1],"P2")
			plt.xlabel("Distance(km)")
			plt.ylabel("Elevation(m)")
			plt.grid()
			plt.legend(fontsize='small')
			plt.show()

	def haversine(self,lat1,lon1,lat2,lon2):
		lat1_rad=math.radians(lat1)
		lat2_rad=math.radians(lat2)
		lon1_rad=math.radians(lon1)
		lon2_rad=math.radians(lon2)
		delta_lat=lat2_rad-lat1_rad
		delta_lon=lon2_rad-lon1_rad
		a=math.sqrt((math.sin(delta_lat/2))**2+math.cos(lat1_rad)*math.cos(lat2_rad)*(math.sin(delta_lon/2))**2)
		d=2*6371000*math.asin(a)
		return d

	def disableButton(self):
		check_campi = [self.coord_xa.text(), self.coord_ya.text(),self.coord_xb.text(), self.coord_yb.text()]
		check_value = []

		for x in check_campi:
			if len(x) > 0:
				value_campi = 1
				check_value.append(value_campi)
			else:
				value_campi = 0
				check_value.append(value_campi)
		campi = sum(check_value)

		if campi > 3:
			self.button_box.setEnabled(True)
		else:
			self.button_box.setEnabled(False)

	def update_num(self, value):
		try:
			valore = float(value.text())
		except:
			value.setText('')

	def radio_vertex_1_clicked(self, enabled):
		if enabled:
			self.coord_xa.setEnabled(True)
			self.coord_ya.setEnabled(True)
			self.coord_xb.setEnabled(True)
			self.coord_yb.setEnabled(True)
			self.dir_input.setEnabled(False)
			self.pushButton_in.setEnabled(False)
			self.alert_text.hide()

	def radio_vertex_2_clicked(self, enabled):
		if enabled:
			self.coord_xa.setEnabled(False)
			self.coord_ya.setEnabled(False)
			self.coord_xb.setEnabled(False)
			self.coord_yb.setEnabled(False)
			self.dir_input.setEnabled(True)
			self.pushButton_in.setEnabled(True)
			self.alert_text.show()