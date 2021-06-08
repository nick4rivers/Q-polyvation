from PyQt5.QtGui import *
import processing

# Specify the maximum elevation in meters
max_elevation = 1

# Make a string for naming files
elevation_name = str(max_elevation).replace('.', '')

# file dialog to select DEM data
message_text = 'Select a detrended DEM'
iface.messageBar().pushMessage(message_text, duration=10)
raw_dem_path = QFileDialog.getOpenFileName()[0]

# load the raster and add to the map
# only add to the map if not already there
try:
    QgsProject.instance().removeMapLayer(raw_dem)
except:
    print('No layer to remove')

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

# create directories for intermediates and outputs
outputs_path = os.path.join(work_path, 'outputs')
intermediates_path = os.path.join(work_path, 'intermediates')

if not os.path.exists(outputs_path):
    os.mkdir(outputs_path)

if not os.path.exists(intermediates_path):
    os.mkdir(intermediates_path)

# --------- PROCESSING -------------

# -- DEM --

# set the file path
less_dem_name = 'less_' + elevation_name + 'm.tif' 
less_dem_path = os.path.join(intermediates_path, less_dem_name)
expression = '(\"raw_dem@1\" <=' + str(max_elevation)+ ')'

processing.run("qgis:rastercalculator",
    {'EXPRESSION':expression + ' / ' + expression,
    'LAYERS':[raw_dem_path],
    'CELLSIZE':0,
    'EXTENT':None,
    'CRS':None,
    'OUTPUT':less_dem_path})

# -- DEM to VECTOR --
raw_vector_name = 'raw_' + elevation_name + 'm.gpkg'
raw_vector_path = os.path.join(intermediates_path, raw_vector_name)

processing.run("gdal:polygonize",
    {'INPUT':less_dem_path,
    'BAND':1,
    'FIELD':'DN',
    'EIGHT_CONNECTEDNESS':False,
    'EXTRA':'',
    'OUTPUT':raw_vector_path})

# -- CALCULATE AREA --

# open the raw vector
raw_vector_layer = QgsVectorLayer(raw_vector_path, '', 'ogr')

# create a provider
pv = raw_vector_layer.dataProvider()

# add the attribute and update
pv.addAttributes([QgsField('raw_area_m', QVariant.Int)])
raw_vector_layer.updateFields()

# Create a context and scope
# Understand WTF this is??
context = QgsExpressionContext()
context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(raw_vector_layer))

# Loop through and add the areas
with edit(raw_vector_layer):
# loop them
    for feature in raw_vector_layer.getFeatures():
        context.setFeature(feature)
        feature['raw_area_m'] = QgsExpression('$area').evaluate(context)
        raw_vector_layer.updateFeature(feature)

# -- Simplify Polygons --
simp_vector_name = 'simp_' + elevation_name + 'm.gpkg'
simp_vector_path = os.path.join(intermediates_path, simp_vector_name)

processing.run("native:simplifygeometries", 
    {'INPUT':raw_vector_layer,
        'METHOD':0,
        'TOLERANCE':0.000008,
        'OUTPUT':simp_vector_path})

simp_vector_layer = QgsVectorLayer(simp_vector_path, '', 'ogr')


# -- Smooth the polygons --
smooth_vector_name = 'smooth_' + elevation_name + 'm.gpkg'
smooth_vector_path = os.path.join(intermediates_path, smooth_vector_name)
        
processing.run("native:smoothgeometry",
    {'INPUT':simp_vector_layer,
    'ITERATIONS':1,
    'OFFSET':0.25,
    'MAX_ANGLE':180,
    'OUTPUT':smooth_vector_path})

smooth_vector_layer = QgsVectorLayer(smooth_vector_path, '', 'ogr')

# Create a context and scope
# Understand WTF this is??
context = QgsExpressionContext()
context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(smooth_vector_layer))

# add an area attribute
# create a provider
pv = smooth_vector_layer.dataProvider()

# add the attribute and update
pv.addAttributes([QgsField('area_m', QVariant.Int)])
smooth_vector_layer.updateFields()

# Loop through and add the areas
with edit(smooth_vector_layer):
# loop them
    for feature in smooth_vector_layer.getFeatures():
        context.setFeature(feature)
        feature['area_m'] = QgsExpression('$area').evaluate(context)
        smooth_vector_layer.updateFeature(feature)


# -- Do a quick geometry fix for twisted polygons --
fixed_vector_name = 'fixed_' + elevation_name + 'm.gpkg'
fixed_vector_path = os.path.join(intermediates_path, fixed_vector_name)
processing.run("native:fixgeometries",
    {'INPUT':smooth_vector_path,
    'OUTPUT':fixed_vector_path})

# Open the fixed vector
fixed_vector_layer = QgsVectorLayer(fixed_vector_path, '', 'ogr')


# -- Copy the vector to outputs directory
output_vector_name = 'final_' + elevation_name + 'm.gpkg'
output_vector_path = os.path.join(outputs_path, output_vector_name)
QgsVectorFileWriter.writeAsVectorFormat(fixed_vector_layer, output_vector_path, 'utf-8,', driverName = 'GPKG')

# open the output layer
output_vector_layer = QgsVectorLayer(output_vector_path, '', 'ogr')


# -- Delete Unneeded Fields --
pv = output_vector_layer.dataProvider()
pv.deleteAttributes([1, 2])
output_vector_layer.updateFields()


# -- Delete small polygons --
# data provider capabilities
caps = output_vector_layer.dataProvider().capabilities()

# features and empty list of features to delete
features = output_vector_layer.getFeatures()
delete_features = []

# if the layer can have deleted features
if caps & QgsVectorDataProvider.DeleteFeatures:
    for feature in features:
        if feature['area_m'] <= 9:
            delete_features.append(feature.id())
    result = output_vector_layer.dataProvider().deleteFeatures(delete_features)
    output_vector_layer.triggerRepaint()



# -- Add final vector to the interface --
iface.addVectorLayer(output_vector_path, '', 'ogr')

# TODO - styles
