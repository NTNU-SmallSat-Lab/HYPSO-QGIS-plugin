# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TargetDetectionDialog
                                 A QGIS plugin
 This plugin allows you to find probability of similarity in spectral intensity across a multispectral image
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-10-28
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Markus Haldorsen
        email                : markushaldorsen@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5.QtWidgets import QFileDialog, QDialog, QListWidgetItem
import PyQt5.uic as uic
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QPixmap

import cv2
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.figure import Figure, SubplotParams
import spectral.io.envi as envi
import numpy as np
import scipy.stats as stats
import time
import matplotlib.pyplot as plt
import shutil

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'target_detection_dialog_base.ui'))


class TargetDetectionDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(TargetDetectionDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.pb_open_img.clicked.connect(self.set_path_to_img)
        self.pb_open_poi.clicked.connect(self.set_path_to_poi)
        self.pb_set_coord.clicked.connect(self.set_coordinates)
        self.pb_generate_result_imgs.clicked.connect(self.generate_result_imgs)
        self.pb_exit.clicked.connect(self.close)
        
        self.sld_threshold.valueChanged.connect(self.set_threshold_by_slider)
        
        self.le_x.editingFinished.connect(self.set_x)
        self.le_y.editingFinished.connect(self.set_y)
        self.le_threshold.editingFinished.connect(self.set_threshold_by_input)
        
        self.rb_thresholded.toggled.connect(self.update_result_img)
        
        self.cb_external_poi.toggled.connect(self.set_external)
        
        self.threshold = 0.9
        self.path_to_img = ""
        self.path_to_poi = ""
        self.path_to_save_folder = ""
        self.x = 0
        self.y = 0
        self.result_generated = False
        self.spectral_signature = np.array
        self.show_dot = True
        self.full_img_loaded = False
        
        self.pb_open_poi.setVisible(False)
        self.lbl_path_to_poi.setVisible(False)
        
        self.select_td_method.addItems(["Pearson's R", "Spearman's Rho"])

    def set_path_to_img(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "HDR Files (*.hdr)", options=options)
        self.path_to_img = file_name
        
        if file_name:
            self.open_img()
            
    def set_path_to_poi(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "NPY Files (*.npy)", options=options)
        self.path_to_poi = file_name
        if file_name:
            self.open_poi()
            
    def get_path_to_img(self):
        return self.path_to_img
    
    def get_path_to_poi(self):
        return self.path_to_poi
    
    def open_img(self):
        if self.path_to_img != "":
            print(self.get_timestamp() + " Opening file: " + self.path_to_img)
            self.lbl_path_to_img.setText("Filename: \n" + self.path_to_img.split("/").pop())
 
            self.show_original_img()
        else:
            self.lbl_path_to_img.setText("Filename: \nNo file selected")
            
    def open_poi(self):
        if self.path_to_poi != "":
            print(self.get_timestamp() + " Opening file: " + self.path_to_poi)
            self.lbl_path_to_poi.setText("Filename: \n" + self.path_to_poi.split("/").pop())
            
            self.spectral_signature = np.load(self.path_to_poi)
            
        else:
            self.lbl_path_to_poi.setText("Filename: \nNo file selected")
            
    def set_external(self):
        if self.cb_external_poi.isChecked():
            self.lbl_coordinate_input.setVisible(False)
            self.lbl_x.setVisible(False)
            self.le_x.setVisible(False)
            self.lbl_y.setVisible(False)
            self.le_y.setVisible(False)
            self.pb_set_coord.setVisible(False)
            
            self.pb_open_poi.setVisible(True)
            self.lbl_path_to_poi.setVisible(True)
            
            self.show_dot = False
        else: 
            self.lbl_coordinate_input.setVisible(True)
            self.lbl_x.setVisible(True)
            self.le_x.setVisible(True)
            self.lbl_y.setVisible(True)
            self.le_y.setVisible(True)
            self.pb_set_coord.setVisible(True)
            
            self.pb_open_poi.setVisible(False)
            self.lbl_path_to_poi.setVisible(False)
            
            self.show_dot = True
            
    def set_x(self):
        if self.le_x.text() != "" and self.full_img_loaded:
            try: 
                self.x = int(self.le_x.text())
                print(self.get_timestamp() + " Setting x coordinate to: " + self.le_x.text())
                
                self.update_pixel_of_interest()
            except Exception as e:
                print(self.get_timestamp() + " Error: " + str(e))
                
                return
        else: 
            self.x = 0
        
    def set_y(self):
        if self.le_y.text() != "" and self.full_img_loaded:     
            try:
                print(self.get_timestamp() + " Setting y coordinate to: " + self.le_y.text())
                self.y = int(self.le_y.text())
                
                self.update_pixel_of_interest()
            except Exception as e:
                print(self.get_timestamp() + " Error: " + str(e))
                
                return
        else:
            self.y = 0
            
        
    def set_coordinates(self):
        self.set_x()
        self.set_y()
        
    def update_pixel_of_interest(self):
        show_dot = True
        if self.cb_external_poi.isChecked():
            show_dot = False
            
        self.show_original_img(show_dot)
        self.spectral_signature = self.full_img.read_pixel(self.x, self.y)
    
    def get_x(self):
        return self.x
    
    def get_y(self):
        return self.y
            
    def set_threshold_by_slider(self):
        self.threshold = self.sld_threshold.value() / 10000
        self.le_threshold.setText(str(self.threshold))
        
        print(self.get_timestamp() + " Setting threshold to: " + str(self.threshold))
        
        if self.result_generated:
            self.update_threshold_img()
            if self.rb_thresholded.isChecked():
                self.update_result_img()
        
    def set_threshold_by_input(self):
        try:
            self.threshold = float(self.le_threshold.text())
            self.sld_threshold.setValue(int(self.threshold * 10000))
            print(self.get_timestamp() + " Setting threshold to: " + str(self.threshold))
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
            
            return
        
        if self.result_generated:
            self.update_threshold_img()
            if self.rb_thresholded.isChecked():
                self.update_result_img()
            
    def get_threshold(self):
        return self.threshold

    def show_original_img(self, show_dot = True):
        if self.path_to_img == "":
            return
        
        try:
            img = self.get_img_from_hdr()
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
            
            return

        height, width, _ = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        if self.show_dot:
            self.paint_dot(q_img)
        
        self.lbl_original_img.setPixmap(QPixmap.fromImage(q_img))
        
        
    def paint_dot(self, q_img):
        painter = QPainter(q_img)
        painter.setPen(QPen(QColor(255, 0, 0), 10))
        painter.drawPoint(self.y, self.x) # X and Y are opposite order because of how envi processes the image. 
        painter.end()
    
    def get_img_from_hdr(self):
        try:
            self.full_img = envi.open(self.path_to_img)
            self.full_img_loaded = True
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
                        
            raise Exception("Error opening file. Make sure that both the .hdr and .bip files are in the same folder.")
        
        img_array = self.full_img.load()
        
        R = 60
        G = 80
        B = 90
        
        img_array = img_array[:,:,(R,G,B)]
        img_array = ((img_array - img_array.min()) / img_array.max() * 255).astype(np.uint8)
        
        np_img = np.array(img_array)
        img = cv2.cvtColor(np_img, cv2.COLOR_BGR2RGB)
        
        return img
    
    def generate_result_imgs(self):
        print(self.get_timestamp() + " Generating...")
        
        self.corr_raw = self.correlation_coefficients(self.spectral_signature)
        self.corr_img = self.raw_to_img(self.corr_raw, cv2.COLORMAP_JET)
     
        self.corr_thresh_raw = self.threshold_correlation_coefficients()
        self.corr_thresh_img = self.raw_to_img(self.corr_thresh_raw, cv2.COLORMAP_BONE)
        
        height, width, _ = self.corr_img.shape
        bytes_per_line = 3 * width
        self.corr_q_img = QImage(self.corr_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.corr_thresh_q_img = QImage(self.corr_thresh_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        self.update_result_img()
        self.result_generated = True
        
    def update_threshold_img(self):
        self.corr_thresh_raw = self.threshold_correlation_coefficients()
        self.corr_thresh_img = self.raw_to_img(self.corr_thresh_raw, cv2.COLORMAP_BONE)
        
        height, width, _ = self.corr_thresh_img.shape
        bytes_per_line = 3 * width
        self.corr_thresh_q_img = QImage(self.corr_thresh_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

    def correlation_coefficients(self, poi):
        print(self.select_td_method.currentText())
        if self.select_td_method.currentText() == "Pearson's R":
            return self.pearsons_r_coefficients(poi)
        elif self.select_td_method.currentText() == "Spearman's Rho":
            return self.spearman_rho_coefficients(poi)
        
        return None

    def pearsons_r_coefficients(self, poi):
        corr = np.ones((self.full_img.shape[0], self.full_img.shape[1]))
        
        for i in range(self.full_img.shape[0]):
            for j in range(self.full_img.shape[1]):
                pixel = self.full_img.read_pixel(i, j)
                corr[i,j] = stats.pearsonr(pixel, poi)[0]
                
        return corr
    
    def spearman_rho_coefficients(self, poi):
        corr = np.ones((self.full_img.shape[0], self.full_img.shape[1]))
        
        for i in range(self.full_img.shape[0]):
            for j in range(self.full_img.shape[1]):
                pixel = self.full_img.read_pixel(i, j)
                corr[i,j] = stats.spearmanr(pixel, poi)[0]
                
        return corr
    
    def threshold_correlation_coefficients(self):
        corr_thresh = self.corr_raw.copy()
        corr_thresh[corr_thresh < self.threshold] = 0
        corr_thresh[corr_thresh >= self.threshold] = 1
        
        return corr_thresh
    
    def raw_to_img(self, raw, colormap):
        img = cv2.normalize(raw, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        img = cv2.applyColorMap(img, colormap)
        
        return img
    
    def update_result_img(self):
        if self.rb_thresholded.isChecked():
            self.lbl_result_img.setPixmap(QPixmap.fromImage(self.corr_thresh_q_img))
        else:
            self.lbl_result_img.setPixmap(QPixmap.fromImage(self.corr_q_img))
        
    def get_timestamp(self):
        return time.strftime("%H:%M:%S", time.localtime()) 