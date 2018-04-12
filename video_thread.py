from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtCore import pyqtSignal, pyqtSlot
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageQt import ImageQt
import core
import numpy
import subprocess as sp
import sys
import pym
import pym_pbuffer

class Worker(QtCore.QObject):

  videoCreated = pyqtSignal()
  progressBarUpdate = pyqtSignal(int)
  progressBarSetText = pyqtSignal(str)

  def __init__(self, parent=None):
    QtCore.QObject.__init__(self)
    parent.videoTask.connect(self.createVideo)
    self.core = core.Core()

    FPS = 30
    # init projectM
    settings = pym.Settings()
    settings.windowWidth = 1280
    settings.windowHeight = 720
    settings.meshX = 1
    settings.meshY = 1
    settings.fps   = FPS
    settings.textureSize = 2048
    settings.smoothPresetDuration = 3
    settings.presetDuration = 7
    settings.beatSensitivity = 0.8
    settings.aspectCorrection = 1
    settings.easterEgg = 0
    settings.shuffleEnabled = 1
    settings.softCutRatingsEnabled = 1
    base_path = ""
    settings.presetURL = base_path + "/home/bryan/projects/projectm_install/share/projectM/presets/"
    #settings.presetURL = base_path + "/home/bryan/projectm/src/projectM-sdl/presets/presets_milkdrop_200/";
    settings.menuFontURL = base_path + "fonts/Vera.ttf"
    settings.titleFontURL = base_path + "fonts/Vera.ttf"

    self.renderer = pym_pbuffer.ImageRenderer(settings, 0)




  @pyqtSlot(str, str, QtGui.QFont, int, int, int, int, tuple, tuple, str, str)
  def createVideo(self, backgroundImage, titleText, titleFont, fontSize, alignment,\
                    xOffset, yOffset,  textColor, visColor, inputFile, outputFile):
    # print('worker thread id: {}'.format(QtCore.QThread.currentThreadId()))
    def getBackgroundAtIndex(i):
        return self.core.drawBaseImage(
            backgroundFrames[i],
            titleText,
            titleFont,
            fontSize,
            alignment,
            xOffset,
            yOffset,
            textColor,
            visColor)

    
    def combineImages(fg_image, bg_image):
      im = Image.new("RGB", (1280, 720), "black")
      im.paste(bg_image, (0, 0))

      fg_image = fg_image.convert("RGBA")

      datas = fg_image.getdata()

      newData = []
      for item in datas:
        if item[0] == 0 and item[1] == 0 and item[2] == 0:
          newData.append((0, 0, 0, 0))
        else:
          newData.append(item)
      fg_image.putdata(newData)

      im.paste(fg_image, (0, 0), mask=fg_image)
      return im



    progressBarValue = 0
    self.progressBarUpdate.emit(progressBarValue)
    self.progressBarSetText.emit('Loading background image…')

    backgroundFrames = self.core.parseBaseImage(backgroundImage)
    if len(backgroundFrames) < 2:
        # the base image is not a video so we can draw it now
        imBackground = getBackgroundAtIndex(0)
    else:
        # base images will be drawn while drawing the audio bars
        imBackground = None
        
    self.progressBarSetText.emit('Loading audio file…')
    completeAudioArray = self.core.readAudioFile(inputFile)

    # test if user has libfdk_aac
    encoders = sp.check_output(self.core.FFMPEG_BIN + " -encoders -hide_banner", shell=True)
    if b'libfdk_aac' in encoders:
      acodec = 'libfdk_aac'
    else:
      acodec = 'aac'

    ffmpegCommand = [ self.core.FFMPEG_BIN,
       '-y', # (optional) means overwrite the output file if it already exists.
       '-f', 'rawvideo',
       '-vcodec', 'rawvideo',
       '-s', '1280x720', # size of one frame
       '-pix_fmt', 'rgb24',
       '-r', '30', # frames per second
       '-i', '-', # The input comes from a pipe
       '-an',
       '-i', inputFile,
       '-acodec', acodec, # output audio codec
       '-b:a', "192k",
       '-vcodec', "libx264",
       '-pix_fmt', "yuv420p",
       '-preset', "medium",
       '-f', "mp4"]

    if acodec == 'aac':
      ffmpegCommand.append('-strict')
      ffmpegCommand.append('-2')

    ffmpegCommand.append(outputFile)
    
    out_pipe = sp.Popen(ffmpegCommand,
        stdin=sp.PIPE,stdout=sys.stdout, stderr=sys.stdout)

    sampleSize = 1470
    
    numpy.seterr(divide='ignore')
    bgI = 0
    for i in range(0, len(completeAudioArray), sampleSize):
      # create video for output
      self.renderer.renderFrame(completeAudioArray[i:i+sampleSize])  
      imForeground = self.renderer.to_image()
      if imBackground != None:
        im = combineImages(imForeground, imBackground)
      else:
        im = combineImages(imForeground, getBackgroundAtIndex(bgI))
        if bgI < len(backgroundFrames)-1:
            bgI += 1
      # write to out_pipe
      try:
        out_pipe.stdin.write(im.tobytes())
      finally:
        True

      # increase progress bar value
      if progressBarValue + 1 <= (i / len(completeAudioArray)) * 100:
        progressBarValue = numpy.floor((i / len(completeAudioArray)) * 100)
        self.progressBarUpdate.emit(progressBarValue)
        self.progressBarSetText.emit('%s%%' % str(int(progressBarValue)))

    numpy.seterr(all='print')

    out_pipe.stdin.close()
    if out_pipe.stderr is not None:
      print(out_pipe.stderr.read())
      out_pipe.stderr.close()
    # out_pipe.terminate() # don't terminate ffmpeg too early
    out_pipe.wait()
    print("Video file created")
    self.core.deleteTempDir()
    self.progressBarUpdate.emit(100)
    self.progressBarSetText.emit('100%')
    self.videoCreated.emit()
