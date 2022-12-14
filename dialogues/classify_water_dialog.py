# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ClassifyWaterDialog
                                 A QGIS plugin
 This is a plugin to perform water classification on multispectral images
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-10-05
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Edmond Baloku
        email                : edmondbv@hotmail.com
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

import cv2
import numpy as np
import os
import shutil
import spectral.io.envi as envi
import scipy.stats as stats

from PyQt5.QtWidgets import QFileDialog, QDialog
import PyQt5.uic as uic
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor

from ..classify_water.atmospheric_correction import atmospheric_correction
from ..classify_water.cube_calibration import cube_calibration


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'classify_water_dialog_base.ui'))


class ClassifyWater(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ClassifyWater, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

        self.setupUi(self)

        self.open_file_button.clicked.connect(self.set_filepath)
        self.calibrate_img_button.clicked.connect(self.perform_cube_calibration)
        self.set_pixels_button.clicked.connect(self.set_pixels)
        self.atmospheric_correction_button.clicked.connect(self.perform_atmospheric_correction)
        self.classify_water_button.clicked.connect(self.perform_water_classification)
        self.save_img_button.clicked.connect(self.save_img_dialog)
        self.save_array_button.clicked.connect(self.save_array_dialog)

        self.input_exp.editingFinished.connect(self.set_exp)

        self.filepath = ""
        self.path_to_directory = ""

        self.exp = 0.035

        self.water_pixel_pos_1 = (0, 0)
        self.water_pixel_pos_2 = (0, 0)
        self.water_pixel_pos_3 = (0, 0)

        self.new_img_status  = ""
        

    def set_filepath(self):
        try:
            options = QFileDialog.Options()
            self.filepath, _ = QFileDialog.getOpenFileName(self, "", "", "HDR Files (*.hdr)", options=options)
            self.open_file()

        except Exception as err:
            print("Error when setting filepath: " + str(err))


    def open_file(self):
        if self.filepath != "":
            self.original_img, _, _= self.get_img_from_hdr(self.filepath)
            self.show_img(self.original_img, self.label_original_img)


    def get_img_from_hdr(self, filepath):
        rgb = (60,80,90)

        try:
            envi_img = envi.open(filepath)

            full_img_array = envi_img.load()
            img_array = full_img_array[:,:,(rgb)]
            img_array = ((img_array - img_array.min()) / img_array.max() * 255).astype(np.uint8)
            np_array = np.array(img_array)

            img = cv2.cvtColor(np_array, cv2.COLOR_BGR2RGB)

            return img, full_img_array, envi_img
        
        except Exception as err:
            print("Error when getting image from hdr: " + str(err))


    def show_img(self, img, label, paint=False):
        height, width, _ = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

        if paint:
            self.paint_pixels(q_img)

        label.setPixmap(QPixmap.fromImage(q_img))


    def paint_pixels(self, q_img):
        painter = QPainter(q_img)
        painter.setPen(QPen(QColor(255, 0, 0), 10))
        painter.drawPoint(self.water_pixel_pos_1[0], self.water_pixel_pos_1[1])

        painter.setPen(QPen(QColor(0, 255, 0), 10))
        painter.drawPoint(self.water_pixel_pos_2[0], self.water_pixel_pos_2[1]) 
        
        painter.setPen(QPen(QColor(255, 255, 0), 10))
        painter.drawPoint(self.water_pixel_pos_3[0], self.water_pixel_pos_3[1]) 
        painter.end()


    def set_exp(self):
        if self.input_exp.text() != "":
            self.exp = float(self.input_exp.text())


    def perform_cube_calibration(self):
        try:
            bip_path = self.filepath[:-4] + ".bip"
            cube_calibrated, self.calibrated_wl, self.cube_scaled = cube_calibration(bip_path, self.exp)

            # Cretes a new calibrated .bip and .hdr file in the same directory
            cube_calibrated.astype(dtype = "uint16").tofile(self.filepath[:-4] + "_calibrated.bip")
            calibrated_hdr_path = shutil.copy2(self.filepath, self.filepath[:-4] + "_calibrated.hdr")   

            self.calibrated_img, self.calibrated_img_array, self.calibrated_envi_img = self.get_img_from_hdr(calibrated_hdr_path)
            self.calibrated_img = self.tune_overexposed_img(self.cube_scaled[:,::-1,:], cube_calibrated[:,::-1,:], wl=self.calibrated_wl)
            self.show_img(self.calibrated_img, self.label_new_img, paint=True)

            self.new_img_status  = "calibrated"

        except Exception as err:
            print("Error when performing cube calibration: " + str(err))


    def set_pixels(self):
        if self.input_pixel_1.text() != "":
            self.water_pixel_pos_1 = tuple(map(int, self.input_pixel_1.text().split(",")))
        if self.input_pixel_2.text() != "":
            self.water_pixel_pos_2 = tuple(map(int, self.input_pixel_2.text().split(",")))
        if self.input_pixel_3.text() != "":
            self.water_pixel_pos_3 = tuple(map(int, self.input_pixel_3.text().split(",")))
            
        self.show_img(self.calibrated_img, self.label_new_img, paint=True)


    def perform_atmospheric_correction(self):
        try:    
            self.cube_atmos_corrected = atmospheric_correction(self.calibrated_envi_img ,self.calibrated_img_array, self.water_pixel_pos_1, self.water_pixel_pos_2, self.water_pixel_pos_3)

            self.atmos_corrected_img =  self.tune_overexposed_img(self.cube_scaled[:,::-1,:], self.cube_atmos_corrected[:,::-1,:], wl=self.calibrated_wl)
            self.show_img(self.atmos_corrected_img, self.label_new_img)

            # Cretes a new atmospheric corrected .bip and .hdr file in the same directory
            self.cube_atmos_corrected.astype(dtype = "uint16").tofile(self.filepath[:-4] + "_atmospheric_corrected.bip")
            shutil.copy2(self.filepath, self.filepath[:-4] + "_atmospheric_corrected.hdr")

            self.new_img_status = "atmospheric_corrected"
        
        except Exception as err:
            print("Error when performing atmospheric correction: " + str(err))


    def tune_overexposed_img(self, cube, cube_calibrated, R_w=630, G_w=540, B_w=480, bandpass=10, wl=[]):
        ''' Assumes input cube has been flipped and scaled if necessary, and
        radiometrically calibrated already if that is desired.
        Cube before calibration is used to make mask for overexposed values.

        This function is written by Marie B??e Henriksen and can be found in https://github.com/NTNU-SmallSat-Lab/cal-char-corr
        '''
        
        num_frames, image_height, _ = cube.shape
        
        _, R_start = self.find_closest_wavelength(wl, R_w - (bandpass / 2))
        _, R_stop  = self.find_closest_wavelength(wl, R_w + (bandpass / 2))
        _, G_start = self.find_closest_wavelength(wl, G_w - (bandpass / 2))
        _, G_stop  = self.find_closest_wavelength(wl, G_w + (bandpass / 2))
        _, B_start = self.find_closest_wavelength(wl, B_w - (bandpass / 2))
        _, B_stop  = self.find_closest_wavelength(wl, B_w + (bandpass / 2))

        # Use cube before calibration to make overexposed mask
        im_R = []
        im_G = []
        im_B = []
        for i in range(num_frames):
            frame = cube[i,:,:]
            
            R_band = frame[:,R_start:R_stop]
            R_line = np.average(R_band, axis=1)
            im_R.append(R_line)

            G_band = frame[:,G_start:G_stop]
            G_line = np.average(G_band, axis=1)
            im_G.append(G_line)

            B_band = frame[:,B_start:B_stop]
            B_line = np.average(B_band, axis=1)
            im_B.append(B_line)
    
        # Make overexposed mask
        over_exposed_lim = 4094
        mask = np.ones([num_frames, image_height])
        mask = np.where(np.array(im_R) > over_exposed_lim, 0, mask) # overexposed value gives 0 in mask
        mask = np.where(np.array(im_G) > over_exposed_lim, 0, mask)
        mask = np.where(np.array(im_B) > over_exposed_lim, 0, mask)
        
        # Work with calibrated cube
        im_R = []
        im_G = []
        im_B = []
        for i in range(num_frames):
            frame = cube_calibrated[i,:,:]

            R_band = frame[:,R_start:R_stop]
            R_line = np.average(R_band, axis=1)
            im_R.append(R_line)

            G_band = frame[:,G_start:G_stop]
            G_line = np.average(G_band, axis=1)
            im_G.append(G_line)

            B_band = frame[:,B_start:B_stop]
            B_line = np.average(B_band, axis=1)
            im_B.append(B_line)
            
        image = np.zeros([image_height, num_frames, 3])
        for i in range(num_frames):
            # Set overexposed pixels to zero by multiplying with mask
            image[:, i, 0] = im_R[i] * mask[i,:] 
            image[:, i, 1] = im_G[i] * mask[i,:]
            image[:, i, 2] = im_B[i] * mask[i,:]
        
        # Scale by max value to automatically brighten image
        max_value = np.max(image)
        image = image / max_value * 255
        
        # Set overexposed values to max value again - inefficient way
        overexp_value = 255
        for j in range(num_frames):
            for i in range(image_height):
                if mask[j, i] == 0:
                    image[i, j, 0] = overexp_value
                    image[i, j, 1] = overexp_value
                    image[i, j, 2] = overexp_value
        

        image = image.astype(dtype = 'uint8')
        image = np.rot90(image, 3)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return image


    def perform_water_classification(self):
        if self.original_classify_radiobutton.isChecked():
            self.classify_water_original()

        elif self.corrected_classify_radiobutton.isChecked():
            self.classify_water_atmos_corrected()


    def classify_water_original(self):
        try:
            original_cube = envi.open(self.filepath)
            height, width, _ = original_cube.shape

            wl = list(map(float, original_cube.metadata["wavelengths"]))
            wl = wl[::-1]

            water_img_array = np.zeros((height,width))

            closest_wl_750, _ = self.find_closest_wavelength(wl, 750)
            closest_wl_760, _ = self.find_closest_wavelength(wl, 760)

            for i in range(height):
                for j in range(width):
                    pixel = original_cube.read_pixel(i,j)
                    wl_750 = pixel[wl.index(closest_wl_750)]
                    wl_763 = pixel[wl.index(closest_wl_760)]

                    if wl_750 > wl_763:
                        diff = wl_750 - wl_763
                        if diff < 3000:
                            water_img_array[i,j] = 1

            self.create_water_img(water_img_array)
            self.show_img(self.water_img, self.label_new_img)
            self.new_img_status  = "classified"

        except Exception as err:
            print("Error when classifying water:", str(err))


    def classify_water_atmos_corrected(self):
        height, width, _ = self.cube_atmos_corrected.shape

        water_pixel_1  = self.cube_atmos_corrected[self.water_pixel_pos_1[1], self.water_pixel_pos_1[0]][4:]
        water_pixel_2  = self.cube_atmos_corrected[self.water_pixel_pos_2[1], self.water_pixel_pos_2[0]][4:] 
        water_pixel_3  = self.cube_atmos_corrected[self.water_pixel_pos_3[1], self.water_pixel_pos_3[0]][4:] 

        avg_water_pixel = (water_pixel_1 + water_pixel_2 + water_pixel_3) / 3

        atmos_corrected_water_cube = np.zeros((height, width))
        for i in range(height):
            for j in range(width):
                pixel = self.cube_atmos_corrected[i,j]

                if stats.pearsonr(pixel[4:], avg_water_pixel)[0] > 0.8:
                    atmos_corrected_water_cube[i,j] = 1


        self.create_water_img(atmos_corrected_water_cube)
        self.show_img(self.water_img, self.label_new_img)
        self.new_img_status  = "classified"


    def find_closest_wavelength(self, wl, target_wl):
        closest_wl = wl[min(range(len(wl)), key = lambda i: abs(wl[i] - target_wl))]
    
        wl_list = wl
        if type(wl)!= list:
            wl_list = wl.tolist()
        index = wl_list.index(closest_wl)

        return closest_wl, index
    

    def create_water_img(self, water_img_array):
        water_img_array = water_img_array[:,:]
        water_img_array = ((water_img_array - water_img_array.min()) / water_img_array.max() * 255).astype(np.uint8)
        self.water_np_array = np.array(water_img_array)

        self.water_img = cv2.cvtColor(self.water_np_array, cv2.COLOR_BGR2RGB)


    def save_img_dialog(self):
        if self.new_img_status == "calibrated":
            filename_ending = "_calibrated"
        elif self.new_img_status == "atmospheric_corrected":
            filename_ending = "_atmospheric_corrected"
        elif self.new_img_status == "classified":
            filename_ending = "_water_highlighted"
        
        try:
            options = QFileDialog.Options()
            self.path_to_directory, _ = QFileDialog.getSaveFileName(self, "", self.filepath[:-4] + filename_ending, "PNG File (*.png) ;; JPEG File (*.jpeg) ;; PDF File (*.pdf)", options=options)
            self.save_img()

        except Exception as err:
            print("Error in save image dialog: " + str(err))


    def save_img(self):
        if self.path_to_directory != "":
            if self.new_img_status == "calibrated":
                cv2.imwrite(self.path_to_directory, self.calibrated_img)
            elif self.new_img_status == "atmospheric_corrected":
                cv2.imwrite(self.path_to_directory, self.atmos_corrected_img)
            elif self.new_img_status == "classified":
                cv2.imwrite(self.path_to_directory, self.water_img)
    

    def save_array_dialog(self):
        if self.new_img_status == "calibrated":
            filename_ending = "_calibrated"
        elif self.new_img_status == "atmospheric_corrected":
            filename_ending = "_atmospheric_corrected"
        elif self.new_img_status == "classified":
            filename_ending = "_water_highlighted"

        try:
            options = QFileDialog.Options()
            self.path_to_directory, file_type = QFileDialog.getSaveFileName(self, "", self.filepath[:-4] + filename_ending, "Numpy File (*.npy) ;; Text file (*.txt)", options=options)
            self.save_array(file_type)

        except Exception as err:
            print("Error in saving array dialog: " + str(err))


    def save_array(self, filetype):
        if self.path_to_directory != "":
            if filetype == "Numpy File (*.npy)":
                if self.new_img_status == "calibrated":
                    np.save(self.path_to_directory, self.calibrated_img_array)
                elif self.new_img_status == "atmospheric_corrected":
                    np.save(self.path_to_directory, self.cube_atmos_corrected)
                elif self.new_img_status == "classified":
                    np.save(self.path_to_directory, self.water_np_array)
            else:
                if self.new_img_status == "calibrated":
                    np.savetxt(self.path_to_directory, self.calibrated_img_array)
                elif self.new_img_status == "atmospheric_corrected":
                    np.savetxt(self.path_to_directory, self.cube_atmos_corrected)
                elif self.new_img_status == "classified":
                    np.savetxt(self.path_to_directory, self.water_np_array)