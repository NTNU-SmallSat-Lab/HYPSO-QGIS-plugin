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
1. Open QGIS.
2. Go to Plugins -> Manage and Install Plugins.
3. Search for "Hypso-1 Data Analysis". If there are none, jump to step 6.
4. Install the plugin.
5. Restart QGIS.
6. If you could not find the plugin in the list, clone this repository to your computer.
7. Open the default installation folder [Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins].
If you installed QGIS in a different location, open the corresponding folder.
8. Copy the folder from the cloned repository to the "python/plugins" folder.
9. Restart QGIS.


## License ##
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details 