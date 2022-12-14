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

from PyQt5.QtWidgets import QFileDialog, QDialog
import PyQt5.uic as uic
from PyQt5.QtGui import QImage, QPainter, QPen, QBrush, QColor, QPixmap

import cv2
import spectral.io.envi as envi
import spectral as spy
import numpy as np
import scipy.stats as stats
import time

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
        
        self.pb_open_file.clicked.connect(self.set_path_to_file)
        self.pb_set_coord.clicked.connect(self.set_coordinates)
        self.pb_generate.clicked.connect(self.generate_result_images)
        self.pb_save_as.clicked.connect(self.save_as)
        self.pb_exit.clicked.connect(self.close)
        
        self.sld_threshold.valueChanged.connect(self.set_threshold_by_slider)
        
        self.le_x.editingFinished.connect(self.set_x)
        self.le_y.editingFinished.connect(self.set_y)
        self.le_threshold.editingFinished.connect(self.set_threshold_by_input)
        
        self.rb_thresholded.toggled.connect(self.update_result_image)
        
        self.threshold = 0.9
        self.path_to_file = ""
        self.path_to_save_folder = ""
        self.x = 0
        self.y = 0
        self.generated = False

    def set_path_to_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "HDR Files (*.hdr)", options=options)
        self.path_to_file = file_name
        
        if file_name:
            self.open_file()
            
    def get_path_to_file(self):
        return self.path_to_file
    
    def open_file(self):
        if self.path_to_file != "":
            print(self.get_timestamp() + " Opening file: " + self.path_to_file)
            self.lbl_path_to_file.setText("Path to file: \n" + self.path_to_file)
 
            self.show_original_image()
        else:
            self.lbl_path_to_file.setText("Path to file: \nNo file selected")
            
    def set_x(self):
        if self.le_x.text() != "":
            try: 
                self.x = int(self.le_x.text())
                print(self.get_timestamp() + " Setting x coordinate to: " + self.le_x.text())
            except Exception as e:
                print(self.get_timestamp() + " Error: " + str(e))
                
                return
        else: 
            self.x = 0
            
        self.show_original_image()
        
    def set_y(self):
        if self.le_y.text() != "":     
            try:
                print(self.get_timestamp() + " Setting y coordinate to: " + self.le_y.text())
                self.y = int(self.le_y.text())
            except Exception as e:
                print(self.get_timestamp() + " Error: " + str(e))
                
                return
        else:
            self.y = 0
            
        self.show_original_image()
        
    def set_coordinates(self):
        self.set_x()
        self.set_y()
    
    def get_x(self):
        return self.x
    
    def get_y(self):
        return self.y
            
    def set_threshold_by_slider(self):
        self.threshold = self.sld_threshold.value() / 10000
        self.le_threshold.setText(str(self.threshold))
        
        print(self.get_timestamp() + " Setting threshold to: " + str(self.threshold))
        
        if self.generated:
            self.update_threshold_image()
            if self.rb_thresholded.isChecked():
                self.update_result_image()
        
    def set_threshold_by_input(self):
        try:
            self.threshold = float(self.le_threshold.text())
            self.sld_threshold.setValue(int(self.threshold * 10000))
            print(self.get_timestamp() + " Setting threshold to: " + str(self.threshold))
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
            
            return
        
        if self.generated:
            self.update_threshold_image()
            if self.rb_thresholded.isChecked():
                self.update_result_image()
            
    def get_threshold(self):
        return self.threshold
    
    def generate_result_images(self):
        print(self.get_timestamp() + " Generating...")
        
        self.corr_raw = self.correlation_coefficients()
        self.corr_img = self.raw_to_img(self.corr_raw, cv2.COLORMAP_JET)
     
        self.corr_thresh_raw = self.threshold_correlation_coefficients()
        self.corr_thresh_img = self.raw_to_img(self.corr_thresh_raw, cv2.COLORMAP_BONE)
        
        height, width, _ = self.corr_img.shape
        bytes_per_line = 3 * width
        self.corr_q_img = QImage(self.corr_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.corr_thresh_q_img = QImage(self.corr_thresh_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        self.update_result_image()
        self.generated = True
    
    def raw_to_img(self, raw, colormap):
        img = cv2.normalize(raw, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        img = cv2.applyColorMap(img, colormap)
        
        return img
        
    def update_result_image(self):
        if self.rb_thresholded.isChecked():
            self.lbl_result_image.setPixmap(QPixmap.fromImage(self.corr_thresh_q_img))
        else:
            self.lbl_result_image.setPixmap(QPixmap.fromImage(self.corr_q_img))

    def show_original_image(self):
        if self.path_to_file == "":
            return
        
        try:
            img = self.get_image_from_hdr()
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
            
            return

        height, width, _ = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        painter = QPainter(q_img)
        painter.setPen(QPen(QColor(255, 0, 0), 10))
        painter.drawPoint(self.y, self.x) # X and Y are opposite order because of how envi processes the image. 
        painter.end()
        
        self.lbl_original_image.setPixmap(QPixmap.fromImage(q_img))
        
    def update_threshold_image(self):
        self.corr_thresh_raw = self.threshold_correlation_coefficients()
        self.corr_thresh_img = self.raw_to_img(self.corr_thresh_raw, cv2.COLORMAP_BONE)
        
        height, width, _ = self.corr_thresh_img.shape
        bytes_per_line = 3 * width
        self.corr_thresh_q_img = QImage(self.corr_thresh_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
    
    def get_image_from_hdr(self):
        try:
            self.full_img = envi.open(self.path_to_file)
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

    def correlation_coefficients(self):
        corr = np.ones((self.full_img.shape[0], self.full_img.shape[1]))
        
        for i in range(self.full_img.shape[0]):
            for j in range(self.full_img.shape[1]):
                pixel = self.full_img.read_pixel(i, j)
                corr[i,j] = stats.pearsonr(pixel, self.full_img.read_pixel(self.x, self.y))[0]

        return corr
    
    def threshold_correlation_coefficients(self):
        corr_thresh = self.corr_raw.copy()
        corr_thresh[corr_thresh < self.threshold] = 0
        corr_thresh[corr_thresh >= self.threshold] = 1
        
        return corr_thresh
    
    def get_timestamp(self):
        return time.strftime("%H:%M:%S", time.localtime())
    
    
    def set_save_directory(self):
        options = QFileDialog.Options()
        folder_name = QFileDialog.getExistingDirectory(self, "QFileDialog.getExistingDirectory()", "", options=options)
        self.path_to_save_folder = folder_name
        
        if folder_name:
            print("Updated path to save folder: ", self.path_to_folder)
    
    def save_as(self):
        options = QFileDialog.Options()
        QFileDialog.getSaveFileName
        folder_name = QFileDialog.getExistingDirectory(self, "QFileDialog.getExistingDirectory()", "", options=options)
        self.path_to_save_folder = folder_name
        
        if self.path_to_save_folder == "":
            self.path_to_save_folder = self.path_to_file
        
        if self.path_to_file == "" or not self.generated:
            return
        
        if self.cb_corr_as_npy.isChecked():
            try:
                np.save(self.path_to_file[:-4] + "_correlation_coefficients.npy", self.corr_raw)
            except Exception as e:
                print(self.get_timestamp() + " Error when saving correlation coefficients as npy: " + str(e))
                
        if self.cb_corr_as_png.isChecked():
            try:
                cv2.imwrite(self.path_to_file[:-4] + "_correlation_coefficients.png", self.corr_img)
            except Exception as e:
                print(self.get_timestamp() + " Error when saving corrrelatinon coefficients as png: " + str(e))
        
        if self.cb_thresholded_as_npy.isChecked():
            try: 
                np.save(self.path_to_file[:-4] + "_thresholded_correlation_coefficients_" + str(self.threshold) + ".npy", self.corr_thresh_raw)
            except Exception as e:
                print(self.get_timestamp() + " Error when saving thresholded corrrelation coefficients as npy: " + str(e))
                
        if self.cb_thresholded_as_png.isChecked():
            try:
                cv2.imwrite(self.path_to_file[:-4] + "_thresholded_correlation_coefficients_" + str(self.threshold) + ".png", self.corr_thresh_img)
            except Exception as e:
                print(self.get_timestamp() + " Error when saving thresholded corrrelation coefficients as png: " + str(e))