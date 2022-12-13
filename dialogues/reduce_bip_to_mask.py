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
    os.path.dirname(__file__), 'reduce_bip_to_mask_base.ui'))


class ReduceBipToMaskDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ReduceBipToMaskDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.pb_open_img.clicked.connect(self.set_path_to_img)
        self.pb_open_mask.clicked.connect(self.set_path_to_mask)
        self.pb_save_as.clicked.connect(self.save_as)
        self.pb_exit.clicked.connect(self.close)
        
        self.path_to_img = ""
        self.path_to_poi = ""
        self.path_to_save_folder = ""

    def set_path_to_img(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "HDR Files (*.hdr)", options=options)
        self.path_to_img = file_name
        
        if file_name:
            self.open_img()
            
    def set_path_to_mask(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "NPY Files (*.npy)", options=options)
        self.path_to_mask = file_name
        if file_name:
            self.open_mask()
            
    def get_path_to_img(self):
        return self.path_to_img
    
    def get_path_to_poi(self):
        return self.path_to_poi
    
    def open_img(self):
        if self.path_to_img != "":
            print(self.get_timestamp() + " Opening file: " + self.path_to_img)
            self.lbl_path_to_img.setText("Filename: \n" + self.path_to_img.split("/").pop())
 
            self.show_original_image()
        else:
            self.lbl_path_to_img.setText("Filename: \nNo file selected")
            
    def open_mask(self):
        if self.path_to_mask != "":
            print(self.get_timestamp() + " Opening file: " + self.path_to_mask)
            self.lbl_path_to_mask.setText("Filename: \n" + self.path_to_mask.split("/").pop())
            
            self.mask = np.load(self.path_to_mask)
            self.show_mask()
            
        else:
            self.lbl_path_to_mask.setText("Filename: \nNo file selected")
            
            
    def show_original_image(self, show_dot = True):
        if self.path_to_img == "":
            return
        try:
            img = self.get_image_from_hdr()
        except Exception as e:
            print(self.get_timestamp() + " Error: " + str(e))
            
            return

        height, width, _ = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        self.lbl_original_image.setPixmap(QPixmap.fromImage(q_img))
    
    def show_mask(self):
        self.mask_img = self.raw_to_img(self.mask, cv2.COLORMAP_BONE)
        
        height, width, _ = self.mask_img.shape
        bytes_per_line = 3 * width
        self.mask_q_img = QImage(self.mask_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        self.lbl_result_image.setPixmap(QPixmap.fromImage(self.mask_q_img))
    
    def get_image_from_hdr(self):
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
    
    def raw_to_img(self, raw, colormap):
        img = cv2.normalize(raw, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        img = cv2.applyColorMap(img, colormap)
        
        return img
    
    def update_result_image(self):
        self.lbl_result_image.setPixmap(QPixmap.fromImage(self.corr_thresh_q_img))
        
    def get_timestamp(self):
        return time.strftime("%H:%M:%S", time.localtime())
    
    def save_as(self):
        # Go through each pixel in self.full_img and self.mask. If self.mask is 1, keep the pixel in self.full_img. If the mask is 0, set the pixel to 0.
        # Save the new image as a .bip file.
        if self.full_img_loaded == False:
            return
        
        self.cube_reduced = np.zeros(self.full_img.shape)
        for i in range(self.full_img.shape[0]):
            for j in range(self.full_img.shape[1]):
                if self.mask[i,j] == 1:
                    self.cube_reduced[i,j,:] = self.full_img.read_pixel(i,j)
                else:
                    self.cube_reduced[i,j,:] = 0
        
        if self.path_to_save_folder == "":
            self.path_to_save_folder = self.path_to_img
            
        if self.path_to_save_folder == "":
            return
        
        try:
            options = QFileDialog.Options()
            path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.path_to_img[:-4] + "_reduced_by_mask", "BIP files (*.bip)", options=options)
            print("hi")
            # np.save(path, self.spectral_signature)
            self.cube_reduced.astype(dtype = "uint16").tofile(path)
            print("hello")
            shutil.copy2(self.path_to_img, self.path_to_img[:-4]+"_reduced_by_mask.hdr")
            print("Saving spectral signature")
        except Exception as e:
            print(self.get_timestamp() + " Error when saving reduced bip: " + str(e))