### Hypso-1 QGIS plugin
QGIS plugin for analyzing multispectral images captured by Hypso-1 satellite

## NOTE ##
To make this work, you need to install the spectral library and opencv-python librari in QGIS.
* Open QGIS
* Open python consol
* Run the following commands
    ```
    import pip
    pip.main(['install', 'spectral'])
    pip.main(['install', 'opencv-python'])
    ``` 
* Restart QGIS

## Installation ##
1. Download the zip file from the releases page (if there are none yet, you can download the source code and build the zip file yourself)
2. Open QGIS
3. Go to Plugins -> Manage and Install Plugins
4. Click on the "Install from ZIP" button
5. Select the zip file you downloaded
6. Restart QGIS

## License ##
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details 