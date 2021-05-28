from PyQt5.QtGui import *


# Specify elevations you would like to process
elevations = [0.5, 1, 2]

# file dialog to select data
hand_path = QFileDialog.getOpenFileName()
print(hand_path)

# WTFs a tuple 
print(type(hand_path))

# load the raster and add to the map
hand = iface.addRasterLayer(hand_path[0])


