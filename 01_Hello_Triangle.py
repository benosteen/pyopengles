#!/usr/bin/env python

from pyopengles import *

ctx = EGL()

vertex_shader = """
    attribute vec4 vPosition;

    void main()
    {
        gl_Position = vPosition;
    }
"""

fragment_shader = """
    precision mediump float;

    void main()
    {
        gl_FragColor = vec4 ( 1.0, 0.0, 0.0, 1.0 );
    }
"""

binding = ((0, 'vPosition'),)

program = ctx.get_program(vertex_shader, fragment_shader, binding)

opengles.glClearColor(eglfloat(0.1), eglfloat(0.1), eglfloat(0.1),eglfloat(1.0))

triangle_vertices = eglfloats(( -0.866, -0.5, 1.0,
                                 0.0,  1.0, 1.0,
                                 0.866, -0.5, 1.0 ))

# Clear the color buffer
opengles.glClear ( GL_COLOR_BUFFER_BIT )

# Set the Viewport: (NB openegl, not opengles)
opengles.glViewport(0,0,ctx.width, ctx.height)

# Use the program object
opengles.glUseProgram ( program )

# Load the vertex data
opengles.glVertexAttribPointer ( 0, 3, GL_FLOAT, GL_FALSE, 0, triangle_vertices )
opengles.glEnableVertexAttribArray ( 0 )

opengles.glDrawArrays ( GL_TRIANGLES, 0, 3 )
openegl.eglSwapBuffers(ctx.display, ctx.surface)

time.sleep(5)

