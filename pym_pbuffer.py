
import sys, io
import pym
from PyQt4 import QtCore, QtGui, QtOpenGL
from PIL import Image

try:
    from OpenGL import GL
except ImportError:
    app = QtGui.QApplication(sys.argv)
    QtGui.QMessageBox.critical(None, "pym-audio-visualizer",
            "PyOpenGL must be installed to run this example.")
    sys.exit(1)

# https://stackoverflow.com/questions/29252214/opengl-offscreen-in-separate-thread-with-qt-4-8?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa

class ImageRenderer(object):

    def __init__(self, settings, flags):
        self.width = settings.windowWidth
        self.height = settings.windowHeight
        self.format = QtOpenGL.QGLFormat()
        self.pbuffer = QtOpenGL.QGLPixelBuffer(
            settings.windowWidth, settings.windowHeight,self.format) 
        self.pbuffer.makeCurrent() 
        self.pym = pym.Pym(settings,flags)   
        self.pym.resetGL(self.width, self.height)
        self.pbuffer.doneCurrent() 

    def renderFrame(self, audio_data):
        self.pbuffer.makeCurrent() 
        self.pym.PCM().addPCM16Data(audio_data)

        
        GL.glClearColor( 0.0, 0.0, 0.0, 0.0 )
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self.pym.renderFrame()
        GL.glFlush()
        self.pbuffer.doneCurrent() 

    def to_image(self):
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.ReadWrite)
        im = self.pbuffer.toImage()
        im2 = QtGui.QImage(im.bits(), im.width(), im.height(), QtGui.QImage.Format_ARGB32);
        im2.save(buffer, "PNG")

        strio = io.BytesIO()
        strio.write(buffer.data())
        buffer.close()
        strio.seek(0)
        return Image.open(strio)

