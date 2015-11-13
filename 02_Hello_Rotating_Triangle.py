#!/usr/bin/env python

from pyopengles import *

#Boilerplate code to allow for non-blocking reading the stdin
import termios, fcntl, sys, os, select

fd = sys.stdin.fileno()

oldterm = termios.tcgetattr(fd)
newattr = oldterm[:]
newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, newattr)

oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

ctx = EGL()

vertex_shader = """
    attribute vec4 vPosition;
    
    uniform float rotation;
    
    mat4 rotate_z(float theta)
    {
    return mat4(
        vec4( cos(theta),  sin(theta),  0.0, 0.0),
        vec4(-sin(theta),  cos(theta),  0.0, 0.0),
        vec4(        0.0,         0.0,  1.0, 0.0),
        vec4(        0.0,         0.0,  0.0, 1.0)
        );
    }

    void main()
    {
        gl_Position = rotate_z(rotation) * vPosition;
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

# Use the program object
opengles.glUseProgram ( program )

# Set the Viewport: (NB openegl, not opengles)
opengles.glViewport(0,0,ctx.width, ctx.height)

# Find the location of the 'uniform' rotation:
rot_loc = opengles.glGetUniformLocation(program, "rotation")

rotation = 0.0

print "Controls: \nm - Rotate clockwise, \nn - rotate counter-clockwise, \nq - Quit\n\nStarts in 3 seconds..."

time.sleep(3)

try:
    running = True
    while(running):
        # Clear the color buffer
        opengles.glClear ( GL_COLOR_BUFFER_BIT )

        # Update then draw:
        # is there a keypress to read?
        r, w, e = select.select([fd], [], [], 0.02)
        if r:
            c = sys.stdin.read(1)
            if c.lower() == "m":
                rotation -= 0.05
            elif c.lower() == "n":
                rotation += 0.05
            elif c.lower() == "q":
                # quit
                running = False

        # set rotation:
        opengles.glUniform1f(rot_loc, eglfloat(rotation))

        # Load the vertex data
        opengles.glVertexAttribPointer ( 0, 3, GL_FLOAT, GL_FALSE, 0, triangle_vertices )
        opengles.glEnableVertexAttribArray ( 0 )

        opengles.glDrawArrays ( GL_TRIANGLES, 0, 3 )
        openegl.eglSwapBuffers(ctx.display, ctx.surface)
finally:
    termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


