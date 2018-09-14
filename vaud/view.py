from gi.repository import Gtk

def draw_cb(widget, cr):
  cr.set_source_rgba(0,0,0,0.5)
  cr.rectangle(50,75,100,100)
  cr.fill()
  return False

class PyApp(Gtk.Window):
    def __init__(self):
        super(PyApp, self).__init__()

        self.set_title("test")
        self.set_default_size(800,600)
        self.connect('delete-event', Gtk.main_quit)
        self.da=Gtk.DrawingArea()
        self.da.connect('draw', draw_cb)
        self.add(self.da)
        self.show_all()
    
    def expose(self):
        pass

PyApp()
Gtk.main()