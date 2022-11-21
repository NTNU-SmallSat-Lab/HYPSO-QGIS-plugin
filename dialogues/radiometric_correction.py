import csv
import numpy as np



'''
This code is written by Marie Bøe Henriksen and can be found in https://github.com/NTNU-SmallSat-Lab/cal-char-corr
'''

def radiometric_correction(bip_path, exp):

    # Metadata
    x_start = 428 # aoi_x
    x_stop = 1508 # aoi_x + column_count 
    y_start = 266 # aoi_y
    y_stop = 950 # aoi_y + row_count
    bin_x = 9 # bin_factor

    image_height = 684 # row_count
    image_width = 120 # column_count/bin_factor

    metadata = [exp, image_height, image_width, x_start, x_stop, y_start, y_stop, bin_x]

    cube = read_bip_cube(bip_path, image_width, image_height)
    cube = cube[:,:,::-1] # Flip HYPSO-1 cube

    # Calibration files
    coeff_path = '/Users/edmondbaloku/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/hypso_1/data/coefficients/'

    spectral_coeffs = readCsvFile(coeff_path + 'spectral_coeffs_FM_order2.csv')
    rad_coeffs = readCsvFile(coeff_path + 'rad_coeffs_FM_binx9.csv')
    
    background_value = 8 * bin_x # [counts] TODO: How is this with binning?

    # Note: do not scale the cube before calibration
    cube_calibrated, w, metadata = calibrate_cube(cube, metadata, spectral_coeffs, rad_coeffs, background_value)
    [exp, image_height, image_width, x_start, x_stop, y_start, y_stop, bin_x] = metadata

    return cube_calibrated, w


def readCsvFile( filename ):
    data = []

    with open(filename) as csvDataFile:
        csvReader = csv.reader(csvDataFile)
        for row in csvReader:
            data.append(row)

    data_array = np.asarray(data)
    data_float = data_array.astype(float)

    return data_float

def read_bip_cube(filename, width=1936, height=1216):
    ''' Note: this function does not flip or scale the frames as must be done
    for HYPSO-1 data (flip and scale from 16-bit to 12-bit).'''
    
    cube = np.fromfile(filename, dtype=np.uint16) # 12-bit
    # cube = np.fromfile(filename, dtype=np.uint8) # 8-bit
    
    size_im_flat = width * height
    num_images = int(len(cube)/size_im_flat)
    
    cube.shape = (num_images, height, width)
    
    return cube

# To handle spectral calibration of different orders
def pixel_to_wavelength(x, spectral_coeffs):
    if len(spectral_coeffs) == 2:
        w = spectral_coeffs[1] + spectral_coeffs[0]*x
    elif len(spectral_coeffs) == 3:
        w = spectral_coeffs[2] + spectral_coeffs[1]*x + spectral_coeffs[0]*x*x
    elif len(spectral_coeffs) == 4:
        w = spectral_coeffs[3] + spectral_coeffs[2]*x + spectral_coeffs[1]*x*x + spectral_coeffs[0]*x*x*x
    elif len(spectral_coeffs) == 5:
        w = spectral_coeffs[4] + spectral_coeffs[3]*x + spectral_coeffs[2]*x*x + spectral_coeffs[1]*x*x*x + spectral_coeffs[0]*x*x*x*x
    else: 
        print('Please update spectrally_calibrate function to include this polynomial.')
        print('Returning 0.')
        w = 0

    return w


def apply_spectral_calibration(x_start, x_stop, image_width, spectral_coeffs):  
    x = np.linspace(x_start,x_stop,image_width) 
    w = pixel_to_wavelength(x, spectral_coeffs)

    return w

def apply_radiometric_calibration(frame, exp, background_value, radiometric_calibration_coefficients):
    ''' Assumes input is 12-bit values, and that the radiometric calibration
    coefficients are the same size as the input image.
    
    Note: radiometric calibration coefficients have original size (684,1080),
    matching the "normal" AOI of the HYPSO-1 data (with no binning).'''
    
    frame = frame - background_value
    frame_calibrated = frame * radiometric_calibration_coefficients / exp
    
    return frame_calibrated

def calibrate_cube(cube, metadata, spectral_coeffs, rad_coeffs, background_value):
    
    [exp, image_height, image_width, x_start, x_stop, y_start, y_stop, bin_x] = metadata
    
    w = apply_spectral_calibration(x_start, x_stop, image_width, spectral_coeffs)
    
    num_frames = cube.shape[0]
    cube_calibrated = np.zeros([num_frames, image_height, image_width])

    for i in range(num_frames):
        frame = cube[i,:,:]
        frame_calibrated = apply_radiometric_calibration(frame, exp, background_value, rad_coeffs)
        cube_calibrated[i,:,:] = frame_calibrated
    
    return cube_calibrated, w, metadata

