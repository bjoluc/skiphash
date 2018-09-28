import gi
gi.require_version('Gtk', '3.0')
import cairo, math, random
from gi.repository import Gtk
from vaud.core import Node

#color constants
NODE_COLOR_EVEN_RS = (0.266, 0.623, 0.835) #(0.407, 0.427, 0.650)
NODE_COLOR_ODD_RS = (0.678, 0.729, 0.760) #(0.407, 0.427, 0.650)
EDGE_DIAGONAL_COLOR = (0.423, 0.278, 0.341) #(0.090, 0.101, 0.250)
EDGE_HORIZONTAL_COLOR = (0.772, 0.125, 0.415) #(0.090, 0.101, 0.250)
EDGE_CURVED_COLOR = (0.658, 0.243, 0.376) #(0.090, 0.101, 0.250)
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
RELATIVE_MAXIMUM_NODE_SIZE = 0.03 #defines how large a node must be at the maximum relative to the screen width

RELATIVE_TEXT_WIDTH_TO_SCREEN = 1/15.0 #defines the width of the longest text on the left side
RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT = 0.5 #defines the empty space width left and right to the left column text relative to that text

RELATIVE_WIDTH_OF_ID_TEXTS = 3 #defines how wide the id texts are in relation to the size of a node
RELATIVE_OFFSET_OF_ID_TEXTS = 0.5 #defines how far below the id text will be placed below a node in relation to the size of a node

RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE = 3.4 # defines the height of the rs layer as defined on S.167 relative to the node size. Unlike the slide, in this representation all rs layers will be quidistant in the same i layer
RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE = 5.0 #defines the distance between the i layers as defined on S.167 relative to the node size.

RELATIVE_CLIQUE_DISTANCE_SIDE = 0.85 #defines the distance from the side end of the node to the sides of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_ABOVE = 0.3 #defines the distance from the upper end of the node to the upper side of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_BELOW = 1.0 #defines the distance from the lower end of the node to the lower side of the clique grouping relative to the node size
RELATIVE_CORNER_RADIUS_OF_CLIQUES_TO_HEIGHT = 0.2 #defines the corner radius of the clique groupings relative to their height

RELATIVE_HORIZONTAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.3 #defines how thick an horizontal edge is relative to the node size
RELATIVE_DIAGONAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.2 #defines how thick an diagonal edge is relative to the node size
RELATIVE_CURVED_EDGE_THICKNESS_TO_NODE_SIZE = 0.08 #defines how thick an curved edge is relative to the node size

RELATIVE_CURVED_EDGE_HEIGHT_TO_RS_LAYER_DISTANCE = 0.7 #defines the height a curved edge can take in relation to the rs layer distance
RELATIVE_CURVED_EDGE_WIDTH_TO_HEIGHT = 0.1 #defines how far away in horizontal direction the control points will be placed for a curved edge in relation to the height of the control point. Lower values (also <0) make the curve harsher

