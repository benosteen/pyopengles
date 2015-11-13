from pyopengles import *
import os.path, pyinotify

file_changed = 0

# File watcher for live updates
class FileWatcher(object):
  def __init__(self, file_list):
    self.file_list = set([os.path.abspath(f) for f in file_list])
    self.watch_dirs = set([os.path.dirname(f) for f in self.file_list])
    self.file_changed = 0

  def handler(self, event):
    if event.pathname in self.file_list:
      self.file_changed = 1
      #print "Event: ", event.maskname, ", triggered by: ", event.pathname

  def start(self):
    handler = self.handler
    class EventHandler(pyinotify.ProcessEvent):
      def process_default(self, event):
        handler(event)

    wm = pyinotify.WatchManager()  # Watch Manager

    mask = pyinotify.IN_MODIFY

    ev = EventHandler()
    self.notifier = pyinotify.ThreadedNotifier(wm, ev)

    for watch_this in self.watch_dirs:
      wm.add_watch(watch_this, mask, rec=True)

    self.notifier.start()

  def stop(self):
    self.notifier.stop()

_v_src = """attribute vec3 position;
           void main() {
              gl_Position = vec4( position, 1.0 );
           }"""

example_frag = """precision mediump float;
uniform float time_ms;
uniform vec2 mouse;
uniform vec2 resolution;

void main( void ) {
	float mouse_charge = 10.;
	vec3 charges[10];
	charges[0] = vec3(0,0,10);
	charges[1] = vec3(0.1,0.1,-10);
	const int N = 2;	
	vec2 position = gl_FragCoord.xy / resolution.xy - resolution.xy/2.0;
	position.x = (gl_FragCoord.x - resolution.x/2.0)/resolution.x;
	position.y = (gl_FragCoord.y - resolution.y/2.0)/resolution.x;
	float r = distance(position.xy,vec2(mouse.x - 0.5, (mouse.y - 0.5)*resolution.y/resolution.x));
	float s = mouse_charge/(r*r);
	for(int i=0; i < N; i++){
		r = distance(position.xy,charges[i].xy);
		s += charges[i].z / (r*r);
	}
	gl_FragColor = vec4(fract(-log(s)*10.),fract(-log(s)*1.),fract(-log(s)/10.),1.);
}"""

# fullscreen, alpha fixed for all pixels, PREMULT flag on
e = EGL(alpha_flags=1+1<<16, alpha_opacity=128)
#e=EGL(pref_width = 640, pref_height=480)

surface_tris = eglfloats( (  - 1.0, - 1.0, 1.0, 
                             - 1.0, 1.0, 1.0, 
                               1.0, 1.0, 1.0, 
                             - 1.0, - 1.0, 1.0, 
                               1.0, 1.0, 1.0, 
                             1.0, - 1.0, 1.0 ) ) # 2 tris

def draw(programObject,time_ms, m, r, Vbo):
  opengles.glClear ( GL_COLOR_BUFFER_BIT )

  location = opengles.glGetUniformLocation(programObject, "time")
  opengles.glUniform1f(location, eglfloat(time_ms))
  try:
    e._check_glerror()
  except GLError, error:
    print "Error setting time uniform var"
    print error

  location = opengles.glGetUniformLocation(programObject, "mouse")
  opengles.glUniform2f(location, eglfloat(float(m.x) / r[0].value), eglfloat(float(m.y) / r[1].value))
  try:
    e._check_glerror()
  except GLError, error:
    print "Error setting mouse uniform var"
    print error

  location = opengles.glGetUniformLocation(programObject, "resolution")
  opengles.glUniform2f(location, r[0], r[1])
  try:
    e._check_glerror()
  except GLError, error:
    print "Error setting resolution uniform var"
    print error

  opengles.glBindBuffer(GL_ARRAY_BUFFER, Vbo)

  opengles.glEnableVertexAttribArray(0);
  
  opengles.glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*4, 0)
  
  # Draws a non-indexed triangle array
  opengles.glDrawArrays ( GL_TRIANGLE_STRIP, 0, 6 )  # 2 tris
  opengles.glBindBuffer(GL_ARRAY_BUFFER, 0)
  e._check_glerror()

  openegl.eglSwapBuffers(e.display, e.surface)
  time.sleep(0.02)
  

def run_shader(frag_shader):
  try:
    try:
      m = start_mouse()
    except Exception, err:
      print err
      class FakeM():
        def __init__(self, x,y):
          self.x = x
          self.y = y
          self.finished = False
      m = FakeM(400,300)

    _v_src = """attribute vec3 position;
           void main() {
              gl_Position = vec4( position, 1.0 );
           }"""

    vertexShader = e.load_shader(_v_src, GL_VERTEX_SHADER )
    fragmentShader = e.load_shader(frag_shader, GL_FRAGMENT_SHADER)
    # Create the program object
    programObject = opengles.glCreateProgram ( )

    opengles.glAttachShader ( programObject, vertexShader )
    opengles.glAttachShader ( programObject, fragmentShader )
    e._check_glerror()

    opengles.glBindAttribLocation ( programObject, 0, "position" )
    e._check_glerror()

    # Link the program
    opengles.glLinkProgram ( programObject )
    e._check_glerror()

    # Check the link status
    if not (e._check_Linked_status(programObject)):
      print "Couldn't link the shaders to the program object. Check the bindings and shader sourcefiles."
      raise Exception
   
    opengles.glClearColor ( eglfloat(0.3), eglfloat(0.3), eglfloat(0.5), eglfloat(1.0) )
    e._check_glerror()

    opengles.glUseProgram( programObject )
    e._check_glerror()

    # Make a VBO buffer obj
    Vbo = eglint()

    opengles.glGenBuffers(1, ctypes.byref(Vbo))
    e._check_glerror()
  
    opengles.glBindBuffer(GL_ARRAY_BUFFER, Vbo)
    e._check_glerror()

    # Set the buffer's data
    opengles.glBufferData(GL_ARRAY_BUFFER, 4 * 6 * 3, surface_tris, GL_STATIC_DRAW)
    e._check_glerror()
  
    # Unbind the VBO
    opengles.glBindBuffer(GL_ARRAY_BUFFER, 0)
    e._check_glerror()

    # render loop
    start = time.time()
    r = (eglfloat(e.width.value), eglfloat(e.height.value))
    while(1):
      draw(programObject, (time.time() - start), m, r, Vbo)
      time.sleep(0.02)
      if fw.file_changed:
        break
    del programObject, vertexShader, fragmentShader
  except KeyboardInterrupt:
    print "Finishing"
    m.finished = True
    opengles.glClearColor ( eglfloat(0.0), eglfloat(0.0), eglfloat(0.0), eglfloat(0.0) )
    opengles.glClear ( GL_COLOR_BUFFER_BIT )
    openegl.eglSwapBuffers(e.display, e.surface)
    return
  except Exception, error:
    print "Error - finishing"
    opengles.glClearColor ( eglfloat(0.0), eglfloat(0.0), eglfloat(0.0), eglfloat(0.0) )
    opengles.glClear ( GL_COLOR_BUFFER_BIT )
    openegl.eglSwapBuffers(e.display, e.surface)
    m.finished = True
    raise error
    
if __name__ == "__main__":
  import sys
  if len(sys.argv) == 2:
    fw=FileWatcher([sys.argv[1]])
    fw.start()
    try:
      while(True):
        fw.file_changed=0
        glsl_file = open(sys.argv[1], "r")
        frag = glsl_file.read()
        glsl_file.close()
        try:
          run_shader(frag)
        except:
          time.sleep(3)
    except IOError:
      print "No such file"
  fw.stop()


