#
# Copyright (c) 2012 Peter de Rivaz
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.
#
# Raspberry Pi 3d demo using OpenGLES 2.0 via Python
#
# Version 0.1 (Draws a rectangle using vertex and fragment shaders)
# Version 0.2 (Draws a Julia set on top of a Mandelbrot controlled by the mouse.  Mandelbrot rendered to texture in advance.

import ctypes
import time
import math
# Pick up our constants extracted from the header files with prepare_constants.py
from egl import *
from gl2 import *
from gl2ext import *

# Define verbose=True to get debug messages
verbose = False

# Define some extra constants that the automatic extraction misses
EGL_DEFAULT_DISPLAY = 0
EGL_NO_CONTEXT = 0
EGL_NO_DISPLAY = 0
EGL_NO_SURFACE = 0
DISPMANX_PROTECTION_NONE = 0

# Open the libraries
bcm = ctypes.CDLL('libbcm_host.so')
opengles = ctypes.CDLL('libGLESv2.so')
openegl = ctypes.CDLL('libEGL.so')

eglint = ctypes.c_int

eglshort = ctypes.c_short

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint*len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat*len(L))(*L)
                
class Alpha_struct(ctypes.Structure):
  """typedef enum {
  /* Bottom 2 bits sets the alpha mode */
  DISPMANX_FLAGS_ALPHA_FROM_SOURCE = 0,
  DISPMANX_FLAGS_ALPHA_FIXED_ALL_PIXELS = 1,
  DISPMANX_FLAGS_ALPHA_FIXED_NON_ZERO = 2,
  DISPMANX_FLAGS_ALPHA_FIXED_EXCEED_0X07 = 3,

  DISPMANX_FLAGS_ALPHA_PREMULT = 1 << 16,
  DISPMANX_FLAGS_ALPHA_MIX = 1 << 17
} DISPMANX_FLAGS_ALPHA_T;

typedef struct {
  DISPMANX_FLAGS_ALPHA_T flags;
  uint32_t opacity;
  VC_IMAGE_T *mask;
} DISPMANX_ALPHA_T;

typedef struct {
  DISPMANX_FLAGS_ALPHA_T flags;
  uint32_t opacity;
  DISPMANX_RESOURCE_HANDLE_T mask;
} VC_DISPMANX_ALPHA_T;  /* for use with vmcs_host */

"""
  _fields_ = [ ("flags", ctypes.c_long),
               ("opacity", ctypes.c_ulong),
               ("mask", ctypes.c_ulong)]

def check(e):
    """Checks that error is zero"""
    if e==0: return
    if verbose:
        print 'Error code',hex(e&0xffffffff)
    raise ValueError

class ShaderCompilationFailed(Exception):
    def __init__(self, reason=None):
        self.reason = reason

class GLError(Exception):
    def __init__(self, code=None):
        self.code = code

    def __str__(self):
        if self.code:
            if self.code == GL_NO_ERROR:
                return "No Error found (%s)" % self.code
            elif self.code == GL_INVALID_ENUM:
                return "A GLenum argument is out of range. The command that generated that error is ignored (%s)" % self.code
            elif self.code == GL_INVALID_VALUE:
                return "A numeric argument is out of range. The command that generated that error is ignored (%s)" % self.code
            elif self.code == GL_INVALID_OPERATION:
                return "The specific command cannot be performed in the current state. The command that generated this is ignored (%s)" % self.code
            elif self.code == GL_OUT_OF_MEMORY:
                return "There is insufficient memory to execute this command. The state of the OpenGL ES pipeline is considered to be undefined. All bets are off, basically. (%s)" % self.code
            return "Unknown error code (%s)" % self.code
        else:
            return "No error code given"
                