class DrawElements:

    def __init__(self, screenWidth, screenHeight, nodes: list, analyzer):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.nodes = nodes
        self.analyzer = analyzer

    def calculateSizes(self) ->None:
        '''calculates the absolute sizes of the elements drawn on screen bases on screen size and prior set constants'''
        # how large is a node
        self.nodeSize = (self.screenWidth - ((4*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +2) *RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth)) / (self.amountNodes + ((self.amountNodes -1) * RELATIVE_DISTANCE_NODES_HORIZONTAL))
        self.nodeSize = max(RELATIVE_MINIMUM_NODE_SIZE*self.screenWidth, self.nodeSize)
        self.nodeSize = min(RELATIVE_MAXIMUM_NODE_SIZE*self.screenWidth, self.nodeSize)
        #print("self.nodeSize: " + str(self.nodeSize))
        # how wide is the horizontal distance between nodes
        self.distanceNodesHorizontal = (RELATIVE_DISTANCE_NODES_HORIZONTAL+1)*self.nodeSize
        # how tall is an rs layer
        self.rsLayerDistance = RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE*self.nodeSize
        # what's the distance between the two i layers
        self.iLayerDistance = RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE*self.nodeSize
        # how thick is an edge
        self.horizontalEdgeThickness = RELATIVE_HORIZONTAL_EDGE_THICKNESS_TO_NODE_SIZE*self.nodeSize
        self.diagonalEdgeThickness = RELATIVE_DIAGONAL_EDGE_THICKNESS_TO_NODE_SIZE*self.nodeSize
        self.curvedEdgeThickness = RELATIVE_CURVED_EDGE_THICKNESS_TO_NODE_SIZE*self.nodeSize
        # how high and wide will the control points be set for a curved edge
        self.curvedEdgeControlPointHeight = RELATIVE_CURVED_EDGE_HEIGHT_TO_RS_LAYER_DISTANCE*self.rsLayerDistance *4.0/3.0
        self.curvedEdgeControlPointWidth = RELATIVE_CURVED_EDGE_WIDTH_TO_HEIGHT * self.curvedEdgeControlPointHeight
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
        #print("self.canvasWidth " + str(self.canvasWidth))
        

    def calculateFontSizeToFitWidth (self, fontface: str, allowedWidth: float, maxTextLength: int) -> int:
        '''calculates the fontsize a textelement is allowed to have given its font and maximum text length.
        At the moment this is not a good solution but the only one I found as you cannot directly calculate the fontsize over the textsize'''
        self.cr.select_font_face(fontface)
        #set the font size to a huge value
        self.cr.set_font_size(10000)
        # get the extents if the font was scaled by 10000
        x_bearing, y_bearing, width, height = (self.cr.text_extents("0"*maxTextLength))[:4]
        # calculate scale factor
        scaleFactor : float = allowedWidth/width
        newFontSize = 10000*scaleFactor

        return newFontSize


    def calculateVerticalPositionOfNode(self, node:Node, iLayer: int) -> float:
        '''Calculates the absolute vertical position of the center of a node based on its iLayer and rsLayer'''
        #return (self.iLayerDistance*(iLayer+1)) + (self.rsLayerDistance*(math.pow(2,iLayer+1)-2+rsLayer))
        
        distance = 0
        previousPrefixLength = 0

        for prefix in self.analyzer.prefixes:
            # has the iLayer changed
            if prefix.length() > previousPrefixLength:
                # add iLayer distance
                distance = distance+self.iLayerDistance
                previousPrefixLength = prefix.length()
            else: # if not add rsLayer distance
                distance = distance+self.rsLayerDistance

            
            # if the prefix matches the prefix of the node of length iLayer+1
            if prefix == node.rs [:iLayer+1]:
                # then the correct rs layer was found
                # return the distance
                return distance

        # if prefix wasn't found then an error has occurred. Return -1
        print("something bad has happend while checking for prefix " + str(prefix))
        print("no match for " +  str(node.rs [:iLayer+1]) + " with i layer length " + str(iLayer))
        return -1

    def calculateHorizontalPositionOfNode (self, nodeXPos) ->float:
        '''Calculates the absolute horizontal position of a node based on its rank of all nodes'''
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
        '''Draws a rounded rectangle encasing all nodes in the interval beginning with node1 and ending with node2.
        Only uses one specific iLayer and rsLayer'''
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
        
    def drawArrowHead(self, headHeight:float, headWidth:float, edgeMedianX:float, edgeMedianY:float, edgeMedianAngle:float) -> None:
        edgeMedianOffset = 50

        #if random.random()<0.5:
        #    edgeMedianAngle = edgeMedianAngle +math.pi

        #precalculate the cos and sin values of the angle
        cosAngle = math.cos(edgeMedianAngle)
        sinAngle = math.sin(edgeMedianAngle)

        # calculate the point where the base intersects with the edge
        headStartingPointX = edgeMedianX + cosAngle*edgeMedianOffset
        headStartingPointY = edgeMedianY - sinAngle*edgeMedianOffset

        # calculate the point for the arrow tip
        headSideX = edgeMedianX + (cosAngle*(edgeMedianOffset+headWidth))
        headSideY = edgeMedianY - (sinAngle*(edgeMedianOffset+headWidth))
        
        # calculate the offsets from the edge intersection point to the base limiters
        headBaseOffsetX = sinAngle*headHeight/2.0
        headBaseOffsetY = cosAngle*headHeight/2.0

        # calculate base limiters with the help of the offsets
        headUpX = headStartingPointX - headBaseOffsetX
        headUpY = headStartingPointY - headBaseOffsetY

        headDownX = headStartingPointX + headBaseOffsetX
        headDownY = headStartingPointY + headBaseOffsetY

        # draw lines and fill them
        # color should have been set by the calling function
        self.cr.move_to(headUpX,headUpY)
        self.cr.line_to(headSideX,headSideY)
        self.cr.line_to(headDownX,headDownY)
        self.cr.fill()

    def drawHorizontalEdge(self, fromNode:Node, toNode:Node, iLayer: int) -> None:
        ''' draws a horizontal edge from node fromXPos to node toXPos on the specified iLayer and rsLayer'''
        #set color
        self.cr.set_source_rgb(*EDGE_HORIZONTAL_COLOR)
        #set line thickness
        self.cr.set_line_width (self.horizontalEdgeThickness)

        #calculate positions
        fromIndex = self.getIndexOfNode(fromNode)
        toIndex = self.getIndexOfNode(toNode)

        x1Pos = self.calculateHorizontalPositionOfNode(fromIndex)
        x2Pos = self.calculateHorizontalPositionOfNode(toIndex)
        yPos = self.calculateVerticalPositionOfNode(fromNode, iLayer)

        self.cr.move_to(x1Pos,yPos)
        self.cr.line_to(x2Pos,yPos)
        self.cr.stroke()

        if fromIndex<toIndex: #arrowhead points right
            arrowHeadAngle = 0
        else: #arrowHead points left
            arrowHeadAngle = math.pi

        self.drawArrowHead(50,100,(x2Pos-x1Pos)/2.0+x1Pos, yPos, arrowHeadAngle)


    def drawDiagonalEdge(self, fromNode:Node, toNode:Node, iLayer: int) -> None:
        ''' draws a diagonal edge from node from to node to'''
        #set color
        self.cr.set_source_rgb(*EDGE_DIAGONAL_COLOR)
        #set line thickness
        self.cr.set_line_width (self.diagonalEdgeThickness)
        
        fromIndex = self.getIndexOfNode(fromNode)
        toIndex = self.getIndexOfNode(toNode)
        x1Pos = self.calculateHorizontalPositionOfNode(fromIndex)
        x2Pos = self.calculateHorizontalPositionOfNode(toIndex)
        y1Pos = self.calculateVerticalPositionOfNode(fromNode, iLayer)
        y2Pos = self.calculateVerticalPositionOfNode(toNode, iLayer)

        self.cr.move_to(x1Pos,y1Pos)
        self.cr.line_to(x2Pos,y2Pos)
        self.cr.stroke()

        # calculate the arrow head angle. Multiply by -1 because GTK uses DirectX coordinates
        arrowHeadAngle = -math.atan((y2Pos-y1Pos)/(x2Pos-x1Pos)) 

        if fromIndex>toIndex: #arrowhead points left. Add pi. Flip it 180°
            arrowHeadAngle = arrowHeadAngle + math.pi

        #print("arrowHeadAngle: " + str(arrowHeadAngle))
        self.drawArrowHead(50,100,(x2Pos-x1Pos)/2.0+x1Pos, (y2Pos-y1Pos)/2.0+y1Pos, arrowHeadAngle)

    def drawCurvedEdge(self, fromNode:Node, toNode:Node, iLayer: int) -> None:
        #set color
        self.cr.set_source_rgb(*EDGE_CURVED_COLOR)
        #set line thickness
        self.cr.set_line_width (self.curvedEdgeThickness)
        # calculate positions
        fromIndex = self.getIndexOfNode(fromNode)
        toIndex = self.getIndexOfNode(toNode)
        x1Pos = self.calculateHorizontalPositionOfNode(fromIndex)
        x2Pos = self.calculateHorizontalPositionOfNode(toIndex)
        yPos = self.calculateVerticalPositionOfNode(fromNode, iLayer)

        control1X = x1Pos+self.curvedEdgeControlPointWidth
        control2X = x2Pos-self.curvedEdgeControlPointWidth
        if (fromIndex-fromIndex)%2 == 0: #alternate between even and odd distances
            controlY = yPos+self.curvedEdgeControlPointHeight
            arrowHeadY = yPos+ (3.0*self.curvedEdgeControlPointHeight/4.0)
        else:
            controlY = yPos-self.curvedEdgeControlPointHeight
            arrowHeadY = yPos- (3.0*self.curvedEdgeControlPointHeight/4.0)

        # draw
        self.cr.move_to(x1Pos,yPos)
        self.cr.curve_to(control1X,controlY,  control2X,controlY,  x2Pos,yPos)
        self.cr.stroke()

        if fromIndex<toIndex: #arrowhead points right
            arrowHeadAngle = 0
        else: #arrowHead points left
            arrowHeadAngle = math.pi

        self.drawArrowHead(50,100,(x2Pos-x1Pos)/2.0+x1Pos, arrowHeadY, arrowHeadAngle)
        '''
        height = 3/4 *(yPos+self.curvedEdgeControlPointHeight) + 1/4 *(yPos)
        self.cr.move_to(x1Pos,height)
        self.cr.line_to(x2Pos,height)
        self.cr.stroke()

        #3/4 Ymax + 1/4 Ymin
        '''

    def drawNodeAndIdText(self, node: Node, iLayer: int) -> None:
        #calculate position for node
        xPos = self.calculateHorizontalPositionOfNode(self.analyzer.nodeToIndexMap[node])
        yPos = self.calculateVerticalPositionOfNode(node, iLayer)
        #set color for node
        rsLayer = self.calculateRsLayerOfNode(node, iLayer)
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
        idText = node.rs.to01()
        x_bearing, y_bearing, width, height = self.cr.text_extents(idText)[:4]
        self.cr.move_to(xPos - width / 2 - x_bearing, yPosText - height / 2 - y_bearing)
        self.cr.show_text(idText)

    def drawLayerMarkings(self) ->None:             

        #set color
        self.cr.set_source_rgb(*TEXT_COLOR)
        #set correct font size
        self.cr.set_font_size(self.levelTextFontSize)

        distance = 0
        previousPrefixLength = 0

        for prefix in self.analyzer.prefixes:

            # has the iLayer changed
            if prefix.length() > previousPrefixLength:
                #increase distance by iLayerDistance
                distance = distance+self.iLayerDistance
                previousPrefixLength = prefix.length()

                #calculate position of the i label
                xPos = self.canvasWidth - (self.sideWidth/2.0)
                #set correct text
                text = "i=" +  str(prefix.length()-1)
                #place i label
                x_bearing, y_bearing, width, height = self.cr.text_extents(text)[:4]
                self.cr.move_to(xPos - width / 2 - x_bearing, distance - height / 2 - y_bearing)
                self.cr.show_text(text)
            else: #increase distance by rsLayer distance
                distance = distance+self.rsLayerDistance

            
            
            #calculate position of the rs label
            xPos = self.sideWidth/2.0
            #set correct text
            text = "rs=" +  prefix.to01() + "..."
            #place rs label
            x_bearing, y_bearing, width, height = self.cr.text_extents(text)[:4]
            self.cr.move_to(xPos - width / 2 - x_bearing, distance - height / 2 - y_bearing)
            self.cr.show_text(text)

        # set the correct canvas height
        self.canvasHeight = distance + self.iLayerDistance        

        # set the size request to make the drawing area scrollable
        self.widget.set_size_request(self.canvasWidth,self.canvasHeight)
            

    def calculateRsLayerOfNode (self, node:Node, iLayer: int) -> int:
        return int(node.rs.to01()[:iLayer+1], 2)

    def getIndexOfNode (self, node:Node) -> int:
        #return self.nodes.index(node)
        return self.analyzer.nodeToIndexMap[node]

    def checkForIntermediateNodes (self, node1:Node, node2:Node, rsPrefix) -> bool:
        if self.getIndexOfNode(node1)<self.getIndexOfNode(node2):
            nodeLeft = node1
            nodeRight = node2
        else:
            nodeLeft = node2
            nodeRight = node1

        nodesInRsLayer = self.analyzer.prefixToNodesMap[rsPrefix]
        for x,node in enumerate(nodesInRsLayer):
            if node == nodeLeft:
                if len(nodesInRsLayer)==x+1 or nodesInRsLayer[x+1] == nodeRight:
                    # it's the edge or the next node is nodeRight
                    return False
                else:
                    # there is a node between left and right on the same rsLayer
                    return True
        return False
        


    def placeNode(self, node:Node) ->None:
        # for each i-layer
        for iLayer in range(self.idLength-1):
            # find rs
            rsText = node.rs.to01()
            #print("rsText: " + str(rsText))
            # find rs-layer
            rsLayer = self.calculateRsLayerOfNode(node, iLayer)
            # call drawNodeAndIdText
            self.drawNodeAndIdText(node, iLayer)
        

    def connectNode(self, node:Node) ->None:
        # for each i-layer
        for iLayer in range(self.idLength-1):
            for neighbor in node.ranges[iLayer]:
                # find out if you need to draw a horizontal, diagonal, or curved edge
                if node.rs[:iLayer+1] != neighbor.rs[:iLayer+1]:
                    #draw a diagonal edge
                    self.drawDiagonalEdge(node, neighbor, iLayer)
                elif self.checkForIntermediateNodes(node,neighbor,node.rs[:iLayer+1]):
                    #draw a curved edge
                    self.drawCurvedEdge(node, neighbor, iLayer)
                else:
                    #draw a horizontal edge
                    self.drawHorizontalEdge(node, neighbor, iLayer)

    def groupNodes(self, nodes: list) ->None:
        # find out which cliques exist


        # find i-layer
        # find rs-layer
        # find lowest horizontal position
        # find highest horizontal position
        # call drawCliqueGrouping
        pass

    def placeExamples(self):
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

        # draw curved edges
        self.drawCurvedEdge(3,8,0,0)
        self.drawCurvedEdge(3,7,0,0)
        self.drawCurvedEdge(3,6,0,0)
        self.drawCurvedEdge(3,5,0,0)

        self.drawCurvedEdge(3,5,0,1)
        self.drawCurvedEdge(4,6,0,1)
        self.drawCurvedEdge(4,7,0,1)
        self.drawCurvedEdge(4,8,0,1)
                
        # place nodes and id texts
        for x in range(self.amountNodes): #iterate over the horizontal nodes    
            for i in range(self.idLength):  #iterate over the i layers
                for rs in range(int(math.pow(2,i+1))):
                    # calculate text
                    text = '{0:b}'.format(x).zfill(self.idLength)
                    self.drawNodeAndIdText(x,i,rs, text)

        # place layer markings for i layers and rs layers
        self.drawLayerMarkings()

    def drawSkipPlusGraph(self, widget, cr):

        self.cr = cr
        self.widget = widget

        # get id length
        self.idLength = 16
        # get amount of nodes
        self.amountNodes = 10#int(math.pow(2,self.idLength))
        # calculate sizes for individual elements
        self.calculateSizes()

        #paint background color
        self.cr.set_source_rgb(*BACKGROUND_COLOR)
        self.cr.paint()

        # draw edges
        for nodeCounter,node in enumerate(self.nodes):
            self.connectNode(node)

        # draw nodes
        for node in self.nodes:
            self.placeNode(node)
              
        # draw layer markings
        self.drawLayerMarkings()

        return False

    def redraw(self) -> None:
        print("now in the main redraw")
        self.widget.queue_draw()
        '''
        self.calculateSizes()

        #paint background color
        self.cr.set_source_rgb(*BACKGROUND_COLOR)
        self.cr.paint()

        # draw edges
        for nodeCounter,node in enumerate(self.nodes):
            self.connectNode(node)

        # draw nodes
        for node in self.nodes:
            self.placeNode(node)
              
        # draw layer markings
        self.drawLayerMarkings()

        return False
        '''
    
