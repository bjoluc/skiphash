from gi.repository import Gtk
import cairo
import math

#color constants
NODE_COLOR = (0.407, 0.427, 0.650)
EDGE_COLOR = (0.090, 0.101, 0.250)
CLIQUE_GROUPING_COLOR = (0.760, 0.760, 0.760)
TEXT_COLOR = (0.121, 0.121, 0.121)
CONNECTION_LINES_COLOR = (0.368, 0.368, 0.368)

#positioning constants
RELATIVE_DISTANCE_NODES_HORIZONTAL = 3 #how many nodes should fit between two nodes horizontally
RELATIVE_DISTANCE_NODES_VERTICAL = 4 #how many nodes should fit between two nodes vertically

RELATIVE_TEXT_WIDTH_TO_SCREEN = 1/4.0 #defines the width of the longest text on the left side
RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT = 0.0 #defines the empty space width left and right to the left column text relative to that text


class DrawElements:

    def __init__(self, screenWidth, screenHeight):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight


    def drawSkipPlusGraph(self) -> None:
        # get the screen size
        # get amount of nodes
        self.amountNodes = 10
        # get id length
        self.idLength = 1
        # calculate sizes for individual elements
        # how large is a node
        self.nodeSize = (self.screenWidth - ((4*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +2) *RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth)) / (self.amountNodes + ((self.amountNodes -1) * RELATIVE_DISTANCE_NODES_HORIZONTAL))

        print("self.nodeSize: " + str(self.nodeSize))
        # how thick is an edge
        # how thick is the vertical dotted connection line
        # how large is a clique grouping
        # how large is a level marking
        self.levelMarkingMaxWidth = RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth
        self.sideWidth = (2*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +1)*self.levelMarkingMaxWidth
        print("levelMarkingMaxWidth is " + str(self.levelMarkingMaxWidth))
        print("sideWidth is " + str(self.sideWidth))
        # how large is the id text

        #place elements on canvas
        # place vertical connection lines
        # place clique groupings
        # place edges
        # place nodes

        self.cr.set_source_rgb(*NODE_COLOR)
        for x in range(self.amountNodes):            
            for y in range(self.idLength):
                #calculate position
                xPos = self.sideWidth+ (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize * x
                yPos = (RELATIVE_DISTANCE_NODES_VERTICAL+1)*self.nodeSize * (self.idLength-y)
                #place single node
                print("place on " + str(xPos) + " " + str(yPos))
                self.cr.arc(xPos, yPos, self.nodeSize/2.0, 0, 2 * math.pi)
                self.cr.fill()
        # place level markings
        # place id texts


    def draw_cb(self, widget, cr):

        self.cr = cr
        self.widget = widget
        
        #paint whole canvas
        self.cr.set_source_rgb(0.5, 0.3, 0.0)
        self.cr.paint_with_alpha(0.5)

        #draw gradients with gradient mask
        linear = cairo.LinearGradient(0, 0, 400, 400)
        linear.add_color_stop_rgb(0, 0, 0.3, 0.8)
        linear.add_color_stop_rgb(1, 0, 0.8, 0.3)

        radial = cairo.RadialGradient(400, 400, 300, 470, 400, 400)
        radial.add_color_stop_rgba(0, 0, 0, 0, 1)
        radial.add_color_stop_rgba(0.5, 0, 0, 0, 0)

        self.cr.set_source(linear)
        self.cr.mask(radial)

        # draw rectangle
        self.cr.set_source_rgba(0,0,0,0.5)
        self.cr.rectangle(50,75,100,100)
        self.cr.fill()

        # draw rectangle outline
        self.cr.set_line_width(0.5)
        self.cr.set_source_rgb(0, 0, 0)
        self.cr.rectangle(250, 250, 50, 75)
        self.cr.stroke()

        #draw text
        self.cr.set_source_rgb(0.0, 0.0, 0.0)
        self.cr.select_font_face("Georgia")
        self.cr.set_font_size(30)
        x_bearing, y_bearing, width, height = self.cr.text_extents("NodeId = 1010010")[:4]
        self.cr.move_to(300 - width / 2 - x_bearing, 300 - height / 2 - y_bearing)
        self.cr.show_text("NodeId = 1010010")

        self.drawSkipPlusGraph()

        return False




class PyApp(Gtk.Window):
    def __init__(self):
        super(PyApp, self).__init__()
        # get screen size
        #self.display = Gtk.gdk_display_get_default()
        #.gdk_display_get_monitor
        #self.monitor = Gtk.gdk_display_get_monitor(display, 0)

        self.window = Gtk.Window()
        self.screen = self.window.get_screen()
        print (str(self.screen.get_width()) + " " + str(self.screen.get_height()))
        self.screenWidth = self.screen.get_width()
        self.screenHeight = self.screen.get_height()
        self.set_title("Skip+ Graph")
        self.set_default_size(self.screenWidth,self.screenHeight)
        self.connect('delete-event', Gtk.main_quit)
        self.da=Gtk.DrawingArea()

        drawElements = DrawElements(self.screenWidth, self.screenHeight)
        self.da.connect('draw', drawElements.draw_cb)
        self.add(self.da)
        self.show_all()
    
    def expose(self):
        pass


PyApp()
Gtk.main()