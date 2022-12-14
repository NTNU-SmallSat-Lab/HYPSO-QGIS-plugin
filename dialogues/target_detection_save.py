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

from .target_detection_dialog import TargetDetectionDialog

from PyQt5.QtWidgets import QFileDialog, QDialog
import PyQt5.uic as uic

import cv2
import numpy as np
import shutil

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'target_detection_save_base.ui'))


class TargetDetectionSave(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(TargetDetectionSave, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
    
        self.buttonBox.accepted.connect(self.save_as)
        self.buttonBox.rejected.connect(self.close)
        
        self.parent = parent
        
        
    def save_as(self):        
        if self.parent.path_to_save_folder == "":
            self.parent.path_to_save_folder = self.parent.path_to_img
            
        if self.parent.path_to_img == "":
            return
        
        if self.cb_spec_sig_as_npy.isChecked():
            try:
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self.parent, 'Save File', self.parent.path_to_img[:-4] + "_spectral_signature", "Numpy files (*.npy)", options=options)
                np.save(path, self.parent.spectral_signature)
                print("Saving spectral signature")
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving spectral signature as npy: " + str(e))
        
        if self.parent.path_to_img == "" or not self.parent.generated:
            return
        
        name = self.parent.path_to_img[self.parent.path_to_img.rfind("/")+1:-4]
        
        if self.cb_corr_as_npy.isChecked():
            try:
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.parent.path_to_img[:-4] + "_correlation_coefficients", "Numpy files (*.npy)", options=options)
                np.save(path, self.parent.corr_raw)
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving correlation coefficients as npy: " + str(e))
                
        if self.cb_corr_as_png.isChecked():
            try:
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.parent.path_to_img[:-4] + "_correlation_coefficients", "PNG files (*.png)", options=options)
                cv2.imwrite(path, self.parent.corr_img)
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving corrrelatinon coefficients as png: " + str(e))
        
        if self.cb_thresholded_as_npy.isChecked():
            try: 
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.parent.path_to_img[:-4] + "_thresholded_correlation_coefficients_" + str(self.parent.threshold), "Numpy files (*.npy)", options=options)
                np.save(path, self.parent.corr_thresh_raw)
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving thresholded corrrelation coefficients as npy: " + str(e))
                
        if self.cb_thresholded_as_png.isChecked():
            try:
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.parent.path_to_img[:-4] + "_thresholded_correlation_coefficients_" + str(self.parent.threshold), "PNG files (*.png)", options=options)
                cv2.imwrite(path, self.parent.corr_thresh_img)
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving thresholded corrrelation coefficients as png: " + str(e))
                
        if self.cb_reduced_by_mask.isChecked():
            try:
                options = QFileDialog.Options()
                path, _ = QFileDialog.getSaveFileName(self, 'Save File', self.parent.path_to_img[:-4] + "_reduced_by_mask", "BIP files (*.bip)", options=options)
                self.parent.cube_reduced.astype(dtype = "uint16").tofile(path)
                shutil.copy2(self.parent.path_to_img, self.parent.path_to_img[:-4]+"_reduced_by_mask.hdr")
            except Exception as e:
                print(self.parent.get_timestamp() + " Error when saving reduced bip: " + str(e))