class EGL(object):

    def __init__(self, pref_width=None, pref_height=None, 
               red_size=8, green_size=8,blue_size=8,
               alpha_size=8, depth_size=None, 
               layer=0, alpha_flags=0, alpha_opacity=0, other_attribs = []):
        """Opens up the OpenGL library and prepares a window for display"""
        b = bcm.bcm_host_init()
        assert b==0
        self.display = openegl.eglGetDisplay(EGL_DEFAULT_DISPLAY)
        assert self.display
        r = openegl.eglInitialize(self.display,0,0)
        assert r
        
        
        attribute_list = [EGL_RED_SIZE, red_size,
                          EGL_GREEN_SIZE, green_size,
                          EGL_BLUE_SIZE, blue_size]
        if alpha_size:
            attribute_list.extend([EGL_ALPHA_SIZE, alpha_size])

        attribute_list.extend([EGL_SURFACE_TYPE, EGL_WINDOW_BIT])
        
        if depth_size:
            attribute_list.extend([EGL_DEPTH_SIZE, depth_size])
        if other_attribs and len(other_attribs) % 2 == 0:
            attribute_list.extend(other_attribs)
        
        attribute_list.append(EGL_NONE)
        attribute_list = eglints( attribute_list )

        numconfig = eglint()
        config = ctypes.c_void_p()
        r = openegl.eglChooseConfig(self.display,
                                     ctypes.byref(attribute_list),
                                     ctypes.byref(config), 1,
                                     ctypes.byref(numconfig));
        assert r
        r = openegl.eglBindAPI(EGL_OPENGL_ES_API)
        assert r
        if verbose:
            print 'numconfig=',numconfig
        context_attribs = eglints( (EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE) )
        self.context = openegl.eglCreateContext(self.display, config,
                                        EGL_NO_CONTEXT,
                                        ctypes.byref(context_attribs))
        assert self.context != EGL_NO_CONTEXT
        width = eglint()
        height = eglint()
        s = bcm.graphics_get_display_size(0,ctypes.byref(width),ctypes.byref(height))
        if pref_width and pref_height:
            self.width = eglint(pref_width)
            self.height = eglint(pref_height)
            width = self.width
            height = self.height
        else:
            self.width = width
            self.height = height
        assert s>=0
        dispman_display = bcm.vc_dispmanx_display_open(0)
        dispman_update = bcm.vc_dispmanx_update_start( 0 )
        dst_rect = eglints( (0,0,width.value,height.value) )
        src_rect = eglints( (0,0,width.value<<16, height.value<<16) )
        assert dispman_update
        assert dispman_display
        alpha_s = Alpha_struct(alpha_flags, alpha_opacity, 0)

        dispman_element = bcm.vc_dispmanx_element_add ( dispman_update, dispman_display,
                                  layer, ctypes.byref(dst_rect), 0,
                                  ctypes.byref(src_rect),
                                  DISPMANX_PROTECTION_NONE,
                                  ctypes.byref(alpha_s) , 0, 0)
        bcm.vc_dispmanx_update_submit_sync( dispman_update )
        nativewindow = eglints((dispman_element,width,height));
        nw_p = ctypes.pointer(nativewindow)
        self.nw_p = nw_p
        self.surface = openegl.eglCreateWindowSurface( self.display, config, nw_p, 0)
        assert self.surface != EGL_NO_SURFACE
        r = openegl.eglMakeCurrent(self.display, self.surface, self.surface, self.context)
        assert r

    def _check_Linked_status(self, programObject):
        # Check the link status
        linked = eglint()
        opengles.glGetProgramiv ( programObject, GL_LINK_STATUS, ctypes.byref(linked))
        try:
            self._check_glerror()
        except GLError, e:
            print e
            return False

        if (linked.value == 0):
            print "Linking failed!"
            loglength = eglint()
            charswritten = eglint()
            opengles.glGetProgramiv(programObject, GL_INFO_LOG_LENGTH, ctypes.byref(loglength))
            logmsg = ctypes.c_char_p(" "*loglength.value)
            opengles.glGetProgramInfoLog(programObject, loglength, ctypes.byref(charswritten), logmsg)
            print logmsg.value
            return False
        return True
    
    def _check_glerror(self):
        e=opengles.glGetError()
        if e:
            raise GLError(e)
        return

    def _show_shader_log(self, shader):
        """Prints the compile log for a shader"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetShaderInfoLog(shader,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value
        
    def _show_program_log(self, program):
        """Prints the compile log for a program"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetProgramInfoLog(program,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value

    def load_shader ( self, shader_src, shader_type = GL_VERTEX_SHADER, quiet = True ):
        # Convert the src to the correct ctype, if not already done
        c_shader_src = shader_src
        if type(shader_src) == basestring or type(shader_src) == str:
            c_shader_src = ctypes.c_char_p(shader_src)

        # Create a shader of the given type
        if not quiet:
            print "Creating shader object"
        shader = opengles.glCreateShader(shader_type)
        opengles.glShaderSource(shader, 1, ctypes.byref(c_shader_src), 0)
        opengles.glCompileShader(shader)
  
        compiled = eglint()

        # Check compiled status
        opengles.glGetShaderiv ( shader, GL_COMPILE_STATUS, ctypes.byref(compiled) )

        if (compiled.value == 0):
            print "Failed to compile shader '%s'" % shader_src 
            loglength = eglint()
            charswritten = eglint()
            opengles.glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(loglength))
            logmsg = ctypes.c_char_p(" "*loglength.value)
            opengles.glGetShaderInfoLog(shader, loglength, ctypes.byref(charswritten), logmsg)
            print logmsg.value
            raise ShaderCompilationFailed(logmsg.value)
        elif not quiet:
            shdtyp = "{unknown}"
            if shader_type == GL_VERTEX_SHADER:
                shdtyp = "GL_VERTEX_SHADER"
            elif shader_type == GL_FRAGMENT_SHADER:
                shdtyp = "GL_FRAGMENT_SHADER"
            print "Compiled %s shader" % (shdtyp)
        if not quiet:
            self._show_shader_log()
        return shader

    def get_program(self, vertex_shader_src, fragment_shader_src, bindings=[], quiet=True):
        # Load the vertex/fragment shaders (can throw a ShaderCompilationFailed exception)
        vertexShader = self.load_shader ( vertex_shader_src, GL_VERTEX_SHADER, quiet )
        fragmentShader = self.load_shader ( fragment_shader_src, GL_FRAGMENT_SHADER, quiet )
        self._check_glerror()

        # Create the program object
        programObject = opengles.glCreateProgram ( )
        self._check_glerror()

        opengles.glAttachShader ( programObject, vertexShader )
        opengles.glAttachShader ( programObject, fragmentShader )
        self._check_glerror()

        # Bind positions to attributes:
        for pos, attrib in bindings:
            opengles.glBindAttribLocation ( programObject, pos, attrib )
        self._check_glerror()

        # Link the program
        opengles.glLinkProgram ( programObject )
        self._check_glerror()

        # Check the link status
        if not (self._check_Linked_status(programObject)):
            print "Couldn't link the shaders to the program object. Check the bindings and shader sourcefiles."
            raise Exception
        if not quiet:
            self._show_program_log(programObject)
        return programObject

