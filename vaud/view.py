from gi.repository import Gtk
import cairo
import math

#color constants
NODE_COLOR = (0.407, 0.427, 0.650)
EDGE_COLOR = (0.709, 0.717, 0.788) #(0.090, 0.101, 0.250)
CLIQUE_GROUPING_COLOR = (0.760, 0.760, 0.760)
TEXT_COLOR = (0.858, 0.858, 0.858) # (0.121, 0.121, 0.121)
CONNECTION_LINES_COLOR = (0.368, 0.368, 0.368)
BACKGROUND_COLOR =  (0.090, 0.090, 0.090) #(0.858, 0.858, 0.858)

#font constants
ID_TEXT_FONT = "Georgia"

#positioning constants
RELATIVE_DISTANCE_NODES_HORIZONTAL = 3 #how many nodes should fit between two nodes horizontally
RELATIVE_DISTANCE_NODES_VERTICAL = 4 #how many nodes should fit between two nodes vertically

RELATIVE_TEXT_WIDTH_TO_SCREEN = 1/15.0 #defines the width of the longest text on the left side
RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT = 0.2 #defines the empty space width left and right to the left column text relative to that text

RELATIVE_WIDTH_OF_ID_TEXTS = 1.5 #defines how wide the id texts are in relation to the size of a node
RELATIVE_OFFSET_OF_ID_TEXTS = 0.5 #defines how far below the id text will be placed below a node in relation to the size of a node

RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE = 2.0 # defines the height of the rs layer as defined on S.167 relative to the node size. Unlike the slide, in this representation all rs layers will be quidistant in the same i layer
RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE = 4.0 #defines the distance between the i layers as defined on S.167 relative to the node size.

class DrawElements:

    def __init__(self, screenWidth, screenHeight):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight


    def drawSkipPlusGraph(self) -> None:
        # get the screen size
        # get id length
        self.idLength = 4
        # get amount of nodes
        self.amountNodes = int(math.pow(2,self.idLength))
        # calculate sizes for individual elements
        # how large is a node
        self.nodeSize = (self.screenWidth - ((4*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +2) *RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth)) / (self.amountNodes + ((self.amountNodes -1) * RELATIVE_DISTANCE_NODES_HORIZONTAL))
        print("self.nodeSize: " + str(self.nodeSize))
        # how tall is an rs layer
        self.rsLayerDistance = RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE*self.nodeSize
        # what's the distance between the two i layers
        self.iLayerDistance = RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE*self.nodeSize
        # how thick is an edge
        # how thick is the vertical dotted connection line
        # how large is a clique grouping
        # how large is a level marking
        self.levelMarkingMaxWidth = RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth
        self.sideWidth = (2*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +1)*self.levelMarkingMaxWidth
        #print("levelMarkingMaxWidth is " + str(self.levelMarkingMaxWidth))
        #print("sideWidth is " + str(self.sideWidth))
        # how large is the id text - currently using a BAD solution
        self.widthOfIdText = RELATIVE_WIDTH_OF_ID_TEXTS*self.nodeSize
        
        self.cr.select_font_face(ID_TEXT_FONT)
        #set the font size to a huge value
        self.cr.set_font_size(10000)
        # get the extents if the font was scaled by 10000
        x_bearing, y_bearing, width, height = [x*self.idLength for x in self.cr.text_extents("0")][:4]
        # calculate scale factor
        scaleFactor : float = self.widthOfIdText/width
        newFontSize = 10000*scaleFactor
        print("newFontSize: " + str(newFontSize))
        #set new font size to achieve accurate width
        self.cr.set_font_size(newFontSize)


        #paint background color
        self.cr.set_source_rgb(*BACKGROUND_COLOR)
        self.cr.paint()

        #place elements on canvas
        # place vertical connection lines
        # place clique groupings
        # place edges
        # place nodes and id texts
        for x in range(self.amountNodes): #iterate over the horizontal nodes    
            xPos = self.sideWidth+ (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize * x
            yPos = 0
            text = '{0:b}'.format(x).zfill(self.idLength)
            for i in range(self.idLength):  #iterate over the i layers
                yPos = yPos + self.iLayerDistance
                for rs in range(int(math.pow(2,i+1))):  #iterate over the i layers
                    #(RELATIVE_DISTANCE_NODES_VERTICAL+1)*self.nodeSize * (self.idLength-i)
                    #set color
                    self.cr.set_source_rgb(*NODE_COLOR)
                    #place single node
                    #print("place on " + str(xPos) + " " + str(yPos))
                    self.cr.arc(xPos, yPos, self.nodeSize/2.0, 0, 2 * math.pi)
                    self.cr.fill()
                    #calculate position of the id text
                    yPosText = yPos+ ((RELATIVE_OFFSET_OF_ID_TEXTS+0.5)*self.nodeSize)
                    #set color
                    self.cr.set_source_rgb(*TEXT_COLOR)
                    #place single id text
                    x_bearing, y_bearing, width, height = self.cr.text_extents(text)[:4]
                    self.cr.move_to(xPos - width / 2 - x_bearing, yPosText - height / 2 - y_bearing)
                    self.cr.show_text(text)

                    yPos = yPos + self.rsLayerDistance

        # place level markings


    def draw_cb(self, widget, cr):

        self.cr = cr
        self.widget = widget
        
        '''
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
        '''

        self.drawSkipPlusGraph()

        return False




class PyApp(Gtk.Window):
    def __init__(self):
        super(PyApp, self).__init__()

        self.window = Gtk.Window()
        self.screen = self.window.get_screen()
        # Using the screen of the Window, the monitor it's on can be identified
        self.m = self.screen.get_monitor_at_window(self.screen.get_active_window())
        # Then get the geometry of that monitor
        self.monitor = self.screen.get_monitor_geometry(self.m)
        # This is an example output
        print("Height: %s, Width: %s" % (self.monitor.height, self.monitor.width))
        self.screenWidth = self.monitor.width
        self.screenHeight = self.monitor.height
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