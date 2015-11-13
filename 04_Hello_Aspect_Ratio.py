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
    uniform vec3 move;
    uniform vec3 rescale;

    mat4 translate(float x, float y, float z)
    {
    return mat4(
        vec4(1.0, 0.0, 0.0, 0.0),
        vec4(0.0, 1.0, 0.0, 0.0),
        vec4(0.0, 0.0, 1.0, 0.0),
        vec4(x,   y,   z,   1.0)
        );
    }
    
    mat4 rotate_z(float theta)
    {
    return mat4(
        vec4( cos(theta),  sin(theta),  0.0, 0.0),
        vec4(-sin(theta),  cos(theta),  0.0, 0.0),
        vec4(        0.0,         0.0,  1.0, 0.0),
        vec4(        0.0,         0.0,  0.0, 1.0)
        );
    }

    mat4 scale(float x, float y, float z)
    {
    return mat4(
        vec4(   x, 0.0, 0.0, 0.0),
        vec4( 0.0,   y, 0.0, 0.0),
        vec4( 0.0, 0.0,   z, 0.0),
        vec4( 0.0, 0.0, 0.0, 1.0)
        );
    }
    void main()
    {
        gl_Position = scale(rescale.x, rescale.y, rescale.z)
                      * translate(move.x, move.y, move.z)
                      * rotate_z(rotation)
                      * vPosition;
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
move_loc = opengles.glGetUniformLocation(program, "move")
rescale_loc = opengles.glGetUniformLocation(program, "rescale")

rotation = 0.0
move = [0.0, 0.0, 0.0]

# Adjust the scaling to match the display's aspect ratio:
rescale = [0.5, 0.5*ctx.width.value / float(ctx.height.value), 0.5]

print "Controls: \nm - Rotate clockwise, n - rotate counter-clockwise, \n"
print "Movement: a - left,  d - right,  w - up, s - down\n\nq - Quit\n\nStarts in 3 seconds..."

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
                # rotate
                rotation -= 0.05
            elif c.lower() == "n": 
                # rotate
                rotation += 0.05
            elif c.lower() == "a":
                # move left
                move[0] = move[0] - 0.1
            elif c.lower() == "d":
                # move right
                move[0] = move[0] + 0.1
            elif c.lower() == "s":
                # move down
                move[1] -= 0.1
            elif c.lower() == "w":
                # move up
                move[1] += 0.1
            elif c.lower() == "q":
                # quit
                running = False

        # sets the rescale
        opengles.glUniform3f(rescale_loc, eglfloat( rescale[0] ), eglfloat( rescale[1]), eglfloat(rescale[2]))

        # set rotation:
        opengles.glUniform1f(rot_loc, eglfloat(rotation))

        # set translation
        opengles.glUniform3f(move_loc, eglfloat( move[0] ), eglfloat(move[1]), eglfloat(move[2]))

        # Load the vertex data
        opengles.glVertexAttribPointer ( 0, 3, GL_FLOAT, GL_FALSE, 0, triangle_vertices )
        opengles.glEnableVertexAttribArray ( 0 )

        opengles.glDrawArrays ( GL_TRIANGLES, 0, 3 )
        openegl.eglSwapBuffers(ctx.display, ctx.surface)
finally:
    termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


