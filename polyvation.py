from PyQt5.QtGui import *
import processing

# Specify elevations you would like to process
elevations = [0.5, 1, 2]

# file dialog to select DEM data
message_text = 'Select a detrended DEM'
iface.messageBar().pushMessage(message_text, duration=10)
raw_dem_path = QFileDialog.getOpenFileName()[0]

# load the raster and add to the map
raw_dem = iface.addRasterLayer(raw_dem_path, 'raw_dem')

# give a success message if valid
if raw_dem.isValid():
    iface.messageBar().pushMessage("Successfully loaded elevation data", level=Qgis.Success, duration=10)
else:
    iface.messageBar().pushMessage("You totally blew it", level=Qgis.Warning, duration=10)
    exit()

# select and zoom to layer
iface.setActiveLayer(raw_dem)
iface.zoomToActiveLayer()

# Select a working directory
message_text = 'Select a working directory when prompted'
iface.messageBar().pushMessage(message_text, duration=10)
work_path = QFileDialog.getExistingDirectory()


# create directories for intermediates and final datasets
output_path = os.path.join(work_path, 'output')
intermediates_path = os.path.join(work_path, 'intermediates')

if not os.path.exists(products_path):
    os.mkdir(products_path)

if not os.path.exists(intermediates_path):
    os.mkdir(intermediates_path)

# --------- PROCESSING -------------

# build less than rasters

# To Do
less_than_path = os.path.join(intermediates_path, 'less_100.tif')

processing.run("qgis:rastercalculator",
    {'EXPRESSION':'(\"raw_dem@1\" <= 1) / (\"raw_dem@1\" <= 1)',
    'LAYERS':[raw_dem_path],
    'CELLSIZE':0,
    'EXTENT':None,
    'CRS':None,
    'OUTPUT':less_than_path})




