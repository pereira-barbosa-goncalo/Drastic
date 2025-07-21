"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
import csv
import shutil
from typing import Any, Optional

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterExtent,
    QgsRasterLayer,
    QgsProviderRegistry,
    QgsApplication,
    QgsVectorLayer,
    QgsField,
    QgsProject,
    QgsProcessingParameterNumber,
    QgsProcessingParameterField,
    
)
from qgis import processing
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from PyQt5.QtCore import QVariant
from osgeo import gdal

class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "myscriptDRASTIC"

    def displayName(self) -> str:
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "DRASTIC"

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return "Groundwater"

    def groupId(self) -> str:
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "aguassubterraneas"

    def shortHelpString(self) -> str:

        return """This tool evaluates the pollution risk of a specific area by calculating the DRASTIC index.
    The DRASTIC index considers seven environmental factors: Depth to water, net Recharge, Aquifer media,
    Soil media, Topography, Impact of the vadose zone, and hydraulic Conductivity of the aquifer.
    The result helps in assessing the vulnerability of groundwater to pollution.
    
     Instructions for CSV Preparation:
    1. Ensure that you have CSV files corresponding to the shapefiles you are using.
    2. Each CSV file should contain two columns: "IN_" and "OUT".
    3. The "IN_" column should contain the values from the shapefile attribute you want to reclassify.
    4. The "OUT" column should contain the new values you want to assign to the corresponding "IN_" values.
    5. Save the CSV files with a clear name indicating their purpose (e.g., reclass_geology.csv, reclass_soil.csv).
    6. When running the tool, select the appropriate CSV file for each shapefile layer.

    Example CSV content:
    IN_,OUT
    Value1,NewValue1
    Value2,NewValue2
    Value3,NewValue3
    
    
    
        Made in Quintiães"""

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        
        #poços
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'caminho_points',
                "water wells points",
                [QgsProcessing.SourceType.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                name='coluna_points',
                description='Column with numerical values of the wells',
                parentLayerParameterName='caminho_points',
                type=QgsProcessingParameterField.Numeric  # restringe a campos numéricos
            )
        )

        
        #geologia
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'caminho_geologia',
                "Geology",
                [QgsProcessing.SourceType.TypeVectorAnyGeometry],
            )
        )
        
        #solo
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'caminho_soil',
                "Soil",
                [QgsProcessing.SourceType.TypeVectorAnyGeometry],
            )
        )

        #precipitaçao
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'caminho_prec',
                "average annual rainfall",
            )
        )

        # #Topografia
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'caminho_topo',
                "Topografy",
            )
        )
        
        #CSV de reclassificação
        self.addParameter(
            QgsProcessingParameterFile(
                name='caminho_recla_csv',
                description='CSV file for reclassifying the letter A',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='CSV files (*.csv)'
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                name='coluna_recla',
                description='Column to be used to reclassify the letter A',
                parentLayerParameterName='caminho_geologia',
                type=QgsProcessingParameterField.Any
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                name='caminho_recls_csv',
                description='CSV file for reclassifying the letter S',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='CSV files (*.csv)'
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                name='coluna_recls',
                description='Column to be used to reclassify the letter S',
                parentLayerParameterName='caminho_soil',
                type=QgsProcessingParameterField.Any
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                name='caminho_recli_csv',
                description='CSV file for reclassifying the letter I',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='CSV files (*.csv)'
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                name='coluna_recli',
                description='Column to be used to reclassify the letter I',
                parentLayerParameterName='caminho_soil',
                type=QgsProcessingParameterField.Any
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                name='extensao',
                description='Spatial extent of processing',
                defaultValue=None  # ou define uma extensão inicial
            )
        )

