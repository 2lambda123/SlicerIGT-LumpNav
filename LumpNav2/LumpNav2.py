import os
import time
import json

import numpy as np
import vtk, qt, ctk, slicer

import logging
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

try:
  import matplotlib.pyplot as plt
except:
  slicer.util.pip_install('matplotlib')
  import matplotlib.pyplot as plt

try:
  from sklearn import datasets
except:
  slicer.util.pip_install('scikit-learn')
  from sklearn import datasets

try:
  from mlxtend.plotting import plot_decision_regions
except:
  slicer.util.pip_install('mlxtend')
  from mlxtend.plotting import plot_decision_regions

#
# LumpNav2
#

# Finding where guidelet.py and ultrasound.py are stored:
# C:\Users\(_NAME_)\AppData\Roaming\NA-MIC\Extensions-28257\SlicerIGT\lib\Slicer-4.10\qt-scripted-modules\Guidelet\GuideletLib\Guidelet.py
# C:\Users\(_NAME_)\AppData\Roaming\NA-MIC\Extensions-28257\SlicerIGT\lib\Slicer-4.10\qt-scripted-modules\Guidelet\GuideletLib\UltraSound.py


class LumpNav2(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "LumpNav2"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Perk Lab (Queen's University)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#LumpNav2">module documentation</a>.
"""
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # LumpNav21
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='LumpNav2',
    sampleName='LumpNav21',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'LumpNav21.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='LumpNav21.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='LumpNav21'
  )

  # LumpNav22
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='LumpNav2',
    sampleName='LumpNav22',
    thumbnailFileName=os.path.join(iconsPath, 'LumpNav22.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='LumpNav22.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='LumpNav22'
  )


# Event filter for LumpNav widget main window

class LumpNavEventFilter(qt.QWidget):
  """
  Install this event filter to overwrite default behavior of main window events like closing the window or saving the
  scene.
  """

  def __init__(self, moduleWidget):
    qt.QWidget.__init__(self)
    self.moduleWidget = moduleWidget

  def eventFilter(self, object, event):
    if self.moduleWidget.getSlicerInterfaceVisible():
      return False

    if event.type() == qt.QEvent.Close:
      if self.moduleWidget.confirmExit():
        slicer.app.quit()
        return True
      else:
        event.ignore()
        return True

    # elif (event.type() == qt.QEvent.KeyPress and event.key() == qt.Qt.Key_S and (event.modifiers() & qt.Qt.ControlModifier)):
    #   print("CTRL + S intercepted")
    #   return True

    return False


#
# LumpNav2Widget
#

class LumpNav2Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # Variables to store widget state

  PIVOT_CALIBRATION = 0
  SPIN_CALIBRATION = 1
  PIVOT_CALIBRATION_TIME_SEC = 5.0
  CAUTERY_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/CauteryCalibrationTresholdMm"
  CAUTERY_CALIBRATION_THRESHOLD_DEFAULT = 1.0
  NEEDLE_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/NeedleCalibrationTresholdMm"
  NEEDLE_CALIBRATION_THRESHOLD_DEFAULT = 1.0
  FONT_SIZE_DEFAULT = 20

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    slicer.mymodW = self  # then in python interactor, call "self = slicer.mymod" to use
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    self._updatingGUIFromMRML = False
    self._updatingGui = False
    self.observedNeedleModel = None
    self.observedCauteryModel = None
    self.observedTrackingSeqBrNode = None
    self.observedUltrasoundSeqBrNode = None

    # Timer for pivot calibration controls

    self.pivotCalibrationLogic = slicer.modules.pivotcalibration.logic()
    self.pivotCalibrationStopTime = 0
    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION  # Default value, but it is always set when starting pivot calibration
    self.pivotCalibrationResultNode = None

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/LumpNav2.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = LumpNav2Logic()
    self._updatingGUIFromParameterNode = True
    self.logic.setup()
    self._updatingGUIFromParameterNode = False

    # Install event filter for main window.
    self.eventFilter = LumpNavEventFilter(self)
    slicer.util.mainWindow().installEventFilter(self.eventFilter)

    # Check settings and set default values if settings not found
    cauteryCalibrationThresholdMm = slicer.util.settingsValue(self.CAUTERY_CALIBRATION_THRESHOLD_SETTING, str(self.CAUTERY_CALIBRATION_THRESHOLD_DEFAULT))
    needleCalibrationThresholdMm = slicer.util.settingsValue(self.NEEDLE_CALIBRATION_THRESHOLD_SETTING, str(self.NEEDLE_CALIBRATION_THRESHOLD_DEFAULT))

    # Set state of custom UI button
    self.setCustomStyle(not self.getSlicerInterfaceVisible())

    # Connections
    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # QT connections
    self.ui.customUiButton.connect('toggled(bool)', self.onCustomUiClicked)
    self.ui.startPlusButton.connect('toggled(bool)', self.onStartPlusClicked)
    self.ui.displayRASButton.connect('toggled(bool)', self.onDisplayRASClicked)
    self.ui.displayCauteryStateButton.connect('toggled(bool)', self.onDisplayCauteryStateClicked)
    self.ui.toolsCollapsibleButton.connect('contentsCollapsed(bool)', self.onToolsCollapsed)
    self.ui.contouringCollapsibleButton.connect('contentsCollapsed(bool)', self.onContouringCollapsed)
    self.ui.navigationCollapsibleButton.connect('contentsCollapsed(bool)', self.onNavigationCollapsed)
    self.ui.cauteryCalibrationButton.connect('clicked()', self.onCauteryCalibrationButton)
    needleVisibilitySetting = slicer.util.settingsValue(self.logic.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    self.ui.needleVisibilityButton.checked = needleVisibilitySetting
    self.ui.needleVisibilityButton.connect('toggled(bool)', self.onNeedleVisibilityToggled)
    self.ui.trackingSequenceBrowserButton.connect('toggled(bool)', self.onTrackingSequenceBrowser)
    cauteryVisible = slicer.util.settingsValue(self.logic.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    self.ui.cauteryVisibilityButton.checked = cauteryVisible
    self.ui.cauteryVisibilityButton.connect('toggled(bool)', self.onCauteryVisibilityToggled)
    warningSoundEnabled = slicer.util.settingsValue(self.logic.WARNING_SOUND_SETTING, True, converter=slicer.util.toBool)
    self.ui.warningSoundButton.checked = warningSoundEnabled
    self.ui.warningSoundButton.connect('toggled(bool)', self.onWarningSoundToggled)
    breachMarkupsProximityThreshold = slicer.util.settingsValue(self.logic.BREACH_MARKUPS_PROXIMITY_THRESHOLD, 1, converter=lambda x: int(x))
    self.ui.breachMarkupsThresholdSpinBox.value = breachMarkupsProximityThreshold
    self.ui.breachMarkupsThresholdSpinBox.connect('valueChanged(int)', self.onBreachMarkupsProximityChanged)
    self.ui.exitButton.connect('clicked()', self.onExitButtonClicked)
    self.ui.saveSceneButton.connect('clicked()', self.onSaveSceneClicked)

    # contouring
    brightnessSetting = slicer.util.settingsValue(self.logic.BRIGHTNESS_SETTING, "Normal")
    self.ui.normalBrightnessButton.connect('toggled(bool)', self.onNormalBrightnessClicked)
    self.ui.brightBrightnessButton.connect('toggled(bool)', self.onBrightBrightnessClicked)
    self.ui.brightestBrightnessButton.connect('toggled(bool)', self.onBrightestBrightnessClicked)
    if brightnessSetting == "Normal":
      self.ui.normalBrightnessButton.checked = True
    elif brightnessSetting == "Bright":
      self.ui.brightBrightnessButton.checked = True
    else:
      self.ui.brightestBrightnessButton.checked = True
    self.ui.markPointsButton.connect('toggled(bool)', self.onMarkPointsToggled)
    self.ui.deleteLastFiducialButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.ui.deleteAllFiducialsButton.connect('clicked()', self.onDeleteAllFiducialsClicked)
    self.ui.selectPointsToEraseButton.connect('toggled(bool)', self.onErasePointsToggled)
    self.ui.markPointCauteryTipButton.connect('clicked()', self.onMarkPointCauteryTipClicked)
    self.ui.startStopRecordingButton.connect('toggled(bool)', self.onStartStopRecordingClicked)
    self.ui.freezeUltrasoundButton.connect('toggled(bool)', self.onFreezeUltrasoundClicked)
    self.ui.segmentationVisibility.connect('toggled(bool)', self.onSegmentationVisibilityToggled)
    self.pivotSamplingTimer.connect('timeout()', self.onPivotSamplingTimeout)
    self.ui.segmentationThresholdSlider.connect("valueChanged(int)", self.onSegmentationThresholdChanged)

    # navigation
    self.ui.leftBreastButton.connect('clicked()', self.onLeftBreastButtonClicked)
    self.ui.rightBreastButton.connect('clicked()', self.onRightBreastButtonClicked)
    # self.ui.bottomBullseyeCameraButton.connect('clicked()', lambda: self.onCameraButtonClicked('View3') )
    self.ui.displayDistanceButton.connect('toggled(bool)', self.onDisplayDistanceClicked)
    self.ui.displayRulerButton.connect('toggled(bool)', self.onDisplayRulerButtonClicked)
    self.ui.leftAutoCenterCameraButton.connect('toggled(bool)', self.onLeftAutoCenterCameraButtonClicked)
    self.ui.rightAutoCenterCameraButton.connect('toggled(bool)', self.onRightAutoCenterCameraButtonClicked)
    self.ui.bottomAutoCenterCameraButton.connect('toggled(bool)', self.onBottomAutoCenterCameraButtonClicked)
    self.ui.increaseDistanceFontSizeButton.setAutoRepeat(True)
    self.ui.increaseDistanceFontSizeButton.setAutoRepeatDelay(500)
    self.ui.increaseDistanceFontSizeButton.setAutoRepeatInterval(10)
    self.ui.increaseDistanceFontSizeButton.connect('clicked()', self.onIncreaseDistanceFontSizeClicked)
    self.ui.decreaseDistanceFontSizeButton.setAutoRepeat(True)
    self.ui.decreaseDistanceFontSizeButton.setAutoRepeatDelay(500)
    self.ui.decreaseDistanceFontSizeButton.setAutoRepeatInterval(10)
    self.ui.decreaseDistanceFontSizeButton.connect('clicked()', self.onDecreaseDistanceFontSizeClicked)
    self.ui.deleteLastFiducialNavigationButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    cauteryToolSelected = slicer.util.settingsValue(self.logic.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    self.ui.toolModelButton.checked = cauteryToolSelected
    self.ui.toolModelButton.connect('toggled(bool)', self.onToolModelClicked)
    self.ui.threeDViewButton.connect('toggled(bool)', self.onThreeDViewButton)
    self.ui.breachLocationButton.connect('toggled(bool)', self.onBreachLocationButtonClicked)
    self.ui.deleteTumorBreachButton.connect('clicked()', self.onDeleteTumorBreachButtonClicked)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    # Add custom layouts
    self.logic.addCustomLayouts()

    import Viewpoint
    self.viewpointLogic = Viewpoint.ViewpointLogic()

  def onCauteryCalibrationButton(self):
    logging.info('onCauteryCalibrationButton')
    cauteryToNeedle = self._parameterNode.GetNodeReference(self.logic.CAUTERY_TO_NEEDLE)
    cauteryTipToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYTIP_TO_CAUTERY)
    self.startPivotCalibration(cauteryToNeedle, cauteryTipToCautery)

  def startPivotCalibration(self, toolToReferenceTransformNode, toolTipToToolTransformNode):
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION
    self.ui.cauteryCalibrationButton.setEnabled(False)
    self.pivotCalibrationResultNode = toolTipToToolTransformNode
    self.pivotCalibrationLogic.SetAndObserveTransformNode(toolToReferenceTransformNode)
    self.pivotCalibrationStopTime = time.time() + self.PIVOT_CALIBRATION_TIME_SEC
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()

  def onPivotSamplingTimeout(self):
    remainingTime = self.pivotCalibrationStopTime - time.time()
    self.ui.cauteryCalibrationLabel.setText("Calibrating for {0:.0f} more seconds".format(remainingTime))
    if time.time() < self.pivotCalibrationStopTime:
      self.pivotSamplingTimer.start()  # continue
    else:
      self.onStopPivotCalibration()  # calibration completed
  
  def onExitButtonClicked(self):
    mainwindow = slicer.util.mainWindow()
    mainwindow.close()

  def onSaveSceneClicked(self):  # common
    #
    # save the mrml scene to a temp directory, then zip it
    #
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    node = self.logic.getParameterNode()
    sceneSaveDirectory = node.GetParameter('SavedScenesDirectory')
    sceneSaveDirectory = sceneSaveDirectory + "/" + self.logic.moduleName + "-" + time.strftime("%Y%m%d-%H%M%S")
    logging.info("Saving scene to: {0}".format(sceneSaveDirectory))
    if not os.access(sceneSaveDirectory, os.F_OK):
      os.makedirs(sceneSaveDirectory)

    applicationLogic = slicer.app.applicationLogic()
    if applicationLogic.SaveSceneToSlicerDataBundleDirectory(sceneSaveDirectory, None):
      logging.info("Scene saved to: {0}".format(sceneSaveDirectory))
    else:
      logging.error("Scene saving failed")
    qt.QApplication.restoreOverrideCursor()
    slicer.util.showStatusMessage(f"Scene saved to {sceneSaveDirectory}!", 2000)

  def onStopPivotCalibration(self):
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.ui.cauteryCalibrationButton.setEnabled(True)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      calibrationSuccess = self.pivotCalibrationLogic.ComputePivotCalibration()
    else:
      calibrationSuccess = self.pivotCalibrationLogic.ComputeSpinCalibration()

    #todo: check if this is cautery or needle calibration and use different thresholds
    calibrationThresholdStr = slicer.util.settingsValue(
      self.CAUTERY_CALIBRATION_THRESHOLD_SETTING, self.CAUTERY_CALIBRATION_THRESHOLD_DEFAULT)
    calibrationThreshold = float(calibrationThresholdStr)

    if not calibrationSuccess:
      self.ui.cauteryCalibrationLabel.setText("Calibration failed: " + self.pivotCalibrationLogic.GetErrorText())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return

    # Warning if RMSE is too high, but still use calibration
    if self.pivotCalibrationLogic.GetPivotRMSE() >= calibrationThreshold:
      self.ui.cauteryCalibrationLabel.setText("Warning: RMSE = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))
    else:
      self.ui.cauteryCalibrationLabel.setText("Success, RMSE = {:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))

    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultNode.SetMatrixTransformToParent(tooltipToToolMatrix)

    # Save calibration result so this calibration will be loaded in the next session automatically

    pivotCalibrationResultName = self.pivotCalibrationResultNode.GetName()
    pivotCalibrationFileWithPath = self.resourcePath(pivotCalibrationResultName + ".h5")
    slicer.util.saveNode(self.pivotCalibrationResultNode, pivotCalibrationFileWithPath)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      logging.info("Pivot calibration completed. Tool: {0}. RMSE = {1:.2f} mm".format(
        self.pivotCalibrationResultNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    else:
      logging.info("Spin calibration completed.")

  def confirmExit(self):
    msgBox = qt.QMessageBox()
    msgBox.setStyleSheet(slicer.util.mainWindow().styleSheet)
    msgBox.setWindowTitle("Confirm exit")
    msgBox.setText("Some data may not have been saved yet. Do you want to exit and discard the current scene?")
    #TODO: Save scene
    if self._parameterNode.GetMTime() > self.logic.saveTime.GetMTime():
      self.onSaveSceneClicked()
    discardButton = msgBox.addButton("Exit", qt.QMessageBox.DestructiveRole)
    cancelButton = msgBox.addButton("Cancel", qt.QMessageBox.RejectRole)
    msgBox.setModal(True)
    msgBox.exec()

    if msgBox.clickedButton() == discardButton:
      return True
    else:
      return False

  def onNeedleVisibilityToggled(self, toggled):
    logging.info("onNeedleVisibilityToggled({})".format(toggled))
    self.logic.setNeedleVisibility(toggled)

  def onCauteryVisibilityToggled(self, toggled):
    logging.info("onCauteryVisibilityToggled({})".format(toggled))
    self.logic.setCauteryVisibility(toggled)

  def onWarningSoundToggled(self, toggled):
    logging.info("onWarningSoundToggled({})".format(toggled))
    self.logic.setWarningSound(toggled)

  def getCauteryVisibility(self):
    return slicer.util.settingsValue(self.logic.CAUTERY_VISIBILITY_SETTING, False, converter=slicer.util.toBool)

  def onToolsCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.contouringCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)

  def onContouringCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(6)

  def onNavigationCollapsed(self, collapsed):
    """
    Called when the navigation tab is collapsed or expanded
    """
    if collapsed:
      self.logic.setBreachWarningOn(False)
    else:
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.contouringCollapsibleButton.collapsed = True
      self.onThreeDViewButton(False)
      interactionNode = slicer.app.applicationLogic().GetInteractionNode()
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
      self.logic.setBreachWarningOn(True)
      self.updateGUIFromParameterNode()

  def onThreeDViewButton(self, toggled):
    self.ui.threeDViewButton.checked = toggled
    if toggled:
      self.ui.threeDViewButton.text = "Triple 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_DUAL3D)
    else:
      self.ui.threeDViewButton.text = "Dual 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_TRIPLE3D)

  def onStartStopRecordingClicked(self, toggled):
    if toggled:
      self.ui.startStopRecordingButton.text = "Stop Ultrasound Recording"
    else:
      self.ui.startStopRecordingButton.text = "Start Ultrasound Recording"
    self.ui.markPointsButton.checked = False
    self.logic.onUltrasoundSequenceBrowserClicked(toggled)

  def onBreachLocationButtonClicked(self, toggled):
    parameterNode = self._parameterNode
    breachMarkups_Needle = parameterNode.GetNodeReference(self.logic.BREACH_MARKUPS_NEEDLE)
    if toggled:
      breachMarkups_Needle.SetDisplayVisibility(1)
    else:
      breachMarkups_Needle.SetDisplayVisibility(0)

  def onDeleteTumorBreachButtonClicked(self):
    parameterNode = self._parameterNode
    breachMarkups_Needle = parameterNode.GetNodeReference(self.logic.BREACH_MARKUPS_NEEDLE)
    breachMarkups_Needle.RemoveAllMarkups()

  def onBreachMarkupsProximityChanged(self, value):
    logging.info(f"onBreachMarkupsProximityChanged({value})")
    settings = qt.QSettings()
    settings.setValue(self.logic.BREACH_MARKUPS_PROXIMITY_THRESHOLD, value)

  def onFreezeUltrasoundClicked(self, toggled):
    logging.info("onFreezeUltrasoundClicked")
    self.logic.setFreezeUltrasoundClicked(toggled)

  def onStartPlusClicked(self, toggled):
    plusRemoteNode = self._parameterNode.GetNodeReference(self.logic.PLUS_REMOTE_NODE)
    if plusRemoteNode:
      if toggled:
        plusRemoteNode.Start()
      else:
        plusRemoteNode.Stop()

  def onDisplayRASClicked(self, toggled):
    parameterNode = self._parameterNode
    RASMarkups = parameterNode.GetNodeReference(self.logic.RAS_MARKUPS)
    if toggled:
      RASMarkups.SetDisplayVisibility(1)
    else:
      RASMarkups.SetDisplayVisibility(0)

  def onDisplayCauteryStateClicked(self, toggled):
    logging.info("onDisplayCauteryStateClicked({})".format(toggled))
    self.logic.setDisplayCauteryStateClicked(toggled)

  def onCustomUiClicked(self, checked):
    self.setCustomStyle(checked)

  def onTrackingSequenceBrowser(self, toggled):
    logging.info("onTrackingSequenceBrowserToggled({})".format(toggled))
    self.logic.setTrackingSequenceBrowser(toggled)

  def onUltrasoundSequenceBrowser(self, toggled):
    logging.info("onUltrasoundSequenceBrowserToggled({})".format(toggled))
    self.logic.onUltrasoundSequenceBrowserClicked(toggled)

  def onNormalBrightnessClicked(self):
    logging.info("onNormalBrightnessClicked")
    settings = qt.QSettings()
    settings.setValue(self.logic.BRIGHTNESS_SETTING, "Normal")
    self.logic.setBrightness(300)

  def onBrightBrightnessClicked(self):
    logging.info("onBrightBrightnessClicked")
    settings = qt.QSettings()
    settings.setValue(self.logic.BRIGHTNESS_SETTING, "Bright")
    self.logic.setBrightness(220)

  def onBrightestBrightnessClicked(self):
    logging.info("onBrightestBrightnessClicked")
    settings = qt.QSettings()
    settings.setValue(self.logic.BRIGHTNESS_SETTING, "Brightest")
    self.logic.setBrightness(140)

  def onErasePointsToggled(self, toggled):
    logging.info("onErasePointsToggled")
    if self._updatingGui:
      return
    self._updatingGui = True
    self.ui.markPointsButton.setChecked(False)
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ADDING)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_ERASING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    self._updatingGui = False

  def onMarkPointsToggled(self, toggled):
    if self._updatingGui:
      return
    self._updatingGui = True
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      self.ui.selectPointsToEraseButton.setChecked(False)
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ADDING)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_ADDING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    self._updatingGui = False
  
  def onMarkPointCauteryTipClicked(self):
    logging.info("Mark point at cautery tip clicked")
    self.logic.setMarkPointCauteryTipClicked()
  
  def onDeleteLastFiducialClicked(self):
    logging.info('onDeleteLastFiducialClicked')
    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
    self.logic.setDeleteLastFiducialClicked(numberOfPoints)

  def onDeleteAllFiducialsClicked(self):
    logging.info('onDeleteAllFiducialsClicked')
    self.logic.setDeleteAllFiducialsClicked()
    self.updateGUIFromParameterNode()

  def onSegmentationVisibilityToggled(self, toggled):
    logging.info("onSegmentationVisibilityToggled")
    if toggled:
      self.ui.segmentationVisibility.text = "Hide AI Segmentation"
    else:
      self.ui.segmentationVisibility.text = "Show AI Segmentation"
    self.logic.setSegmentationVisibility(toggled)

  def onSegmentationThresholdChanged(self, value):
    pct = value / (255 + 50) * -100 + 100
    self.ui.thresholdSliderValue.text = str(round(pct)) + "%"
    reconstructionVolume = self._parameterNode.GetNodeReference(self.logic.RECONSTRUCTION_VOLUME)
    if reconstructionVolume:
      self.logic.setVolumeRenderingProperty(reconstructionVolume, 50, value - 50 / 2)

  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    logging.debug("getViewNode")
    viewNode = self._parameterNode.GetNodeReference(viewName)
    return viewNode

  def onLeftBreastButtonClicked(self):
    logging.info("onLeftButtonClicked")
    self.ui.rightBreastButton.setEnabled(True)
    self.ui.rightBreastButton.setChecked(False)
    self.ui.leftBreastButton.setEnabled(False)
    # check if autocenter buttons are already clicked before activating autocenter
    if not self.ui.leftAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View1')
    if not self.ui.rightAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View2')
    if not self.ui.bottomAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View3')
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    #TODO: Don't use magic numbers
    cameraNode1.SetPosition(-242.0042709749552, 331.2026122150233, -36.6617924419265)
    cameraNode1.SetViewUp(0.802637869051714, 0.5959392355990031, -0.025077452777348814)
    cameraNode1.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode2.ResetClippingRange()
    cameraNode1.ResetClippingRange()

  def onRightBreastButtonClicked(self):
    logging.info("onRightButtonClicked")
    self.ui.rightBreastButton.setEnabled(False)
    self.ui.leftBreastButton.setEnabled(True)
    self.ui.leftBreastButton.setChecked(False)
    if not self.ui.leftAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View1')
    if not self.ui.rightAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View2')
    if not self.ui.bottomAutoCenterCameraButton.isChecked():
      self.onAutoCenterButtonClicked('View3')
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    # TODO: magic numbers
    cameraNode1.SetPosition(275.4944476449362, 309.31555951664205, 42.169967768629164)
    cameraNode1.SetViewUp(-0.749449157051234, 0.661802245162601, -0.018540477149624528)
    cameraNode1.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(-1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode2.ResetClippingRange()
    cameraNode1.ResetClippingRange()

  def onDisplayDistanceClicked(self, toggled):
    logging.info("onDisplayDistanceClicked({})".format(toggled))
    self.logic.showDistance = toggled
    if toggled:
      for i in range(slicer.app.layoutManager().threeDViewCount):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        parameterNode = self._parameterNode
        breachWarningNode = parameterNode.GetNodeReference(self.logic.BREACH_WARNING)
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft,
                                        f"{breachWarningNode.GetClosestDistanceToModelFromToolTip():.2f}")
        view.cornerAnnotation().SetMaximumFontSize(self.FONT_SIZE_DEFAULT)
        view.cornerAnnotation().SetMinimumFontSize(self.FONT_SIZE_DEFAULT)
        view.cornerAnnotation().SetNonlinearFontScaleFactor(1)
        view.forceRender()
    else:
        for i in range(slicer.app.layoutManager().threeDViewCount):  # Clear distance text
          view = slicer.app.layoutManager().threeDWidget(i).threeDView()
          view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft, "")
          view.forceRender()
        return

  def onDisplayRulerButtonClicked(self, toggled):
    logging.info(f"onDisplayRulerButtonClicked({toggled})")
    self.logic.setRulerVisibility(toggled)

  def onIncreaseDistanceFontSizeClicked(self):
    logging.info("onIncreaseDistanceFontSizeClicked")
    for i in range(slicer.app.layoutManager().threeDViewCount):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      fontSize = view.cornerAnnotation().GetMaximumFontSize() + 1
      view.cornerAnnotation().SetMaximumFontSize(fontSize)
      view.cornerAnnotation().SetMinimumFontSize(fontSize)
      view.cornerAnnotation().SetNonlinearFontScaleFactor(1)
      view.forceRender()

  def onDecreaseDistanceFontSizeClicked(self):
    logging.info("onDecreaseDistanceFontSizeClicked")
    for i in range(slicer.app.layoutManager().threeDViewCount):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      fontSize = view.cornerAnnotation().GetMaximumFontSize() - 1
      view.cornerAnnotation().SetMaximumFontSize(fontSize)
      view.cornerAnnotation().SetMinimumFontSize(fontSize)
      view.cornerAnnotation().SetNonlinearFontScaleFactor(1)
      view.forceRender()
  
  def onToolModelClicked(self, toggled):
    logging.info('onToolModelClicked')
    if toggled:
      self.ui.toolModelButton.text = "Stick Model"
    else:
      self.ui.toolModelButton.text = "Cautery Model"
    self.logic.setToolModelClicked(toggled)

  def enableBullseyeInViewNode(self, viewNode):
    logging.debug("enableBullseyeInViewNode")
    if self._parameterNode is None:
      return
    self.disableViewpointInViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    cauteryCameraToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYCAMERA_TO_CAUTERY)
    self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetTransformNode(cauteryCameraToCautery)
    self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStart()
    self.updateGUISliders(viewNode)

  def disableBullseyeInViewNode(self, viewNode):
    logging.debug("disableBullseyeInViewNode")
    if self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye():
      self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStop()
      self.updateGUISliders(viewNode)

  def disableBullseyeInAllViewNodes(self):
    logging.debug("disableBullseyeInAllViewNodes")
    leftViewNode = self.getViewNode('View1')
    self.disableBullseyeInViewNode(leftViewNode)
    rightViewNode = self.getViewNode('View2')
    self.disableBullseyeInViewNode(rightViewNode)
    bottomViewNode = self.getViewNode('View3')
    self.disableBullseyeInViewNode(bottomViewNode)

  def onLeftAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onLeftAutoCenterButtonClicked")
    self.onAutoCenterButtonClicked('View1')

  def onRightAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onRightAutoCenterCameraButtomClicked")
    self.onAutoCenterButtonClicked('View2')

  def onBottomAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onBottomAutoCenterCameraButtonClicked")
    self.onAutoCenterButtonClicked('View3')

  def onAutoCenterButtonClicked(self, viewName):
    logging.debug("onAutoCenterButtonClicked")
    viewNode = self.getViewNode(viewName)
    if self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
      self.disableAutoCenterInViewNode(viewNode)
    else:
      self.enableAutoCenterInViewNode(viewNode)
      logging.info("Auto center for %s enabled", viewName)
    self.updateGUIButtons()

  def disableAutoCenterInViewNode(self, viewNode):
    logging.debug("disableAutoCenterInViewNode")
    if self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
      self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStop()
      logging.info("Auto center for %s disabled", viewNode.GetName())

  def enableAutoCenterInViewNode(self, viewNode):
    logging.debug("enableAutoCenterInViewNode")
    self.disableViewpointInViewNode(viewNode)
    heightViewCoordLimits = 0.6
    widthViewCoordLimits = 0.9
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMinimum(-widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMaximum(widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMinimum(-heightViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMaximum(heightViewCoordLimits)
    parameterNode = self._parameterNode
    tumorModel = parameterNode.GetNodeReference(self.logic.TUMOR_MODEL)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetModelNode(tumorModel)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStart()

  def disableViewpointInViewNode(self,viewNode):
    logging.debug("disableViewpointInViewNode")
    self.disableBullseyeInViewNode(viewNode)
    self.disableAutoCenterInViewNode(viewNode)

  def updateGUIButtons(self):
    logging.debug("updateGUIButtons")

    leftViewNode = self.getViewNode('View1')

    blockSignalState = self.ui.leftAutoCenterCameraButton.blockSignals(True)
    if self.viewpointLogic.getViewpointForViewNode(leftViewNode).isCurrentModeAutoCenter():
      self.ui.leftAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.leftAutoCenterCameraButton.setChecked(False)
    self.ui.leftAutoCenterCameraButton.blockSignals(blockSignalState)

    rightViewNode = self.getViewNode('View2')

    blockSignalState = self.ui.rightAutoCenterCameraButton.blockSignals(True)
    if self.viewpointLogic.getViewpointForViewNode(rightViewNode).isCurrentModeAutoCenter():
      self.ui.rightAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.rightAutoCenterCameraButton.setChecked(False)
    self.ui.rightAutoCenterCameraButton.blockSignals(blockSignalState)

    centerViewNode = self.getViewNode('View3')

    blockSignalState = self.ui.bottomAutoCenterCameraButton.blockSignals(True)
    if self.viewpointLogic.getViewpointForViewNode(centerViewNode).isCurrentModeAutoCenter():
      self.ui.bottomAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.bottomAutoCenterCameraButton.setChecked(False)
    self.ui.bottomAutoCenterCameraButton.blockSignals(blockSignalState)

  def setCustomStyle(self, visible):
    """
    Applies UI customization. Hide Slicer widgets and apply custom stylesheet.
    :param visible: True to apply custom style.
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue('LumpNav2/SlicerInterfaceVisible', not visible)

    slicer.util.setToolbarsVisible(not visible)
    slicer.util.setMenuBarsVisible(not visible)
    slicer.util.setApplicationLogoVisible(not visible)
    slicer.util.setModuleHelpSectionVisible(not visible)
    slicer.util.setModulePanelTitleVisible(not visible)
    slicer.util.setDataProbeVisible(not visible)
    slicer.util.setStatusBarVisible(not visible)

    if visible:
      styleFile = self.resourcePath("LumpNav.qss")
      f = qt.QFile(styleFile)
      f.open(qt.QFile.ReadOnly | qt.QFile.Text)
      ts = qt.QTextStream(f)
      stylesheet = ts.readAll()
      slicer.util.mainWindow().setStyleSheet(stylesheet)
    else:
      slicer.util.mainWindow().setStyleSheet("")

    self.ui.customUiButton.checked = visible

  def getSlicerInterfaceVisible(self):
    return slicer.util.settingsValue('LumpNav2/SlicerInterfaceVisible', False, converter=slicer.util.toBool)

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """

    plusServerNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_NODE)
    if plusServerNode:
      plusServerNode.StopServer()

    slicer.util.mainWindow().removeEventFilter(self.eventFilter)

    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

    slicer.util.setDataProbeVisible(False)
    slicer.util.setApplicationLogoVisible(False)
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)

    # Choose layout based on which collapsible button is open

    if self.ui.toolsCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)

    if self.ui.contouringCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(6)

    if self.ui.navigationCollapsibleButton.checked:
      self.onThreeDViewButton(self.ui.threeDViewButton.checked)

    self.updateGUIFromParameterNode()
    self.updateGUIFromMRML()
  
  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    logging.debug("getCamera")
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(self._parameterNode.GetNodeReference(viewName))
    return camera
  
  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    # self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self.removeObservers(method=self.updateGUIFromParameterNode)
    self.removeObservers(method=self.updateGUIFromMRML)

    # self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    self.observedCauteryModel = None

    # self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    self.observedNeedleModel = None

    slicer.util.setDataProbeVisible(True)
    slicer.util.setApplicationLogoVisible(True)
    slicer.util.setModuleHelpSectionVisible(True)
    slicer.util.setModulePanelTitleVisible(True)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    logging.info("onSceneEndClose")

    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Read parameter nodes and update GUI accordingly

    # If new MRML nodes are referenced, update observers

    currentNeedleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if self.observedNeedleModel and currentNeedleModel != self.observedNeedleModel:
      self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedNeedleModel = currentNeedleModel
      if self.observedNeedleModel:
        self.addObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    
    currentCauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    if self.observedCauteryModel and currentCauteryModel != self.observedCauteryModel:
      self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedCauteryModel = currentCauteryModel
      if self.observedCauteryModel:
        self.addObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)

    currentTrackingSeqBrNode = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if self.observedTrackingSeqBrNode and currentTrackingSeqBrNode != self.observedTrackingSeqBrNode:
      self.removeObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedTrackingSeqBrNode = currentTrackingSeqBrNode
      if self.observedTrackingSeqBrNode is not None:
        self.addObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    currentUltrasoundSeqBrNode = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if self.observedUltrasoundSeqBrNode and currentUltrasoundSeqBrNode != self.observedUltrasoundSeqBrNode:
      self.removeObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedUltrasoundSeqBrNode = currentUltrasoundSeqBrNode
      if self.observedUltrasoundSeqBrNode is not None:
        self.addObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
    if numberOfPoints >= 1:
      self.ui.deleteLastFiducialButton.setEnabled(True)
      self.ui.deleteAllFiducialsButton.setEnabled(True)
      self.ui.deleteLastFiducialNavigationButton.setEnabled(True)
      self.ui.selectPointsToEraseButton.setEnabled(True)

    if numberOfPoints < 1:
      self.ui.deleteLastFiducialButton.setEnabled(False)
      self.ui.deleteAllFiducialsButton.setEnabled(False)
      self.ui.deleteLastFiducialNavigationButton.setEnabled(False)
      self.ui.selectPointsToEraseButton.setChecked(False)
      self.ui.selectPointsToEraseButton.setEnabled(False)

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateGUIFromMRML(self, caller=None, event=None):
    """
    Updates the GUI from MRML nodes in the scene (except parameter node).
    """
    if self._updatingGUIFromMRML:
      return

    if self._parameterNode is None:
      return

    self._updatingGUIFromMRML = True

    needleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if needleModel is not None:
      if needleModel.GetDisplayVisibility():
        self.ui.needleVisibilityButton.checked = True
      else:
        self.ui.needleVisibilityButton.checked = False

    cauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    if cauteryModel is not None:
      if cauteryModel.GetDisplayVisibility():
        self.ui.cauteryVisibilityButton.checked = True
      else:
        self.ui.cauteryVisibilityButton.checked = False

    trackingSqBr = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if trackingSqBr is not None:
      self.ui.trackingSequenceBrowserButton.checked = trackingSqBr.GetRecordingActive()

    ultrasoundSqBr = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if ultrasoundSqBr is not None:
      self.ui.startStopRecordingButton.checked = ultrasoundSqBr.GetRecordingActive()

    self._updatingGUIFromMRML = False

  def updateGUISliders(self, viewNode):
    logging.debug("updateGUISliders")
    if self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye():
      self.ui.fieldOfViewSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.ui.cameraXPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.ui.cameraYPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.ui.cameraZPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.ui.fieldOfViewSlider.setDisabled(False)
      self.ui.cameraXPosSlider.setDisabled(False)
      self.ui.cameraZPosSlider.setDisabled(False)
      self.ui.cameraYPosSlider.setDisabled(False)
    else:
      self.ui.fieldOfViewSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.ui.cameraXPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.ui.cameraYPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.ui.cameraZPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.ui.fieldOfViewSlider.setDisabled(True)
      self.ui.cameraXPosSlider.setDisabled(True)
      self.ui.cameraZPosSlider.setDisabled(True)
      self.ui.cameraYPosSlider.setDisabled(True)

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    needleVisible = self.ui.needleVisibilityButton.checked
    if needleVisible:
      self._parameterNode.SetParameter(self.logic.NEEDLE_MODEL_VISIBLE, "true")
    else:
      self._parameterNode.SetParameter(self.logic.NEEDLE_MODEL_VISIBLE, "false")

    self._parameterNode.EndModify(wasModified)


#
# LumpNav2Logic
#

class LumpNav2Logic(ScriptedLoadableModuleLogic, VTKObservationMixin):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # Transform names
  REFERENCE_TO_RAS = "ReferenceToRas"
  NEEDLE_TO_REFERENCE = "NeedleToReference"
  NEEDLETIP_TO_NEEDLE = "NeedleTipToNeedle"
  CAUTERY_TO_REFERENCE = "CauteryToReference"
  CAUTERY_TO_NEEDLE = "CauteryToNeedle"
  CAUTERYTIP_TO_CAUTERY = "CauteryTipToCautery"
  TRANSD_TO_REFERENCE = "TransdToReference"
  IMAGE_TO_TRANSD = "ImageToTransd"
  CAUTERYCAMERA_TO_CAUTERY = "CauteryCameraToCautery"
  TRANSD_TO_NEEDLE = "TransdToNeedle"
  PREDICTION_TO_NEEDLE = "PredictionToNeedle"

  CONTOUR_STATUS = "ContourStatus"
  CONTOUR_ADDING = "ContourAdding"
  POINTS_STATUS = "PointsStatus"
  POINTS_ADDING = "PointsAdding"
  POINTS_ERASING = "PointsErasing"
  CONTOUR_UNSELECTED = "ContourUnselected"
  POINTS_UNSELECTED = "PointsUnselected"

  # Ultrasound image
  IMAGE_IMAGE = "Image_Image"
  DEFAULT_US_DEPTH = 90

  # OpenIGTLink PLUS connection
  CONFIG_FILE_SETTING = "LumpNav2/PlusConfigFile"
  CONFIG_FILE_DEFAULT = "LumpNavDefault.xml"  # Default config file if the user doesn't set another.
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"
  PLUS_REMOTE_NODE = "PlusRemoteNode"

  # Model names and settings
  NEEDLE_MODEL = "NeedleModel"
  NEEDLE_VISIBILITY_SETTING = "LumpNav2/NeedleVisible"
  NEEDLETIP_TO_NEEDLE_SETTING = "NeedleTipToNeedleSetting"
  CAUTERY_MODEL = "CauteryModel"
  CAUTERY_VISIBILITY_SETTING = "LumpNav2/CauteryVisible"
  CAUTERY_MODEL_FILENAME = "CauteryModel.stl"
  CAUTERY_MODEL_SELECTED = "LumpNav2/CauteryModelSelected"
  TUMOR_MODEL = "TumorModel"
  STICK_MODEL = "StickModel"
  WARNING_SOUND_SETTING = "LumpNav2/WarningSoundEnabled"
  BREACH_MARKUPS_PROXIMITY_THRESHOLD = "LumpNav2/BreachMarkupsProximitySetting"
  BRIGHTNESS_SETTING = "LumpNav2/BrightnessSetting"

  # Model reconstruction
  ROI_NODE = "ROI"
  AI_MODEL_PATH = "BreastSeg_2021-01-05_model_0.h5"
  PREDICTION_VOLUME = "Prediction"
  RECONSTRUCTION_NODE = "ReconstructionNode"
  RECONSTRUCTION_VOLUME = "ReconstructionVolume"

  # Layout codes

  LAYOUT_2D3D = 501
  LAYOUT_TRIPLE3D = 502
  LAYOUT_DUAL3D = 503

  DISTANCE_TEXT_SCALE = '3'

  # Sequence names
  TRACKING_SEQUENCE_BROWSER = "TrackingSequenceBrowser"
  ULTRASOUND_SEQUENCE_BROWSER = "UltrasoundSequenceBrowser"
  TUMOR_MARKUPS_NEEDLE = "TumorMarkups_Needle"
  BREACH_WARNING = "LumpNavBreachWarning"
  BREACH_MARKUPS_NEEDLE = "BreachMarkups_Needle"

  RAS_MARKUPS = "DirectionMarkups_RAS"

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    slicer.mymodL = self
    VTKObservationMixin.__init__(self)

    # Telemed C5 probe geometry

    self.scaling_Intercept = 0.01663333
    self.scaling_Slope = 0.00192667

    # self.tumorMarkups_Needle = None
    self.tumorMarkupAddedObserverTag = None

    self.eraseMarkups_Needle = None
    self.eraseMarkupsAddedObserverTag = None
    self.eraseMarkupEndInteractionObserverTag = None

    self.eraserFlag = True  # Indicates if we are removing points

    self.showDistance = False

    self.saveTime = vtk.vtkTimeStamp()

    self.segmentationLogic = slicer.modules.segmentationunet.widgetRepresentation().self().logic
    self.firstOutputReady = False
    self.reconstructionLogic = slicer.modules.volumereconstruction.logic()
    self.reconstructionActive = False
    self.transferFunctionPoints = None
    self.lastSliderValue = 50

  def resourcePath(self, filename):
    """
    Returns the full path to the given resource file.
    :param filename: str, resource file name
    :returns: str, full path to file specified
    """
    moduleDir = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(moduleDir, "Resources", filename)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

    parameterNode = self.getParameterNode()
    parameterNode.SetAttribute("TipToSurfaceDistanceTextScale", "3")

  def addCustomLayouts(self):
    layout2D3D = \
      """
      <layout type="horizontal" split="true">
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="1">
            <property name="viewlabel" action="default">1</property>
          </view>
        </item>
        <item splitSize="500">
          <view class="vtkMRMLSliceNode" singletontag="Red">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">R</property>
            <property name="viewcolor" action="default">#F34A33</property>
          </view>
        </item>
      </layout>
      """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_2D3D, layout2D3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_2D3D, layout2D3D)

    layoutTriple3D = \
      """
      <layout type="vertical" split="true">
        <item splitSize="500">
          <layout type="horizontal">
            <item splitSize="500">
              <view class="vtkMRMLViewNode" singletontag="1">
                <property name="viewLabel" action="default">1</property>
              </view>
            </item>
            <item splitSize="500">
              <view class="vtkMRMLViewNode" singletontag="2" type="secondary">
                <property name="viewLabel" action="default">2</property>
              </view>
            </item>
          </layout>  
        </item>
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="3" type="tertiary">
            <property name="viewLabel" action="default">3</property>
          </view>
        </item>
      </layout>
      """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_TRIPLE3D, layoutTriple3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_TRIPLE3D, layoutTriple3D)

    layoutDual3D = \
      """
      <layout type="horizontal" split="true">
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="1">
            <property name="viewLabel" action="default">1</property>
          </view>
        </item>
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="2" type="secondary">
            <property name="viewLabel" action="default">2</property>
          </view>
        </item>
      </layout>
      """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_DUAL3D, layoutDual3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_DUAL3D, layoutDual3D)

  def setNeedleVisibility(self, visible):
    """
    Changes the visibility of the needle model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue(self.NEEDLE_VISIBILITY_SETTING, "True" if visible else "False")
    parameterNode = self.getParameterNode()
    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is not None:
      needleModel.SetDisplayVisibility(visible)

  def setCauteryVisibility(self, visible):
    """
    Changes the visibility of the cautery model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue(self.CAUTERY_VISIBILITY_SETTING, "True" if visible else "False")
    cauteryModelSelected = slicer.util.settingsValue(self.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    if cauteryModel is not None and stickModel is not None:
      if cauteryModelSelected:
        cauteryModel.SetDisplayVisibility(visible)
      else:
        stickModel.SetDisplayVisibility(visible)

  def setWarningSound(self, enabled):
    breachWarningNode = self.getParameterNode().GetNodeReference(self.BREACH_WARNING)
    if breachWarningNode is not None:
      breachWarningNode.SetPlayWarningSound(enabled)
      settings = qt.QSettings()
      settings.setValue(self.WARNING_SOUND_SETTING, enabled)

  def setup(self):
    """
    Sets up the Slicer scene. Creates nodes if they are missing.
    """
    parameterNode = self.getParameterNode()

    self.setupTransformHierarchy()

    # Show ultrasound in 2D view

    layoutManager = slicer.app.layoutManager()
    # Show ultrasound in red view.
    redSlice = layoutManager.sliceWidget('Red')
    controller = redSlice.sliceController()
    controller.setSliceVisible(True)
    redSliceLogic = redSlice.sliceLogic()
    image_Image = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    redSliceLogic.GetSliceCompositeNode().SetBackgroundVolumeID(image_Image.GetID())
    # Set up volume reslice driver.
    resliceLogic = slicer.modules.volumereslicedriver.logic()
    if resliceLogic:
      redNode = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
      # Typically the image is zoomed in, therefore it is faster if the original resolution is used
      # on the 3D slice (and also we can show the full image and not the shape and size of the 2D view)
      redNode.SetSliceResolutionMode(slicer.vtkMRMLSliceNode.SliceResolutionMatchVolumes)
      resliceLogic.SetDriverForSlice(image_Image.GetID(), redNode)
      resliceLogic.SetModeForSlice(6, redNode)  # Transverse mode, default for PLUS ultrasound.
      resliceLogic.SetFlipForSlice(False, redNode)
      resliceLogic.SetRotationForSlice(180, redNode)
      redSliceLogic.FitSliceToAll()
    else:
      logging.warning('Logic not found for Volume Reslice Driver')

    # Create models
    createModelsLogic = slicer.modules.createmodels.logic()

    # Needle model
    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is None:
      needleModel = createModelsLogic.CreateNeedle(60.0, 1.0, 2.0, 0)
      needleModel.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
      needleModel.SetName(self.NEEDLE_MODEL)
      needleModel.GetDisplayNode().SliceIntersectionVisibilityOn()
      parameterNode.SetNodeReferenceID(self.NEEDLE_MODEL, needleModel.GetID())

    needleVisible = slicer.util.settingsValue(self.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    needleModel.SetDisplayVisibility(needleVisible)

    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleModel.SetAndObserveTransformNodeID(needleTipToNeedle.GetID())

    settings = qt.QSettings()
    needleTipToNeedle_settings = slicer.util.settingsValue(self.NEEDLETIP_TO_NEEDLE_SETTING, "")
    if needleTipToNeedle_settings == "":
      needleTipToNeedle_settings = slicer.util.arrayFromTransformMatrix(needleTipToNeedle)
      needleTipToNeedle_settings = needleTipToNeedle_settings.tolist()
      needleTipToNeedle_settings = json.dumps(needleTipToNeedle_settings)
      settings.setValue(self.NEEDLETIP_TO_NEEDLE_SETTING, needleTipToNeedle_settings)
    else:
      needleTipToNeedle_settings = json.loads(needleTipToNeedle_settings)
      needleTipToNeedle_settings = np.array(needleTipToNeedle_settings)
      needleTipToNeedle_settings = slicer.util.vtkMatrixFromArray(needleTipToNeedle_settings)
      needleTipToNeedle.SetMatrixTransformToParent(needleTipToNeedle_settings)
    self.addObserver(needleTipToNeedle, slicer.vtkMRMLLinearTransformNode.TransformModifiedEvent, self.needleTipToNeedleModified)

    # Cautery model
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    if cauteryModel is None:
      cauteryModel = slicer.util.loadModel(self.resourcePath(self.CAUTERY_MODEL_FILENAME))
      cauteryModel.GetDisplayNode().SetColor(1.0, 1.0, 0.0)
      cauteryModel.SetName(self.CAUTERY_MODEL)
      parameterNode.SetNodeReferenceID(self.CAUTERY_MODEL, cauteryModel.GetID())

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    cauteryModel.SetAndObserveTransformNodeID(cauteryTipToCautery.GetID())

    cauteryVisible = slicer.util.settingsValue(self.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    cauteryModel.SetDisplayVisibility(cauteryVisible)

    # Stick Model
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    if stickModel is None:
      stickModel = createModelsLogic.CreateNeedle(100, 1.0, 2.0, 0)
      stickModel.GetDisplayNode().SetColor(1.0, 1.0, 0)
      stickModel.SetName(self.STICK_MODEL)
      stickModel.GetDisplayNode().VisibilityOff()  # Default is only cautery model, turn stick model off visibility
      parameterNode.SetNodeReferenceID(self.STICK_MODEL, stickModel.GetID())

    stickTipToStick = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    stickModel.SetAndObserveTransformNodeID(stickTipToStick.GetID())

    # Determine which cautery model to display from settings
    cauterySelected = slicer.util.settingsValue(self.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    self.setToolModelClicked(cauterySelected)

    # Create tumor model
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    if tumorModel_Needle is None:
      tumorModel_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL)
      tumorModel_Needle.CreateDefaultDisplayNodes()
      modelDisplayNode = tumorModel_Needle.GetDisplayNode()
      modelDisplayNode.SetColor(0,1,0) # Green
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      parameterNode.SetNodeReferenceID(self.TUMOR_MODEL, tumorModel_Needle.GetID())

    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    tumorModel_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())

    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if tumorMarkups_Needle is None:
      tumorMarkups_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.TUMOR_MARKUPS_NEEDLE)
      tumorMarkups_Needle.CreateDefaultDisplayNodes()
      tumorMarkups_Needle.GetDisplayNode().SetTextScale(0)
      tumorMarkups_Needle.LockedOn()
      tumorMarkups_Needle.GetDisplayNode().VisibilityOff()
      parameterNode.SetNodeReferenceID(self.TUMOR_MARKUPS_NEEDLE, tumorMarkups_Needle.GetID())
    tumorMarkups_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())
    self.removeObservers(method=self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.modifyPoints)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.onTumorMarkupsNodeModified)

    parameterNode.SetNodeReferenceID(self.TUMOR_MARKUPS_NEEDLE, tumorMarkups_Needle.GetID())

    RASMarkups = parameterNode.GetNodeReference(self.RAS_MARKUPS)
    if RASMarkups is None:
      RASMarkups = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.RAS_MARKUPS)
      RASMarkups.CreateDefaultDisplayNodes()
      RASMarkups.GetDisplayNode().SetTextScale(5)
      RASMarkups.GetDisplayNode().SetGlyphScale(5)
      RASMarkups.AddControlPoint(10, 0, 0,"RIGHT")
      RASMarkups.AddControlPoint(0, 10, 0, "ANTERIOR")
      RASMarkups.AddControlPoint(0, 0, 10, "SUPERIOR")
      RASMarkups.AddControlPoint(-10, 0, 0,"LEFT")
      RASMarkups.AddControlPoint(0, -10, 0, "POSTERIOR")
      RASMarkups.AddControlPoint(0, 0, -10, "INFERIOR")
      RASMarkups.LockedOn()
      RASMarkups.SetDisplayVisibility(0)
      parameterNode.SetNodeReferenceID(self.RAS_MARKUPS, RASMarkups.GetID())

    sequenceLogic = slicer.modules.sequences.logic()

    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)

    if sequenceBrowserTracking is None:
      sequenceBrowserTracking = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.TRACKING_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.TRACKING_SEQUENCE_BROWSER, sequenceBrowserTracking.GetID())
    cauteryToReference = parameterNode.GetNodeReference(self.CAUTERY_TO_REFERENCE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, cauteryToReference, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, needleToReference, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, needleTipToNeedle, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, cauteryTipToCautery, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    sequenceBrowserTracking.SetRecordingActive(True)  # Actually start recording

    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)

    if sequenceBrowserUltrasound is None:
      sequenceBrowserUltrasound = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.ULTRASOUND_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.ULTRASOUND_SEQUENCE_BROWSER, sequenceBrowserUltrasound.GetID())

    image_Image = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, image_Image, sequenceBrowserUltrasound)
    sequenceBrowserUltrasound.SetRecording(sequenceNode, True)
    sequenceBrowserUltrasound.SetPlayback(sequenceNode, True)
    sequenceBrowserUltrasound.SetRecordingActive(False)

    # Set up breach warning node
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    if breachWarningNode is None:
      breachWarningNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLBreachWarningNode', self.BREACH_WARNING)
      breachWarningNode.SetWarningColor(1, 0, 0)

      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      breachWarningNode.SetOriginalColor(tumorModel_Needle.GetDisplayNode().GetColor())
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      breachWarningNode.SetAndObserveToolTransformNodeId(cauteryTipToCautery.GetID())
      breachWarningNode.SetAndObserveWatchedModelNodeID(tumorModel_Needle.GetID())
      self.addObserver(breachWarningNode, vtk.vtkCommand.ModifiedEvent, self.onBreachWarningNodeChanged)
      parameterNode.SetNodeReferenceID(self.BREACH_WARNING, breachWarningNode.GetID())
      warningSoundEnabled = slicer.util.settingsValue(self.WARNING_SOUND_SETTING, True, converter=slicer.util.toBool)
      self.setWarningSound(warningSoundEnabled)

      # Line properties can only be set after the line is created (made visible at least once)
      breachWarningLogic = slicer.modules.breachwarning.logic()
      breachWarningLogic.SetLineToClosestPointVisibility(True, breachWarningNode)
      breachWarningLogic.SetLineToClosestPointTextScale(0, breachWarningNode)
      breachWarningLogic.SetLineToClosestPointColor(0, 0, 0.5, breachWarningNode)

    breachMarkups_Needle = parameterNode.GetNodeReference(self.BREACH_MARKUPS_NEEDLE)
    if breachMarkups_Needle is None:
      breachMarkups_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.BREACH_MARKUPS_NEEDLE)
      breachMarkups_Needle.CreateDefaultDisplayNodes()
      breachMarkups_Needle.GetDisplayNode().SetGlyphScale(5)
      breachMarkups_Needle.GetDisplayNode().SetTextScale(0)
      breachMarkups_Needle.GetDisplayNode().SetColor(1, 0, 0)
      breachMarkups_Needle.LockedOn()
      breachMarkups_Needle.SetDisplayVisibility(1)
      parameterNode.SetNodeReferenceID(self.BREACH_MARKUPS_NEEDLE, breachMarkups_Needle.GetID())
    breachMarkups_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())

    cauteryCameraToCautery = parameterNode.GetNodeReference(self.CAUTERYCAMERA_TO_CAUTERY)
    if cauteryCameraToCautery is None:
      cauteryCameraToCauteryFileWithPath = self.resourcePath(self.CAUTERYCAMERA_TO_CAUTERY + ".h5")
      try:
        logging.info("Loading cautery camera to cautery calibration from file: {}".format(cauteryCameraToCauteryFileWithPath))
        cauteryCameraToCautery = slicer.util.loadTransform(cauteryCameraToCauteryFileWithPath)
      except Exception as e:
        logging.info("Creating cautery camera to cautery calibration file, because none was found at: "
                     "{}".format(cauteryCameraToCauteryFileWithPath))
        cauteryCameraToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYCAMERA_TO_CAUTERY)
        m = self.createMatrixFromString('0 0 -1 0 '
                                        '1 0 0 0 '
                                        '0 -1 0 0 '
                                        '0 0 0 1')
        cauteryCameraToCautery.SetMatrixTransformToParent(m)
      parameterNode.SetNodeReferenceID(self.CAUTERYCAMERA_TO_CAUTERY, cauteryCameraToCautery.GetID())
    cauteryCameraToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

    # OpenIGTLink connection
    # self.setupPlusServer()

    # Set nodes for segmentation logic
    self.segmentationLogic.setModelPath(self.resourcePath(self.AI_MODEL_PATH))
    self.segmentationLogic.setInputImage(parameterNode.GetNodeReference(self.IMAGE_IMAGE))
    self.segmentationLogic.setOutputImage(parameterNode.GetNodeReference(self.PREDICTION_VOLUME))
    self.segmentationLogic.setOutputTransform(parameterNode.GetNodeReference(self.PREDICTION_TO_NEEDLE))

    # Start segmentation to avoid delay when user starts recording
    self.segmentationLogic.setRealTimePrediction(True)
    self.segmentationLogic.pausePrediction()

  def setupTransformHierarchy(self):
    """
    Sets up transform nodes in the scene if they don't exist yet.
    """
    parameterNode = self.getParameterNode()

    # ReferenceToRas puts everything in a rough anatomical reference (right, anterior, superior).
    # Translation is not relevant for ReferenceToRas, and rotation is fine even with +/- 30 deg error.

    referenceToRas = self.addLinearTransformToScene(self.REFERENCE_TO_RAS)

    # Needle tracking
    needleToReference = self.addLinearTransformToScene(self.NEEDLE_TO_REFERENCE, parentTransform=referenceToRas)
    self.addLinearTransformToScene(self.NEEDLETIP_TO_NEEDLE, parentTransform=needleToReference)

    # Cautery tracking
    cauteryToReference = self.addLinearTransformToScene(self.CAUTERY_TO_REFERENCE, parentTransform=referenceToRas)
    self.addLinearTransformToScene(self.CAUTERY_TO_NEEDLE)  # For cautery calibration

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    if cauteryTipToCautery is None:
      cauteryTipToCauteryFileWithPath = self.resourcePath(self.CAUTERYTIP_TO_CAUTERY + ".h5")
      try:
        logging.info("Loading cautery calibration from file: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.util.loadTransform(cauteryTipToCauteryFileWithPath)
      except Exception as e:
        logging.info("Creating cautery calibration file, because none was found as: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYTIP_TO_CAUTERY)
      parameterNode.SetNodeReferenceID(self.CAUTERYTIP_TO_CAUTERY, cauteryTipToCautery.GetID())
    cauteryTipToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

    # Ultrasound image tracking
    transdToReference = self.addLinearTransformToScene(self.TRANSD_TO_REFERENCE, parentTransform=referenceToRas)
    imageToTransd = self.addLinearTransformToScene(self.IMAGE_TO_TRANSD, parentTransform=transdToReference)
    predictionToNeedle = self.addLinearTransformToScene(self.PREDICTION_TO_NEEDLE)
    self.updateImageToTransdFromDepth(self.DEFAULT_US_DEPTH)

    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    if imageImage is None:
      imageImage = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.IMAGE_IMAGE)
      imageImage.CreateDefaultDisplayNodes()
      imageArray = np.zeros((1, 615, 525), dtype="uint8")  # TODO: temporary solution
      slicer.util.updateVolumeFromArray(imageImage, imageArray)
      parameterNode.SetNodeReferenceID(self.IMAGE_IMAGE, imageImage.GetID())
      # Update prediction volume dimensions when image dimensions change
      self.addObserver(imageImage, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.onImageImageModified)
    imageImage.SetAndObserveTransformNodeID(imageToTransd.GetID())

    predictionImage = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    if predictionImage is None:
      predictionImage = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.PREDICTION_VOLUME)
      predictionImage.CreateDefaultDisplayNodes()
      predictionDisplayNode = predictionImage.GetDisplayNode()
      predictionDisplayNode.SetWindow(205)
      predictionDisplayNode.SetLevel(220)
      predictionDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGreen")
      imageArray = np.zeros((1, 615, 525), dtype="uint8")
      slicer.util.updateVolumeFromArray(predictionImage, imageArray)
      parameterNode.SetNodeReferenceID(self.PREDICTION_VOLUME, predictionImage.GetID())
    predictionImage.SetAndObserveTransformNodeID(predictionToNeedle.GetID())

    # TransdToNeedle to display tumour reconstruction in needle coordinate system
    transdToNeedle = self.addLinearTransformToScene(self.TRANSD_TO_NEEDLE, parentTransform=needleToReference)
    parameterNode.SetNodeReferenceID(self.TRANSD_TO_NEEDLE, transdToNeedle.GetID())

  def updateImageToTransdFromDepth(self, depthMm):
    """
    Computes ImageToTransd for a specified ultrasound depth setting (millimeters), and updates the ImageToTransd
    transform node in the current MRML scene.
    """

    imageToTransdPixel = vtk.vtkTransform()
    imageToTransdPixel.Translate(-255.5, 0, 0)

    pxToMm = self.scaling_Intercept + self.scaling_Slope * depthMm

    transdPixelToTransd = vtk.vtkTransform()
    transdPixelToTransd.Scale(pxToMm, pxToMm, pxToMm)

    imageToTransd = vtk.vtkTransform()
    imageToTransd.Concatenate(transdPixelToTransd)
    imageToTransd.Concatenate(imageToTransdPixel)
    imageToTransd.Update()

    parameterNode = self.getParameterNode()
    imageToTransdNode = parameterNode.GetNodeReference(self.IMAGE_TO_TRANSD)
    imageToTransdNode.SetAndObserveTransformToParent(imageToTransd)

  def addLinearTransformToScene(self, transformName, parentTransform=None):
    """
    Makes sure there is a transform with specified name, and it is referenced in parameter node by its name.
    :param transformName: str, name and reference of the transform.
    :param parentTransform: vtkMRMLLinearTransformNode, optional parent tranform
    :returns: vtkMRMLLinearTransformNode, the existing or newly created transform named trasnformName
    """
    parameterNode = self.getParameterNode()
    transform = parameterNode.GetNodeReference(transformName)
    if transform is None:
      transform = slicer.mrmlScene.GetFirstNodeByName(transformName)
      if transform is None:
        transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", transformName)
      parameterNode.SetNodeReferenceID(transformName, transform.GetID())
    if parentTransform is not None:
      transform.SetAndObserveTransformNodeID(parentTransform.GetID())
    else:
      transform.SetAndObserveTransformNodeID(None)
    return transform

  def setupPlusServer(self):
    """
    Creates PLUS server and OpenIGTLink connection if it doesn't exist already.
    """
    parameterNode = self.getParameterNode()

    # Check if config file is specified in settings. Set and use default if not.
    configFullpath = slicer.util.settingsValue(self.CONFIG_FILE_SETTING, '')
    if configFullpath == '':
      configFullpath = self.resourcePath(self.CONFIG_FILE_DEFAULT)
      settings = qt.QSettings()
      settings.setValue(self.CONFIG_FILE_SETTING, configFullpath)

    # Make sure text node for config file exists
    configTextNode = parameterNode.GetNodeReference(self.CONFIG_TEXT_NODE)
    if configTextNode is None:
      configTextNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", self.CONFIG_TEXT_NODE)
      configTextNode.SaveWithSceneOff()
      configTextNode.SetForceCreateStorageNode(slicer.vtkMRMLTextNode.CreateStorageNodeAlways)
      parameterNode.SetNodeReferenceID(self.CONFIG_TEXT_NODE, configTextNode.GetID())
    if not configTextNode.GetStorageNode():
      configTextNode.AddDefaultStorageNode()
    configTextStorageNode = configTextNode.GetStorageNode()
    configTextStorageNode.SaveWithSceneOff()
    configTextStorageNode.SetFileName(configFullpath)
    configTextStorageNode.ReadData(configTextNode)

    # Make sure PLUS server and launcher exist, and launcher references server
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    if not plusServerNode:
      plusServerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerNode", self.PLUS_SERVER_NODE)
      plusServerNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.PLUS_SERVER_NODE, plusServerNode.GetID())
    plusServerNode.SetAndObserveConfigNode(configTextNode)

    plusServerLauncherNode = parameterNode.GetNodeReference(self.PLUS_SERVER_LAUNCHER_NODE)
    if not plusServerLauncherNode:
      plusServerLauncherNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerLauncherNode", self.PLUS_SERVER_LAUNCHER_NODE)
      plusServerLauncherNode.SaveWithSceneOff()

    if plusServerLauncherNode.GetNodeReferenceID('plusServerRef') != plusServerNode.GetID():
      plusServerLauncherNode.AddAndObserveServerNode(plusServerNode)

    # TODO: may not be the right way to start server?
    plusRemoteNode = parameterNode.GetNodeReference(self.PLUS_REMOTE_NODE)
    if not plusRemoteNode:
      plusRemoteNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLIGTLConnectorNode", self.PLUS_REMOTE_NODE)
      plusRemoteNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.PLUS_REMOTE_NODE, plusRemoteNode.GetID())

  def setTrackingSequenceBrowser(self, recording):
    parameterNode = self.getParameterNode()
    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)
    sequenceBrowserTracking.SetRecordingActive(recording)  # stop

  def onUltrasoundSequenceBrowserClicked(self, toggled):
    self.setUltrasoundSequenceBrowser(toggled)
    self.setLivePrediction(toggled)
    if toggled:
      self.segmentationLogic.resumePrediction()
    else:
      self.segmentationLogic.pausePrediction()

  def setLivePrediction(self, toggled):
    logging.info(f"setLivePrediction({toggled})")
    parameterNode = self.getParameterNode()
    imageToTransd = parameterNode.GetNodeReference(self.IMAGE_TO_TRANSD)
    transdToNeedle = parameterNode.GetNodeReference(self.TRANSD_TO_NEEDLE)
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)

    if toggled:
      # Rearrange transform hierarchy so that Needle is effectively world
      imageToTransd.SetAndObserveTransformNodeID(transdToNeedle.GetID())
      transdToNeedle.SetAndObserveTransformNodeID(None)
      needleTipToNeedle.SetAndObserveTransformNodeID(None)

      # Start prediction
      self.setRegionOfInterestNode(toggled)
      self.segmentationLogic.resumePrediction()
      # self.segmentationLogic.setRealTimePrediction(toggled)
      self.setVolumeReconstruction(toggled)

    else:
      # Stop prediction
      self.segmentationLogic.pausePrediction()
      # self.segmentationLogic.setRealTimePrediction(toggled)

      # Move transforms back
      transdToReference = parameterNode.GetNodeReference(self.TRANSD_TO_REFERENCE)
      needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
      imageToTransd.SetAndObserveTransformNodeID(transdToReference.GetID())
      transdToNeedle.SetAndObserveTransformNodeID(needleToReference.GetID())
      needleTipToNeedle.SetAndObserveTransformNodeID(needleToReference.GetID())

      # If reconstruction is live, moving ROI will automatically move the reconstruction volume
      roiNode = parameterNode.GetNodeReference(self.ROI_NODE)
      roiNode.SetAndObserveTransformNodeID(needleToReference.GetID())

  def setUltrasoundSequenceBrowser(self, recording):
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop

  def setSegmentationVisibility(self, toggled):
    parameterNode = self.getParameterNode()
    segmentationVolume = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    reconstructionVolume = parameterNode.GetNodeReference(self.RECONSTRUCTION_VOLUME)
    if segmentationVolume is not None and reconstructionVolume is not None:
      if toggled:
        slicer.util.setSliceViewerLayers(foreground=segmentationVolume, foregroundOpacity=0.5)
        reconstructionVolume.SetDisplayVisibility(True)
      else:
        slicer.util.setSliceViewerLayers(foreground=None)
        reconstructionVolume.SetDisplayVisibility(False)
    else:
      logging.warning("setSegmentationVisibility() called but no segmentation volume found")

  def setRegionOfInterestNode(self, toggled):
    if not toggled:
      return

    parameterNode = self.getParameterNode()
    roiNode = parameterNode.GetNodeReference(self.ROI_NODE)
    if roiNode is None:
      # Create new ROI node
      roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", self.ROI_NODE)
      parameterNode.SetNodeReferenceID(self.ROI_NODE, roiNode.GetID())
      roiNode.SetDisplayVisibility(False)
    else:
      # Move ROI out of transform hierarchy
      roiNode.SetAndObserveTransformNodeID(None)

    # Set center of ROI to be center of current image
    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    bounds = [0, 0, 0, 0, 0, 0]
    imageImage.GetSliceBounds(bounds, vtk.vtkMatrix4x4())
    sliceCenter = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2]
    roiNode.SetXYZ(sliceCenter)
    roiNode.SetRadiusXYZ(100, 100, 100)
    logging.info(f"Added a 10x10x10cm ROI at position: {sliceCenter}")

  def setVolumeReconstruction(self, toggled):
    parameterNode = self.getParameterNode()
    reconstructionNode = parameterNode.GetNodeReference(self.RECONSTRUCTION_NODE)

    if toggled:
      if self.reconstructionActive:
        return

      logging.info("Starting volume reconstruction")
      # Set up nodes for live reconstruction
      if reconstructionNode is None:
        reconstructionNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVolumeReconstructionNode", self.RECONSTRUCTION_NODE)
        parameterNode.SetNodeReferenceID(self.RECONSTRUCTION_NODE, reconstructionNode.GetID())
        reconstructionNode.SetLiveVolumeReconstruction(True)
        reconstructionNode.SetInterpolationMode(1)  # linear interpolation

      reconstructionNode.SetAndObserveInputVolumeNode(parameterNode.GetNodeReference(self.PREDICTION_VOLUME))
      reconstructionNode.SetAndObserveInputROINode(parameterNode.GetNodeReference(self.ROI_NODE))

      # Create volume node for reconstruction output
      reconstructionVolume = parameterNode.GetNodeReference(self.RECONSTRUCTION_VOLUME)
      if reconstructionVolume is None:
        reconstructionVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.RECONSTRUCTION_VOLUME)
        parameterNode.SetNodeReferenceID(self.RECONSTRUCTION_VOLUME, reconstructionVolume.GetID())

      reconstructionNode.SetAndObserveOutputVolumeNode(reconstructionVolume)
      volRenLogic = slicer.modules.volumerendering.logic()
      reconstructionDisplayNode = volRenLogic.CreateVolumeRenderingDisplayNode()
      reconstructionDisplayNode.UnRegister(volRenLogic)
      slicer.mrmlScene.AddNode(reconstructionDisplayNode)
      reconstructionVolume.AddAndObserveDisplayNodeID(reconstructionDisplayNode.GetID())
      volRenLogic.UpdateDisplayNodeFromVolumeNode(reconstructionDisplayNode, reconstructionVolume)
      reconstructionDisplayNode.SetAndObserveROINodeID(parameterNode.GetNodeReference(self.ROI_NODE).GetID())
      self.setVolumeRenderingProperty(reconstructionVolume, 50, 220)
      reconstructionVolume.SetDisplayVisibility(False)
      self.reconstructionLogic.StartLiveVolumeReconstruction(reconstructionNode)
      self.reconstructionActive = True

    else:
      logging.info("Stopping volume reconstruction")
      self.reconstructionLogic.StopLiveVolumeReconstruction(reconstructionNode)
      self.reconstructionActive = False

  def setVolumeRenderingProperty(self, volumeNode, window, level):
    # Manually define volume property for volume rendering
    volRenLogic = slicer.modules.volumerendering.logic()
    displayNode = volRenLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)

    upper = min(265, level + window / 2)
    lower = max(0, level - window / 2)
    p0 = lower
    p1 = lower + (upper - lower) * 0.15
    p2 = lower + (upper - lower) * 0.4
    p3 = upper
    self.transferFunctionPoints = [p0, p1, p2, p3]

    opacityTransferFunction = vtk.vtkPiecewiseFunction()
    opacityTransferFunction.AddPoint(p0, 0.0)
    opacityTransferFunction.AddPoint(p1, 0.3)
    opacityTransferFunction.AddPoint(p2, 0.6)
    opacityTransferFunction.AddPoint(p3, 1.0)

    colorTransferFunction = vtk.vtkColorTransferFunction()
    colorTransferFunction.AddRGBPoint(p0, 0.25, 0.10, 0.00)
    colorTransferFunction.AddRGBPoint(p1, 0.15, 0.20, 0.00)
    colorTransferFunction.AddRGBPoint(p2, 0.05, 0.35, 0.00)
    colorTransferFunction.AddRGBPoint(p3, 0.00, 0.50, 0.00)

    # The property describes how the data will look
    volumeProperty = displayNode.GetVolumePropertyNode().GetVolumeProperty()
    volumeProperty.SetColor(colorTransferFunction)
    volumeProperty.SetScalarOpacity(opacityTransferFunction)
    volumeProperty.ShadeOn()
    volumeProperty.SetInterpolationTypeToLinear()

  def setDeleteLastFiducialClicked(self, numberOfPoints):
    deleted_coord = [0.0, 0.0, 0.0]
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints-1,deleted_coord)
    tumorMarkups_Needle.RemoveMarkup(numberOfPoints-1)
    logging.info("Deleted last fiducial at %s", deleted_coord)
    if numberOfPoints <= 1:
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      parameterNode = self.getParameterNode()
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      tumorModel_Needle.Modified()

  def setDeleteAllFiducialsClicked(self):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.RemoveAllMarkups()
    logging.info("Deleted all fiducials")

    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(0.001)
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
    tumorModel_Needle.Modified()

  def setMarkPointCauteryTipClicked(self):
    parameterNode = self.getParameterNode()
    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    cauteryTipToNeedle = vtk.vtkMatrix4x4()
    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    cauteryTipToCautery.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedle)
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.AddControlPoint(cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))
    logging.info("Tumor point placed at cautery tip, (%s, %s, %s)", cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))

  def setFreezeUltrasoundClicked(self, toggled):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    if toggled:
      # self.guideletParent.connectorNode.Stop()
      plusServerNode.StopServer()
    else:
      # self.guideletParent.connectorNode.Start()
      plusServerNode.StartServer()

  def setToolModelClicked(self, toggled):
    logging.info("setToolModelClicked")
    settings = qt.QSettings()
    settings.setValue(self.CAUTERY_MODEL_SELECTED, "True" if toggled else "False")
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    isCauteryVisible = slicer.util.settingsValue(self.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    if isCauteryVisible:  # Only toggle if cautery visibility is enabled
      if cauteryModel is not None and stickModel is not None:
        if toggled:
          cauteryModel.SetDisplayVisibility(True)
          stickModel.SetDisplayVisibility(False)
        else:
          cauteryModel.SetDisplayVisibility(False)
          stickModel.SetDisplayVisibility(True)

  def setBreachWarningOn(self, active):
    """
    Turns breach warning on or off
    """
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    if active == True:
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      breachWarningNode.SetAndObserveToolTransformNodeId(cauteryTipToCautery.GetID())
    else:
      breachWarningNode.SetAndObserveToolTransformNodeId(None)

  def setRulerVisibility(self, toggled):
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    breachWarningLogic = slicer.modules.breachwarning.logic()
    if toggled:
      breachWarningLogic.SetLineToClosestPointVisibility(True, breachWarningNode)
    else:
      breachWarningLogic.SetLineToClosestPointVisibility(False, breachWarningNode)

  def setBrightness(self, maxLevel):
    self.setImageMinMaxLevel(0, maxLevel)

  def setImageMinMaxLevel(self, minLevel, maxLevel):
    parameterNode = self.getParameterNode()
    liveUSNode = parameterNode.GetNodeReference(self.IMAGE_IMAGE).GetDisplayNode()
    liveUSNode.SetAutoWindowLevel(0)
    liveUSNode.SetWindowLevelMinMax(minLevel, maxLevel)

  def onTumorMarkupsNodeModified(self, observer, eventid):
    logging.debug("onTumorMarkupsNodeModified")
    self.createTumorFromMarkups()
    parameterNode = self.getParameterNode()
    parameterNode.Modified()

  def createTumorFromMarkups(self):
    logging.debug('createTumorFromMarkups')
    # Create polydata point set from markup points
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if numberOfPoints < 1:
      sphereSource = vtk.vtkSphereSource()
      # sphereSource.SetRadius(0.001)
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      tumorModel_Needle.Modified()
      return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]
    for i in range(numberOfPoints):
      tumorMarkups_Needle.GetNthControlPointPosition(i, new_coord)
      points.SetPoint(i, new_coord)

    tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints - 1, new_coord)
    logging.info("Placed point at position: %s", new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)
    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)

    delaunay = vtk.vtkDelaunay3D()

    logging.debug("use glyphs")
    sphere = vtk.vtkCubeSource()
    glyph = vtk.vtkGlyph3D()
    glyph.SetInputData(pointPolyData)
    glyph.SetSourceConnection(sphere.GetOutputPort())
    # glyph.SetVectorModeToUseNormal()
    # glyph.SetScaleModeToScaleByVector()
    # glyph.SetScaleFactor(0.25)
    delaunay.SetInputConnection(glyph.GetOutputPort())
    # print("delaunay")
    # print(delaunay)
    delaunay.Update()
    surfaceFilter = vtk.vtkDataSetSurfaceFilter()
    surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

    smoother = vtk.vtkButterflySubdivisionFilter()
    smoother.SetInputConnection(surfaceFilter.GetOutputPort())
    smoother.SetNumberOfSubdivisions(3)
    smoother.Update()

    delaunaySmooth = vtk.vtkDelaunay3D()
    delaunaySmooth.SetInputData(smoother.GetOutput())
    delaunaySmooth.Update()
    #print("delaySmooth")
    #print(delaunaySmooth)
    smoothSurfaceFilter = vtk.vtkDataSetSurfaceFilter()
    smoothSurfaceFilter.SetInputConnection(delaunaySmooth.GetOutputPort())
    #print("smoothSurface")
    #print(smoothSurfaceFilter)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(smoothSurfaceFilter.GetOutputPort())
    normals.SetFeatureAngle(100.0)
    #print("normals")
    #print(normals)
    normals.Update()
    parameterNode = self.getParameterNode()
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.SetAndObservePolyData(normals.GetOutput())

  def modifyPoints(self, observer, eventID):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if parameterNode.GetParameter(self.POINTS_STATUS) == self.POINTS_ERASING:
      numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
      mostRecentPoint = [0.0, 0.0, 0.0]
      tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints - 1, mostRecentPoint)
      closestPoint, closestPointPosition = self.returnClosestPoint(tumorMarkups_Needle, mostRecentPoint)
      tumorMarkups_Needle.RemoveMarkup(closestPoint)
      tumorMarkups_Needle.RemoveMarkup(tumorMarkups_Needle.GetNumberOfControlPoints() - 1)
      logging.info("Used eraser to remove point at %s", closestPointPosition)
      self.createTumorFromMarkups()

  def returnClosestPoint(self, fiducialNode, erasePoint):
    # Returns closest marked point to where eraser fiducial was placed
    closestIndex = 0
    distanceToClosest = np.inf
    fiducialPosition = [0.0, 0.0, 0.0]
    numberOfPoints = fiducialNode.GetNumberOfControlPoints()
    for fiducialIndex in range(numberOfPoints - 1):
      fiducialNode.GetNthControlPointPosition(fiducialIndex, fiducialPosition)
      distanceToPoint = self.calculateDistance(fiducialPosition, erasePoint)
      if distanceToPoint < distanceToClosest:
        closestIndex = fiducialIndex
        distanceToClosest = distanceToPoint
    fiducialNode.GetNthFiducialPosition(closestIndex, fiducialPosition)
    return closestIndex, fiducialPosition

  def onBreachWarningNodeChanged(self, observer, eventid):
    if self.showDistance:
      self.showDistanceToTumor()
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    if breachWarningNode.GetClosestDistanceToModelFromToolTip() < 0:
      # Display breach warning text in corner of view
      for i in range(slicer.app.layoutManager().threeDViewCount):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "BREACH!")
        textProperty = view.cornerAnnotation().GetTextProperty()
        textProperty.SetColor(1, 0, 0)
        view.forceRender()

      # Get coordinate of cautery tip in needle coordinate system
      needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
      cauteryTipToNeedle = vtk.vtkMatrix4x4()
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      cauteryTipToCautery.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedle)
      cauteryTip_needleTip = cauteryTipToNeedle.MultiplyFloatPoint([0, 0, 0, 1])

      # Check if another fiducial already exists within threshold distance from cautery tip
      breachMarkupsProximityThreshold = slicer.util.settingsValue(self.BREACH_MARKUPS_PROXIMITY_THRESHOLD, 1, converter=lambda x: int(x))
      breachMarkups_Needle = parameterNode.GetNodeReference(self.BREACH_MARKUPS_NEEDLE)
      if not self.hasFiducialWithinDistance(breachMarkups_Needle, cauteryTip_needleTip[0:3], breachMarkupsProximityThreshold):
        breachMarkups_Needle.AddControlPoint(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2], "")
        logging.info(f"Added breach warning fiducial at position {cauteryTip_needleTip[0:3]}")

    else:
      # Remove corner annotation
      for i in range(slicer.app.layoutManager().threeDViewCount):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "")
        textProperty = view.cornerAnnotation().GetTextProperty()
        textProperty.SetColor(1, 1, 1)
        view.forceRender()

  def hasFiducialWithinDistance(self, markupsNode, point, threshold):
    numberOfPoints = markupsNode.GetNumberOfControlPoints()
    for fiducialIndex in range(numberOfPoints):
      fiducialPosition = markupsNode.GetNthControlPointPosition(fiducialIndex)
      distance = self.calculateDistance(point, fiducialPosition)
      if distance <= threshold:
        return True
    else:
      return False

  def showDistanceToTumor(self):
    breachWarningNode = self.getParameterNode().GetNodeReference(self.BREACH_WARNING)
    for i in range(slicer.app.layoutManager().threeDViewCount):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()
      if distanceToTumor > 10:  # Only show distance with 2 decimal places if the cautery is within 10mm of the tumor boundary
        view.setCornerAnnotationText("{0:.1f}mm".format(breachWarningNode.GetClosestDistanceToModelFromToolTip()))
      else:
        view.setCornerAnnotationText("{0:.2f}mm".format(breachWarningNode.GetClosestDistanceToModelFromToolTip()))

  def onImageImageModified(self, observer, eventid):
    self.updatePredictionImageDimensions()

  def updatePredictionImageDimensions(self):
    parameterNode = self.getParameterNode()
    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    imageDimensions = imageImage.GetImageData().GetDimensions()
    predictionImage = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    predictionData = predictionImage.GetImageData()
    if predictionData.GetDimensions() != imageDimensions:
      predictionData.SetDimensions(imageDimensions)

  def needleTipToNeedleModified(self, observer, eventid):
    logging.debug('needleTipToNeedleModified')
    import json
    settings = qt.QSettings()
    parameterNode = self.getParameterNode()
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleTipToNeedle_settings = slicer.util.arrayFromTransformMatrix(needleTipToNeedle)
    needleTipToNeedle_settings = needleTipToNeedle_settings.tolist()
    needleTipToNeedle_settings = json.dumps(needleTipToNeedle_settings)
    settings.setValue(self.NEEDLETIP_TO_NEEDLE_SETTING, needleTipToNeedle_settings)

  def setDisplayCauteryStateClicked(self, pressed):
    parameterNode = self.getParameterNode()
    import CauteryClassification
    cauteryClassificationLogic = CauteryClassification.CauteryClassificationLogic()
    #cauteryClassificationLogic.init()
    cauteryClassificationLogic.setup()
    cauteryClassificationLogic.setUseModelClicked(pressed)

  @staticmethod
  def calculateDistance(point1, point2):
    tumorFiducialPoint = np.array(point1)
    eraserPoint = np.array(point2)
    distance = np.linalg.norm(tumorFiducialPoint - eraserPoint)
    return distance

  @staticmethod
  def createMatrixFromString(transformMatrixString):
    transformMatrix = vtk.vtkMatrix4x4()
    transformMatrixArray = list(map(float, transformMatrixString.split(' ')))
    for r in range(4):
      for c in range(4):
        transformMatrix.SetElement(r, c, transformMatrixArray[r*4+c])
    return transformMatrix


#
# LumpNav2Test
#

class LumpNav2Test(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LumpNav21()

  def test_LumpNav21(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('LumpNav21')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = LumpNav2Logic()


    self.delayDisplay('Test passed')