from twisted.application.internet import TimerService    
class PyApp(Gtk.Window):
    def __init__(self, nodes: list, analyzer):
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
        #print("Height: %s, Width: %s" % (self.monitor.height, self.monitor.width))
        self.screenWidth = self.monitor.width
        self.screenHeight = self.monitor.height
        self.set_title("Skip+ Graph")
        self.set_default_size(self.screenWidth,self.screenHeight)
        self.connect('delete-event', Gtk.main_quit)
        self.drawingArea=Gtk.DrawingArea()

        self.drawElements = DrawElements(self.screenWidth, self.screenHeight, nodes, analyzer)
        self.drawingArea.connect('draw', self.drawElements.drawSkipPlusGraph)

        self.scrolledWindow.add(self.drawingArea)
        self.add(self.scrolledWindow)
        
        self.show_all()

        timer = TimerService(1, self.drawElements.redraw())  # use some of your object's update method of course ;)
        timer.startService()
    
    def expose(self):
        pass

    def redraw(self):
        print("upper draw call")
        self.drawElements.redraw()
        #self.drawingArea.widgetQueueDraw()

class Visualizer():

    def __init__(self, nodes: list, analyzer):
        self.nodes = nodes
        self.analyzer = analyzer
        self.pyApp = PyApp(nodes, analyzer)
        Gtk.main()

    def redraw(self):
        self.pyApp.redraw()