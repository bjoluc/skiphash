import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import cairo, math, random

#color constants
NODE_COLOR_EVEN_RS = (0.266, 0.623, 0.835) #(0.407, 0.427, 0.650)
NODE_COLOR_ODD_RS = (0.678, 0.729, 0.760) #(0.407, 0.427, 0.650)
EDGE_DIAGONAL_COLOR = (0.423, 0.278, 0.341) #(0.090, 0.101, 0.250)
EDGE_HORIZONTAL_COLOR = (0.772, 0.125, 0.415) #(0.090, 0.101, 0.250)
CLIQUE_GROUPING_COLOR = (0.250, 0.250, 0.250)
TEXT_COLOR = (0.858, 0.858, 0.858) # (0.121, 0.121, 0.121)
CONNECTION_LINES_COLOR = (0.368, 0.368, 0.368)
BACKGROUND_COLOR =  (0.090, 0.090, 0.090) #(0.858, 0.858, 0.858)

#font constants
ID_TEXT_FONT = "Georgia"
LAYER_TEXT_FONT = "Georgia"

#positioning and size constants
RELATIVE_DISTANCE_NODES_HORIZONTAL = 3 #how many nodes should fit between two nodes horizontally
RELATIVE_MINIMUM_NODE_SIZE = 0.013 #defines how large a node must be at the minimum relative to the screen width

RELATIVE_TEXT_WIDTH_TO_SCREEN = 1/15.0 #defines the width of the longest text on the left side
RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT = 0.5 #defines the empty space width left and right to the left column text relative to that text

RELATIVE_WIDTH_OF_ID_TEXTS = 1.5 #defines how wide the id texts are in relation to the size of a node
RELATIVE_OFFSET_OF_ID_TEXTS = 0.5 #defines how far below the id text will be placed below a node in relation to the size of a node

RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE = 3.4 # defines the height of the rs layer as defined on S.167 relative to the node size. Unlike the slide, in this representation all rs layers will be quidistant in the same i layer
RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE = 4.0 #defines the distance between the i layers as defined on S.167 relative to the node size.

RELATIVE_CLIQUE_DISTANCE_SIDE = 0.85 #defines the distance from the side end of the node to the sides of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_ABOVE = 0.3 #defines the distance from the upper end of the node to the upper side of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_BELOW = 1.0 #defines the distance from the lower end of the node to the lower side of the clique grouping relative to the node size
RELATIVE_CORNER_RADIUS_OF_CLIQUES_TO_HEIGHT = 0.2 #defines the corner radius of the clique groupings relative to their height

RELATIVE_HORIZONTAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.3 #defines how thick an horizontal edge is relative to the node size
RELATIVE_DIAGONAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.2 #defines how thick an diagonal edge is relative to the node size