#--------Outputs

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                name='pasta',
                description='Output folder for processing results (do not put "/" or similar at the end of the path)'
            )
        )
        self.addParameter(
                    QgsProcessingParameterRasterDestination(
                        'drastic',
                        'DRASTIC'
                    )
                )



    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        """
        Here is where the processing itself takes place.
        """

        # # Retrieve the feature source and sink. The 'dest_id' variable is used
        # # to uniquely identify the feature sink, and must be included in the
        # # dictionary returned by the processAlgorithm function.
        # source = self.parameterAsSource(parameters, self.INPUT, context)
        points = self.parameterAsVectorLayer(parameters, 'caminho_points', context)
        caminho_points=points.source()
        coluna_points = self.parameterAsString(parameters, 'coluna_points', context)
        index = points.fields().indexOf(coluna_points)
        geologia = self.parameterAsVectorLayer(parameters, 'caminho_geologia', context)
        caminho_geologia=geologia.source()
        soil = self.parameterAsVectorLayer(parameters, 'caminho_soil', context)
        caminho_soil = soil.source()
        prec = self.parameterAsRasterLayer(parameters, 'caminho_prec', context)
        caminho_prec = prec.source()
        topo = self.parameterAsRasterLayer(parameters, 'caminho_topo', context)
        caminho_topo = topo.source()
        caminho_recls_csv = self.parameterAsFile(parameters, 'caminho_recls_csv', context)
        coluna_recla = self.parameterAsString(parameters, 'coluna_recla', context)
        coluna_recls = self.parameterAsString(parameters, 'coluna_recls', context)
        coluna_recli = self.parameterAsString(parameters, 'coluna_recli', context)
        caminho_recli_csv = self.parameterAsFile(parameters, 'caminho_recli_csv', context)
        caminho_recla_csv = self.parameterAsFile(parameters, 'caminho_recla_csv', context)
        extent = self.parameterAsExtent(parameters, 'extensao', context)
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        # Se precisares de usar como string:
        extensao = f"{xmin},{ymin},{xmax},{ymax} [EPSG:3763]"
        
        pixel = 25
        pasta = self.parameterAsString(parameters, 'pasta', context)
        if feedback.isCanceled():
            return {}

        feedback.pushInfo("Começou")
        #------------------------------------------------------D------------------------------------------------------
        #------------------interpolação------------------

        idw_raster=processing.run(
            "qgis:idwinterpolation",
            {
                'INTERPOLATION_DATA': f"{caminho_points}::~::0::~::{index}::~::0",
                'DISTANCE_COEFFICIENT': 2,
                'EXTENT': extensao,
                'PIXEL_SIZE': pixel,
                'OUTPUT': f'{pasta}/idw.tif'
            },
            is_child_algorithm = True,
            context=context,
            feedback=feedback
        )
        if feedback.isCanceled():
            return {}
        

        idw=QgsRasterLayer(idw_raster['OUTPUT'],"IDW")

        feedback.pushInfo("Acabou IDW")

        #------------------csv to shp.------------------

        expressaod = (
            '("idw@1" >= 0 AND "idw@1" < 1.524) * 10 + '
            '("idw@1" >= 1.524 AND "idw@1" < 4.572) * 9 + '
            '("idw@1" >= 4.572 AND "idw@1" < 9.144) * 7 + '
            '("idw@1" >= 9.144 AND "idw@1" < 15.24) * 5 + '
            '("idw@1" >= 15.24 AND "idw@1" < 22.86) * 3 + '
            '("idw@1" >= 22.86 AND "idw@1" < 30.48) * 2 + '
            '("idw@1" >= 30.48 AND "idw@1" < 99999) * 1 + '
            '("idw@1" < 0 OR "idw@1" >= 99999) * "idw@1"'
        )
        #Configurar as entradas para o raster calculator


        qrce = QgsRasterCalculatorEntry()
        qrce .bandNumber = 1
        qrce. raster = idw
        qrce.ref = 'idw@1'

        entradas = [qrce]


        #Criar o objeto QgsRasterCalculator
        reclassifyd = QgsRasterCalculator(expressaod, f"{pasta}/d.tif", "GTiff",idw.extent(), idw.width(), idw.height(), entradas)

        #Executar o cálculo
        reclassifyd.processCalculation()

        reclassifyd_layer=QgsRasterLayer(f"{pasta}/d.tif","d")

        feedback.setProgress(13)
        feedback.pushInfo("acabou D")

        #------------------------------------------------------R------------------------------------------------------

        #------------------Reclassificação------------------

        # Carregar a camada raster inicial
        #crs_res = QgsCoordinateReferenceSystem(“EPSG:3763”)
        prec = QgsRasterLayer(caminho_prec, "prec",)

        #QgsProject.instance().addMapLayer(prec)


        # Criar a expressão para o raster calculator Aqui, estamos reclassificando os valores entre valor_inicial e valor_final para valor_reclassificado
        expressaor = (
            '("prec@1" >= 0 AND "prec@1" < 50.8) * 1 + '
            '("prec@1" >= 50.8 AND "prec@1" < 101.6) * 3 + '
            '("prec@1" >= 101.6 AND "prec@1" < 177.8) * 6 + '
            '("prec@1" >= 177.8 AND "prec@1" < 254) * 8 + '
            '("prec@1" >= 254 AND "prec@1" < 99999) * 9 + '
            '("prec@1" < 0 OR "prec@1" >= 99999) * "prec@1"'
        )
        #Configurar as entradas para o raster calculator
        #entradas = [QgsRasterCalculatorEntry(prec, 1, 'prec@1')]

        qrce = QgsRasterCalculatorEntry()
        qrce .bandNumber = 1
        qrce. raster = prec
        qrce.ref = 'prec@1'

        entradas = [qrce]


        #Criar o objeto QgsRasterCalculator
        reclassifyr = QgsRasterCalculator(expressaor, f"{pasta}/r.tif", "GTiff", prec.extent(), prec.width(), prec.height(), entradas)

        #Executar o cálculo
        reclassifyr.processCalculation()

        feedback.setProgress(25)
        feedback.pushInfo("acabou R")

        #------------------------------------------------------A------------------------------------------------------

        #------------------gopakage to shp.------------------
        #geologia = QgsVectorLayer(f"{caminho_geologia}|layername={camada_geologia}", "geologia", "ogr")
        geologia = QgsVectorLayer(f"{caminho_geologia}", "geologia", "ogr")

        #------------------reclassificação------------------

        #------------------shp add values------------------

        #------------------call csv------------------
        try:
            # Open the CSV file
            with open(caminho_recla_csv, newline='', encoding='utf-8-sig') as csvfile:
                # Create a CSV reader object
                reader = csv.reader(csvfile)
                
            # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                for i, row in enumerate(reader):
                    if i < 5:  # Print only the first 5 rows
                        row_dict = dict(zip(headers, row[0].split(';')))
                        #print(row_dict)
                    else:
                        break

        except FileNotFoundError:
            feedback.pushInfo(f"Error: The file at {csv_path} was not found.")
        except Exception as e:
            feedback.pushInfo(f"An error occurred: {e}")

        in_out_map = {}#este dicionário é o csv transformado para visualizar faz print(in_out_map) antes de except
        try:
            # Open the CSV file again to create the mapping
            with open(caminho_recla_csv, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)

                # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                # Iterate over the rows and create the mapping
                for row in reader:
                    row_dict = dict(zip(headers, row[0].split(';')))
                    in_value = row_dict["IN_"]
                    out_value = row_dict["OUT"]
                    in_out_map[in_value] = out_value



        except Exception as e:
            print(f"An error occurred while creating the mapping: {e}")

        #------------------call .shp------------------

        # Check if the layer is valid
        if not geologia.isValid():
            feedback.pushInfo("Failed to load the layer!")
            # Print additional information about the error
            feedback.pushInfo("Error details:", geologia.error().summary())
            feedback.pushInfo("File readable:", os.access(caminho_geologia, os.R_OK))
        else:
            # Start editing the layer
            geologia.startEditing()

            # Add a new field to store the "OUT" values
            new_field = QgsField("OUT", QVariant.Double)
            geologia.dataProvider().addAttributes([new_field])
            geologia.updateFields()

            # Get the index of the new field
            out_field_index = geologia.fields().indexFromName("OUT")

            # Iterate over each feature in the layer
            for feature in geologia.getFeatures():
                classifica_value = feature[coluna_recla]
                # Check if the "CLASSIFICA" value exists in the mapping
                if classifica_value in in_out_map:
                    out_value = in_out_map[classifica_value]
                    # Update the new field with the "OUT" value
                    geologia.dataProvider().changeAttributeValues({feature.id(): {out_field_index: out_value}})
            geologia.commitChanges()


        #------------------shp to raster------------------

        reclassifya=processing.run("gdal:rasterize", {'INPUT':f'{caminho_geologia}','FIELD':'OUT','BURN':0,'USE_Z':False,'UNITS':1,'WIDTH':25,'HEIGHT':25,'EXTENT':extent,'NODATA':0,'OPTIONS':None,'DATA_TYPE':5,'INIT':None,'INVERT':False,'EXTRA':'','OUTPUT':f'{pasta}/a.tif'},is_child_algorithm = True,context=context,feedback=feedback)
        if feedback.isCanceled():
            return {}
        
        feedback.setProgress(38)
        feedback.pushInfo('acabou A')

        #------------------------------------------------------S------------------------------------------------------
        #------------------shp------------------
        soil = QgsVectorLayer(f"{caminho_soil}", "Soil", "ogr")

        #------------------shp add values------------------

        #------------------call csv------------------

        try:
            # Open the CSV file
            with open(caminho_recls_csv, newline='', encoding='utf-8-sig') as csvfile:
                # Create a CSV reader object
                reader = csv.reader(csvfile)
                
            # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                for i, row in enumerate(reader):
                    if i < 5:  # Print only the first 5 rows
                        row_dict = dict(zip(headers, row[0].split(';')))
                        #print(row_dict)
                    else:
                        break

        except FileNotFoundError:
            feedback.pushInfo(f"Error: The file at {csv_path} was not found.")
        except Exception as e:
            feedback.pushInfo(f"An error occurred: {e}")


        in_out_map = {} #este dicionário é o csv transformado para visualizar faz print(in_out_map) antes de except
        try:
            # Open the CSV file again to create the mapping
            with open(caminho_recls_csv, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)

                # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                # Iterate over the rows and create the mapping
                for row in reader:
                    row_dict = dict(zip(headers, row[0].split(';')))
                    in_value = row_dict["IN_"]
                    out_value = row_dict["OUT"]
                    in_out_map[in_value] = out_value
            
            
        except Exception as e:
            feedback.pushInfo(f"An error occurred while creating the mapping: {e}")
            
        #------------------call shp ------------------
        solo=soil
        # Check if the layer is valid
        if not solo.isValid():
            feedback.pushInfo("Failed to load the layer!")
            feedback.pushInfo("Error details:", solo.error().summary())
            feedback.pushInfo("File readable:", os.access(caminho_soil, os.R_OK))
        else:
            #print("Carregou layer")
            # Start editing the layer
            solo.startEditing()

            # Add a new field to store the "OUT" values
            new_field = QgsField("OUT", QVariant.Double)
            solo.dataProvider().addAttributes([new_field])
            solo.updateFields()

            # Get the index of the new field
            out_field_index = solo.fields().indexFromName("OUT")

            # Iterate over each feature in the layer
            for feature in solo.getFeatures():
                classifica_value = feature[coluna_recls]
                # Check if the "CLASSIFICA" value exists in the mapping
                if classifica_value in in_out_map:
                    out_value = in_out_map[classifica_value]
                    # Update the new field with the "OUT" value
                    solo.dataProvider().changeAttributeValues({feature.id(): {out_field_index: out_value}})



        #------------------shp to raster------------------


        reclassifys=processing.run("gdal:rasterize", {'INPUT':f'{caminho_soil}','FIELD':'OUT','BURN':0,'USE_Z':False,'UNITS':1,'WIDTH':25,'HEIGHT':25,'EXTENT':extent,'NODATA':0,'OPTIONS':None,'DATA_TYPE':5,'INIT':None,'INVERT':False,'EXTRA':'','OUTPUT':f'{pasta}/s.tif'},is_child_algorithm = True,context=context,feedback=feedback)
        if feedback.isCanceled():
            return {}
        
        feedback.setProgress(50)
        feedback.pushInfo('acabou S')

        #------------------------------------------------------T------------------------------------------------------

        declive=processing.run("native:slope",\
            {'INPUT':f'{caminho_topo}',\
                'Z_FACTOR':1,\
                'OUTPUT':f'{pasta}/slope.tif'
            },
            is_child_algorithm = True,
            context=context,
            feedback=feedback
        )
        if feedback.isCanceled():
            return {}
        
        slope=QgsRasterLayer(declive['OUTPUT'],"slope")


        # Criar a expressão para o raster calculator Aqui, estamos reclassificando os valores entre valor_inicial e valor_final para valor_reclassificado
        expressaot = (
            '("slope@1" >= 0 AND "slope@1" < 2) * 10 + '
            '("slope@1" >= 2 AND "slope@1" < 6) * 9 + '
            '("slope@1" >= 6 AND "slope@1" < 12) * 5 + '
            '("slope@1" >= 12 AND "slope@1" < 18) * 3 + '
            '("slope@1" >= 18 AND "slope@1" < 99999) * 1 + '
            '("slope@1" < 0 OR "slope@1" >= 99999) * "slope@1"'
        )
        #Configurar as entradas para o raster calculator
        #entradas = [QgsRasterCalculatorEntry(slope, 1, 'topo@1')]

        qrce = QgsRasterCalculatorEntry()
        qrce.bandNumber = 1
        qrce.raster = slope
        qrce.ref = 'slope@1'

        entradas = [qrce]


        #Criar o objeto QgsRasterCalculator
        reclassifyt = QgsRasterCalculator(expressaot, f"{pasta}/t.tif", "GTiff", slope.extent(), slope.width(), slope.height(), entradas)

        #Executar o cálculo
        reclassifyt.processCalculation()
        feedback.setProgress(63)
        feedback.pushInfo('acabou T')

        #------------------------------------------------------I------------------------------------------------------
        #------------------shp------------------
        soil = QgsVectorLayer(f"{caminho_soil}", "Soil", "ogr")

        #------------------shp add values------------------

        #------------------call csv------------------

        try:
            # Open the CSV file
            with open(caminho_recli_csv, newline='', encoding='utf-8-sig') as csvfile:
                # Create a CSV reader object
                reader = csv.reader(csvfile)
                
            # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                for i, row in enumerate(reader):
                    if i < 5:  # Print only the first 5 rows
                        row_dict = dict(zip(headers, row[0].split(';')))
                        #print(row_dict)
                    else:
                        break

        except FileNotFoundError:
            feedback.pushInfo(f"Error: The file at {csv_path} was not found.")
        except Exception as e:
            feedback.pushInfo(f"An error occurred: {e}")


        in_out_map = {} #este dicionário é o csv transformado para visualizar faz print(in_out_map) antes de except
        try:
            # Open the CSV file again to create the mapping
            with open(caminho_recli_csv, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)

                # Read the headers and split them
                headers = next(reader)
                headers = [header.strip() for header in headers[0].split(';')]

                # Iterate over the rows and create the mapping
                for row in reader:
                    row_dict = dict(zip(headers, row[0].split(';')))
                    in_value = row_dict["IN_"]
                    out_value = row_dict["OUT"]
                    in_out_map[in_value] = out_value

            
            
        except Exception as e:
            feedback.pushInfo(f"An error occurred while creating the mapping: {e}")


        #------------------call shp ------------------
        solo=soil
        # Check if the layer is valid
        if not solo.isValid():
            feedback.pushInfo("Failed to load the layer!")
            feedback.pushInfo("Error details:", solo.error().summary())
            feedback.pushInfo("File readable:", os.access(caminho_soil, os.R_OK))
        else:
            # Start editing the layer
            solo.startEditing()

            # Add a new field to store the "OUT" values
            new_field = QgsField("OUT", QVariant.Double)
            solo.dataProvider().addAttributes([new_field])
            solo.updateFields()

            # Get the index of the new field
            out_field_index = solo.fields().indexFromName("OUT")

            # Iterate over each feature in the layer
            for feature in solo.getFeatures():
                classifica_value = feature[coluna_recli]
                # Check if the "CLASSIFICA" value exists in the mapping
                if classifica_value in in_out_map:
                    out_value = in_out_map[classifica_value]
                    # Update the new field with the "OUT" value
                    solo.dataProvider().changeAttributeValues({feature.id(): {out_field_index: out_value}})
            solo.commitChanges()



        #------------------shp to raster------------------

        reclassifys=processing.run("gdal:rasterize", {'INPUT':f'{caminho_soil}','FIELD':'OUT','BURN':0,'USE_Z':False,'UNITS':1,'WIDTH':25,'HEIGHT':25,'EXTENT':extent,'NODATA':0,'OPTIONS':None,'DATA_TYPE':5,'INIT':None,'INVERT':False,'EXTRA':'','OUTPUT':f'{pasta}/i.tif'},is_child_algorithm = True,context=context,feedback=feedback)
        if feedback.isCanceled():
            return {}
        
        feedback.setProgress(75)
        feedback.pushInfo('acabou I')

        #------------------------------------------------------C------------------------------------------------------
        feedback.setProgress(88)
        feedback.pushInfo("acabou C")

        #------------------------------------------------------Soma------------------------------------------------------


        # ------------------ D ------------------

        d = QgsRasterLayer(f"{pasta}/d.tif", "d")

        if not d.isValid():

            raise Exception("Layer d.tif not valid")

        dqrce = QgsRasterCalculatorEntry()

        dqrce.bandNumber = 1

        dqrce.raster = d

        dqrce.ref = 'd@1'

         

        # ------------------ R ------------------

        r = QgsRasterLayer(f"{pasta}/r.tif", "r")

        if not r.isValid():

            raise Exception("Layer r.tif not valid")

        rqrce = QgsRasterCalculatorEntry()

        rqrce.bandNumber = 1

        rqrce.raster = r

        rqrce.ref = 'r@1'

         

        # ------------------ A ------------------

        a = QgsRasterLayer(f"{pasta}/a.tif", "a")

        if not a.isValid():

            raise Exception("Layer a.tif not valid")

        aqrce = QgsRasterCalculatorEntry()

        aqrce.bandNumber = 1

        aqrce.raster = a

        aqrce.ref = 'a@1'

         

        # ------------------ S ------------------

        s = QgsRasterLayer(f"{pasta}/s.tif", "s")

        if not s.isValid():

            raise Exception("Layer s.tif not valid")

        sqrce = QgsRasterCalculatorEntry()

        sqrce.bandNumber = 1

        sqrce.raster = s

        sqrce.ref = 's@1'

         

        # ------------------ T ------------------

        t = QgsRasterLayer(f"{pasta}/t.tif", "t")

        if not t.isValid():

            raise Exception("Layer t.tif not valid")

        tqrce = QgsRasterCalculatorEntry()

        tqrce.bandNumber = 1

        tqrce.raster = t

        tqrce.ref = 't@1'

         

        # ------------------ I ------------------

        i = QgsRasterLayer(f"{pasta}/i.tif", "i")

        if not i.isValid():

            raise Exception("Layer i.tif not valid")

        iqrce = QgsRasterCalculatorEntry()

        iqrce.bandNumber = 1

        iqrce.raster = i

        iqrce.ref = 'i@1'



        # ------------------ Calculator Setup ------------------

        entries = [dqrce, rqrce, aqrce, sqrce, tqrce, iqrce]

         

        expression = 'd@1*5 + r@1*4 + a@1*3 + s@1*2 + t@1*1 + i@1*5 + 1'

         

        calc = QgsRasterCalculator( expression, f"{pasta}/drastic.tif", 'GTiff', extent, d.width(), d.height(), entries)



        result = calc.processCalculation()

        if result != 0:

            raise Exception(f"Raster calculation failed with code: {result}")

        
        output_path = self.parameterAsOutputLayer(parameters, 'drastic', context)
        shutil.copyfile(f"{pasta}/drastic.tif", output_path)
        final_layer = QgsRasterLayer(output_path, "DRASTIC")
        QgsProject.instance().addMapLayer(final_layer)
        

        return{
            "pasta": pasta,
            "drastic":output_path}

    def createInstance(self):
        return self.__class__()
