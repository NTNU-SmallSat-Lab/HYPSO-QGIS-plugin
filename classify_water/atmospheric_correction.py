import numpy as np
import os
import scipy.stats as stats

def atmospheric_correction(calibrated_envi_img, calibrated_np_array, water_pixel_pos_1, water_pixel_pos_2, water_pixel_pos_3):
    '''
    This method is based on the Empricial Line Fits described by Micheal T. Eismann in the book Hyperspectral Remote Sesing
    '''

    avg_intercept, avg_slope = find_correlation(calibrated_envi_img, water_pixel_pos_1, water_pixel_pos_2, water_pixel_pos_3)

    corrected_np_array = np.zeros((calibrated_np_array.shape[0], calibrated_np_array.shape[1], calibrated_np_array.shape[2]))

    for i in range(calibrated_np_array.shape[0]):
        for j in range(calibrated_np_array.shape[1]):
            pixel = calibrated_np_array[i,j]

            corrected_pixel =  (pixel - avg_intercept) / avg_slope
            pixel = pixel - corrected_pixel

            corrected_np_array[i,j,:] = pixel

    return corrected_np_array

    
def get_ground_station_truth():
    '''
    Source for the ground station data: https://crustal.usgs.gov/speclab/QueryAll07a.php?quick_filter=open_ocean
    '''
    
    dirname = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(dirname, "data/ground_station_data.txt")

    open_ocean_pixel = np.loadtxt(filepath)

    return open_ocean_pixel


def find_correlation(calibrated_envi_img, water_pixel_pos_1, water_pixel_pos_2, water_pixel_pos_3):
    water_pixel_1  = calibrated_envi_img.read_pixel(water_pixel_pos_1[1], water_pixel_pos_1[0])[4:]
    water_pixel_2  = calibrated_envi_img.read_pixel(water_pixel_pos_2[1], water_pixel_pos_2[0])[4:] 
    water_pixel_3  = calibrated_envi_img.read_pixel(water_pixel_pos_3[1], water_pixel_pos_3[0])[4:]  

    open_ocean_pixel = get_ground_station_truth()

    corr_coff_1 = stats.pearsonr(water_pixel_1, open_ocean_pixel[:,1])[0]
    corr_coff_2 = stats.pearsonr(water_pixel_2, open_ocean_pixel[:,1])[0]
    corr_coff_3 = stats.pearsonr(water_pixel_3, open_ocean_pixel[:,1])[0]

    intercept_1 = stats.pearsonr(water_pixel_1, open_ocean_pixel[:,1])[1]
    intercept_2 = stats.pearsonr(water_pixel_2, open_ocean_pixel[:,1])[1]
    intercept_3 = stats.pearsonr(water_pixel_3, open_ocean_pixel[:,1])[1]

    avg_intercept = (intercept_1 + intercept_2 + intercept_3) / 3        

    slope_1 = corr_coff_1 * np.std(open_ocean_pixel[:,1]) / np.std(water_pixel_1)
    slope_2 = corr_coff_2 * np.std(open_ocean_pixel[:,1]) / np.std(water_pixel_2)
    slope_3 = corr_coff_3 * np.std(open_ocean_pixel[:,1]) / np.std(water_pixel_3)

    avg_slope = (slope_1 + slope_2 + slope_3) / 3
    
    return avg_intercept, avg_slope