class DrawElements:

    def __init__(self, screenWidth, screenHeight):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight

    def calculateSizes(self) ->None:
        # how large is a node
        self.nodeSize = (self.screenWidth - ((4*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +2) *RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth)) / (self.amountNodes + ((self.amountNodes -1) * RELATIVE_DISTANCE_NODES_HORIZONTAL))
        self.nodeSize = max(RELATIVE_MINIMUM_NODE_SIZE*self.screenWidth, self.nodeSize)
        print("self.nodeSize: " + str(self.nodeSize))
        # how wide is the horizontal distance between nodes
        self.distanceNodesHorizontal = (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize
        # how tall is an rs layer
        self.rsLayerDistance = RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE*self.nodeSize
        # what's the distance between the two i layers
        self.iLayerDistance = RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE*self.nodeSize
        # how thick is an edge
        self.horizontalEdgeThickness = RELATIVE_HORIZONTAL_EDGE_THICKNESS_TO_NODE_SIZE*self.nodeSize
        self.diagonalEdgeThickness = RELATIVE_DIAGONAL_EDGE_THICKNESS_TO_NODE_SIZE*self.nodeSize
        # how thick is the vertical dotted connection line
        # how large is a clique grouping
        self.cliqueDistanceSide = RELATIVE_CLIQUE_DISTANCE_SIDE*self.nodeSize
        self.cliqueDistanceAbove = RELATIVE_CLIQUE_DISTANCE_ABOVE*self.nodeSize
        self.cliqueDistanceBelow = RELATIVE_CLIQUE_DISTANCE_BELOW*self.nodeSize
        #print("cliqueDistanceAbove: " + str(self.cliqueDistanceAbove))
        # how large is a level marking - currently using a BAD solution
        self.levelMarkingMaxWidth = RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth
        self.sideWidth = (2*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +1)*self.levelMarkingMaxWidth
        self.levelTextFontSize = self.calculateFontSizeToFitWidth(LAYER_TEXT_FONT, self.levelMarkingMaxWidth, self.idLength+6) #there are 6 additional characters: rs=...  
        #print("levelMarkingMaxWidth is " + str(self.levelMarkingMaxWidth))
        #print("sideWidth is " + str(self.sideWidth))
        # how large is the id text - currently using a BAD solution
        self.widthOfIdText = RELATIVE_WIDTH_OF_ID_TEXTS*self.nodeSize  
        self.idTextFontSize = self.calculateFontSizeToFitWidth(ID_TEXT_FONT, self.widthOfIdText, self.idLength)  
        # calculate the canvas width and height
        self.canvasWidth = self.sideWidth*2 + ((self.amountNodes-1)*self.distanceNodesHorizontal) + self.nodeSize
        print("self.canvasWidth " + str(self.canvasWidth))
        self.canvasHeight = self.calculateVerticalPositionOfNode(self.idLength-1, int(math.pow(2,self.idLength)))
        print("self.canvasHeight " + str(self.canvasHeight))
        

    def calculateFontSizeToFitWidth (self, fontface: str, allowedWidth: float, maxTextLength: int) -> int:
        self.cr.select_font_face(fontface)
        #set the font size to a huge value
        self.cr.set_font_size(10000)
        # get the extents if the font was scaled by 10000
        x_bearing, y_bearing, width, height = (self.cr.text_extents("0"*maxTextLength))[:4]
        # calculate scale factor
        scaleFactor : float = allowedWidth/width
        newFontSize = 10000*scaleFactor

        return newFontSize


    def calculateVerticalPositionOfNode(self, iLayer: int, rsLayer: int) -> float:
        return (self.iLayerDistance*(iLayer+1)) + (self.rsLayerDistance*(math.pow(2,iLayer+1)-2+rsLayer))
        ''' ORIGINAL OBSOLETE CALCULATION
        for i in range(self.idLength):  #iterate over the i layers
            yPos = yPos + self.iLayerDistance
            for rs in range(int(math.pow(2,i+1))):  #iterate over the i layers
                if i==iLayer and rs==rsLayer:

                    print("for iLayer " + str(iLayer) + " and rsLayer " + str(rsLayer) + " it's " + str(yPos))
                    x1Pos = self.sideWidth+ (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize * node1XPos
                    x2Pos = self.sideWidth+ (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize * node2XPos
                    upperLeftX = x1Pos-self.cliqueDistanceSide -(0.5*self.nodeSize)
                    upperLeftY = yPos-self.cliqueDistanceAbove -(0.5*self.nodeSize)
                    lowerRightX = x2Pos+self.cliqueDistanceSide +(0.5*self.nodeSize)
                    lowerRightY = yPos+self.cliqueDistanceBelow +(0.5*self.nodeSize)

                    self.draw_rounded(upperLeftX, upperLeftY, lowerRightX, lowerRightY)
                    #self.draw_rounded(500, 1500, 1700, 1700)

                yPos = yPos + self.rsLayerDistance
        '''

    def calculateHorizontalPositionOfNode (self, nodeXPos) ->float:
        return self.sideWidth+ self.distanceNodesHorizontal * nodeXPos

    def draw_rounded(self, upperLeftX: float, upperLeftY: float, lowerRightX: float, lowerRightY: float):
        """ draws rectangles with rounded (circular arc) corners """
        aspect = 1.0
        cornerRadius = (lowerRightY-upperLeftY)*RELATIVE_CORNER_RADIUS_OF_CLIQUES_TO_HEIGHT
        radius = cornerRadius/aspect
        degrees = math.pi / 180

        self.cr.arc(lowerRightX - radius, upperLeftY + radius, radius, -90 * degrees, 0 * degrees)
        self.cr.arc(lowerRightX - radius, lowerRightY - radius, radius, 0 * degrees, 90 * degrees)
        self.cr.arc(upperLeftX + radius, lowerRightY - radius, radius, 90 * degrees, 180 * degrees) 
        self.cr.arc(upperLeftX + radius, upperLeftY + radius, radius, 180 * degrees, 270 * degrees)

        self.cr.close_path()
        self.cr.fill()

    def drawCliqueGrouping(self, node1XPos: int, node2XPos: int, iLayer: int, rsLayer: int) -> None:
        #set color
        self.cr.set_source_rgb(*CLIQUE_GROUPING_COLOR)
        yPos = self.calculateVerticalPositionOfNode(iLayer, rsLayer)
        #print("for iLayer " + str(iLayer) + " and rsLayer " + str(rsLayer) + " it's " + str(yPos))
        x1Pos = self.calculateHorizontalPositionOfNode(node1XPos)
        x2Pos = self.calculateHorizontalPositionOfNode(node2XPos)
        upperLeftX = x1Pos-self.cliqueDistanceSide -(0.5*self.nodeSize)
        upperLeftY = yPos-self.cliqueDistanceAbove -(0.5*self.nodeSize)
        lowerRightX = x2Pos+self.cliqueDistanceSide +(0.5*self.nodeSize)
        lowerRightY = yPos+self.cliqueDistanceBelow +(0.5*self.nodeSize)

        self.draw_rounded(upperLeftX, upperLeftY, lowerRightX, lowerRightY)
        
    def drawHorizontalEdge(self, node1XPos: int, node2XPos: int, iLayer: int, rsLayer: int) -> None:
        #set color
        self.cr.set_source_rgb(*EDGE_HORIZONTAL_COLOR)
        #set line thickness
        self.cr.set_line_width (self.horizontalEdgeThickness)
        x1Pos = self.calculateHorizontalPositionOfNode(node1XPos)
        x2Pos = self.calculateHorizontalPositionOfNode(node2XPos)
        yPos = self.calculateVerticalPositionOfNode(iLayer, rsLayer)

        self.cr.move_to(x1Pos,yPos)
        self.cr.line_to(x2Pos,yPos)
        self.cr.stroke()


    def drawDiagonalEdge(self, node1XPos: int, node2XPos: int, iLayerLower: int, iLayerUpper: int, rsLayerLower: int, rsLayerUpper: int) -> None:
        #set color
        self.cr.set_source_rgb(*EDGE_DIAGONAL_COLOR)
        #set line thickness
        self.cr.set_line_width (self.diagonalEdgeThickness)
        
        x1Pos = self.calculateHorizontalPositionOfNode(node1XPos)
        x2Pos = self.calculateHorizontalPositionOfNode(node2XPos)
        y1Pos = self.calculateVerticalPositionOfNode(iLayerLower, rsLayerLower)
        y2Pos = self.calculateVerticalPositionOfNode(iLayerUpper, rsLayerUpper)

        self.cr.move_to(x1Pos,y1Pos)
        self.cr.line_to(x2Pos,y2Pos)
        self.cr.stroke()

    def drawNodeAndIdText(self, nodeXPos: int, iLayer: int, rsLayer: int, idText: str) -> None:
        #calculate position for node
        xPos = self.calculateHorizontalPositionOfNode(nodeXPos)
        yPos = self.calculateVerticalPositionOfNode(iLayer, rsLayer)
        #set color for node
        if rsLayer%2 == 0:
            self.cr.set_source_rgb(*NODE_COLOR_EVEN_RS)
        else:
            self.cr.set_source_rgb(*NODE_COLOR_ODD_RS)
        #place single node
        #print("place on " + str(xPos) + " " + str(yPos))
        self.cr.arc(xPos, yPos, self.nodeSize/2.0, 0, 2 * math.pi)
        self.cr.fill()
        #calculate position of the id text
        yPosText = yPos+ ((RELATIVE_OFFSET_OF_ID_TEXTS+0.5)*self.nodeSize)
        #set color for text
        self.cr.set_source_rgb(*TEXT_COLOR)
        #set font face
        self.cr.set_font_size(self.idTextFontSize)
        #place single id text
        x_bearing, y_bearing, width, height = self.cr.text_extents(idText)[:4]
        self.cr.move_to(xPos - width / 2 - x_bearing, yPosText - height / 2 - y_bearing)
        self.cr.show_text(idText)

    def drawLayerMarkings(self) ->None:
        yPos = 0
        #set color
        self.cr.set_source_rgb(*TEXT_COLOR)
        #set correct font size
        self.cr.set_font_size(self.levelTextFontSize)
        for i in range(self.idLength):  #iterate over the i layers
            yPos = yPos + self.iLayerDistance
            #calculate position of the i label
            xPos = self.canvasWidth - (self.sideWidth/2.0)
            #set correct text
            text = "i=" +  str(i)
            #place i label
            x_bearing, y_bearing, width, height = self.cr.text_extents(text)[:4]
            self.cr.move_to(xPos - width / 2 - x_bearing, yPos - height / 2 - y_bearing)
            self.cr.show_text(text)

            for rs in range(int(math.pow(2,i+1))):  #iterate over the i layers
                #calculate position of the rs label
                xPos = self.sideWidth/2.0
                #set correct text
                text = "rs=" +  '{0:b}'.format(rs).zfill(i+1) + "..."
                #place rs label
                x_bearing, y_bearing, width, height = self.cr.text_extents(text)[:4]
                self.cr.move_to(xPos - width / 2 - x_bearing, yPos - height / 2 - y_bearing)
                self.cr.show_text(text)

                yPos = yPos + self.rsLayerDistance

    def drawSkipPlusGraph(self, widget, cr):

        self.cr = cr
        self.widget = widget

        # get id length
        self.idLength = 5
        # get amount of nodes
        self.amountNodes = int(math.pow(2,self.idLength))
        # calculate sizes for individual elements
        self.calculateSizes()
        # set the size request to make the drawing area scrollable
        self.widget.set_size_request(self.canvasWidth,self.canvasHeight)

        #paint background color
        self.cr.set_source_rgb(*BACKGROUND_COLOR)
        self.cr.paint()

        #place elements on canvas
        # place vertical connection lines - I deem them unnecessary as we already have the ids displayed and the vertical alignment is visible
        # place clique groupings
        for i in range(self.idLength):  #iterate over the i layers
            for rs in range(int(math.pow(2,i+1))):                 
                if (i+rs)*rs % 20 < 6:
                    start = i*rs % 13
                    self.drawCliqueGrouping(start, start+3,i,rs)
        # place edges
        # draw horizontal edges
        for i in range(self.idLength):  #iterate over the i layers
            for rs in range(int(math.pow(2,i+1))):                 
                if (i+rs)*rs % 20 > 6:
                    start = i*rs % 13
                    self.drawHorizontalEdge(start, (start+(i+rs)*rs)%15,i,rs)

        # draw diagonal edges
        self.drawDiagonalEdge(5,8,0,0,0,1)
        self.drawDiagonalEdge(5,8,0,1,1,0)
                
        # place nodes and id texts
        for x in range(self.amountNodes): #iterate over the horizontal nodes    
            for i in range(self.idLength):  #iterate over the i layers
                for rs in range(int(math.pow(2,i+1))):
                    # calculate text
                    text = '{0:b}'.format(x).zfill(self.idLength)
                    self.drawNodeAndIdText(x,i,rs, text)

        # place layer markings for i layers and rs layers
        self.drawLayerMarkings()

        return False
        
        
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

        self.scrolledWindow = Gtk.ScrolledWindow()
        self.scrolledWindow.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        self.scrolledWindow.set_border_width(10)
        #self.scrolledWindow.set_propagate_natural_width(True)
        self.screen = self.scrolledWindow.get_screen()
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
        self.drawingArea=Gtk.DrawingArea()

        drawElements = DrawElements(self.screenWidth, self.screenHeight)
        self.drawingArea.connect('draw', drawElements.drawSkipPlusGraph)

        #self.viewPort = Gtk.Viewport()
        #self.viewPort.add(self.drawingArea)
        #self.scrolledWindow.add(self.viewPort)
        #flowbox = Gtk.FlowBox()
        #flowbox.add(self.drawingArea)

        #Gtk.Container.add(self.drawingArea)

        #self.scrolledWindow.set_max_content_height (4000)
        #self.scrolledWindow.add(self.drawingArea)
        #self.scrolledWindow.add_with_viewport(self.drawingArea)
        #self.add(self.drawingArea)

        #self.add(self.scrolledWindow)

        sw=Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        #sw.set_border_width(100)
        vp=Gtk.Viewport()
        box=Gtk.VBox()

        vp.set_size_request(100,100)
        '''
        for i in range(90):
            da=Gtk.DrawingArea()
            da.connect("draw", self.draw, [0.3, 0.4, 0.6])
            da.set_size_request(100,100)
            box.add(da)
        '''

        #self.drawingArea.set_size_request(10000,10000)
        box.add(self.drawingArea)

        sw.add(vp)
        vp.add(box)        
        self.add(sw)
        
        self.show_all()

    
    def expose(self):
        pass

    def draw(self, widget, cr, color):
        cr.rectangle(0, 0, 100, 100)
        cr.set_source_rgb(color[0], color[1], color[2])
        cr.fill()
        #cr.queue_draw_area(0, 0, 100, 100)

        return True


class MyWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        Gtk.Window.__init__(
            self, title="ScrolledWindow Example", application=app)
        self.set_default_size(200, 200)

        # the scrolledwindow
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_border_width(10)
        # there is always the scrollbar (otherwise: AUTOMATIC - only if needed
        # - or NEVER)
        scrolled_window.set_policy(
            Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)

        # an image - slightly larger than the window...
        image = Gtk.Image()
        image.set_from_file("gnome-image.png")

        # add the image to the scrolledwindow
        scrolled_window.add_with_viewport(image)

        # add the scrolledwindow to the window
        self.add(scrolled_window)

import sys

class MyApplication(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        win = MyWindow(self)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

#app = MyApplication()
#exit_status = app.run(sys.argv)



PyApp()
Gtk.main()
