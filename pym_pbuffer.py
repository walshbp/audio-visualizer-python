
import sys, io
import pym
import numpy
from PyQt4 import QtCore, QtGui, QtOpenGL
from PIL import Image

try:
    from OpenGL import GL
    from OpenGL import GLU
except ImportError:
    app = QtGui.QApplication(sys.argv)
    QtGui.QMessageBox.critical(None, "pym-audio-visualizer",
            "PyOpenGL must be installed to run this example.")
    sys.exit(1)

# https://stackoverflow.com/questions/29252214/opengl-offscreen-in-separate-thread-with-qt-4-8?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa

class BackgroundImageRenderer(object):
    def __init__(self, filename):

        self.id = GL.glGenTextures(1)

        GL.glEnable(GL.GL_TEXTURE_2D)

        GL.glGenTextures(1, self.id)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.id)

        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_DECAL)

        img = Image.open(filename) # .jpg, .bmp, etc. also work
        img_data = numpy.array(list(img.getdata()), numpy.int8)
 
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, img.size[0], img.size[1],
            0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data)
        self.iw = img.size[0]
        self.ih = img.size[1]
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_LINEAR)

        GL.glDisable(GL.GL_TEXTURE_2D)
    
    def render(self, width, height):
        GL.glBindTexture( GL.GL_TEXTURE_2D, self.id ) 

        # orthogonal start
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GLU.gluOrtho2D(-width/2, width/2, -height/2, height/2)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        # texture width/height
        iw = self.iw
        ih = self.ih

        GL.glPushMatrix()
        GL.glTranslatef( -iw/2, -ih/2, 0 )
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2i(0,0)
        GL.glVertex2i(0, 0)
        GL.glTexCoord2i(1,0)
        GL.glVertex2i(iw, 0)
        GL.glTexCoord2i(1,1)
        GL.glVertex2i(iw, ih)
        GL.glTexCoord2i(0,1)
        GL.glVertex2i(0, ih)
        GL.glEnd()
        GL.glPopMatrix()

        # orthogonalEnd()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)

class ProjectMRenderer(object):

    def __init__(self, settings, flags):
        self.width = settings.windowWidth
        self.height = settings.windowHeight
        self.format = QtOpenGL.QGLFormat()
        self.format.setAlpha(True)
        self.format.setRgba(True)
        self.pbuffer = QtOpenGL.QGLPixelBuffer(
            settings.windowWidth, settings.windowHeight,self.format) 
        self.pbuffer.makeCurrent() 
        self.pym = pym.Pym(settings,flags)   
        self.pym.resetGL(self.width, self.height)
        #GL.glEnable (GL.GL_BLEND)
        #GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA, GL.GL_ONE, GL.GL_ONE)
        self.pbuffer.doneCurrent() 
        self.i = 0

    def loadBackgroundImage(self, filename):
        self.background = BackgroundImageRenderer(filename)


    def renderFrame(self, audio_data):
        self.pbuffer.makeCurrent() 
        self.pym.PCM().addPCM16Data(audio_data)
        #GL.glEnable (GL.GL_BLEND)
        #GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        GL.glClearColor( 0., 0.0, 0.0, 0.0 )
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        #GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
        #self.background.render(self.width,self.height)
        self.pym.renderFrame()
        
        GL.glFlush()
        self.pbuffer.doneCurrent() 

    def to_image(self):
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.ReadWrite)
        im = self.pbuffer.toImage()
        #print("format: %d " % im.format())
        im2 = QtGui.QImage(im.bits(), im.width(), im.height(), QtGui.QImage.Format_ARGB32);
        im2.save(buffer, "PNG")
        strio = io.BytesIO()
        strio.write(buffer.data())
        buffer.close()
        strio.seek(0)
        return Image.open(strio)

