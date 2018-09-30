import math
import random
from typing import List

import cairo
import gi
from gi.repository import GLib, Gtk

from vaud.core import Node, NodeFactory
from vaud.skipplus import RS_BIT_LENGTH, SkipNode, SkipNodeReference, prefix

gi.require_version('Gtk', '3.0')

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
RS_TEXT_FONT = "Georgia"
LAYER_TEXT_FONT = "Georgia"

#positioning and size constants
RELATIVE_DISTANCE_NODES_HORIZONTAL = 3 #how many nodes should fit between two nodes horizontally
RELATIVE_MINIMUM_NODE_SIZE = 0.013 #defines how large a node must be at the minimum relative to the screen width
RELATIVE_MAXIMUM_NODE_SIZE = 0.03 #defines how large a node must be at the maximum relative to the screen width

RELATIVE_TEXT_WIDTH_TO_SCREEN = 1/10.0 #defines the width of the longest text on the left side
RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT = 0.2 #defines the empty space width left and right to the left column text relative to that text

RELATIVE_WIDTH_OF_RS_TEXTS = 3 #defines how wide the id texts are in relation to the size of a node
RELATIVE_OFFSET_OF_RS_TEXTS = 0.5 #defines how far below the id text will be placed below a node in relation to the size of a node

RELATIVE_RS_LAYER_HEIGHT_TO_NODE_SIZE = 5.9 # defines the height of the rs layer as defined on S.167 relative to the node size. Unlike the slide, in this representation all rs layers will be quidistant in the same i layer
RELATIVE_DISTANCE_BETWEEN_I_LAYERS_TO_NODE_SIZE = 7.0 #defines the distance between the i layers as defined on S.167 relative to the node size.

RELATIVE_CLIQUE_DISTANCE_SIDE = 0.85 #defines the distance from the side end of the node to the sides of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_ABOVE = 0.3 #defines the distance from the upper end of the node to the upper side of the clique grouping relative to the node size
RELATIVE_CLIQUE_DISTANCE_BELOW = 1.0 #defines the distance from the lower end of the node to the lower side of the clique grouping relative to the node size
RELATIVE_CORNER_RADIUS_OF_CLIQUES_TO_HEIGHT = 0.2 #defines the corner radius of the clique groupings relative to their height

RELATIVE_HORIZONTAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.13 #defines how thick an horizontal edge is relative to the node size
RELATIVE_DIAGONAL_EDGE_THICKNESS_TO_NODE_SIZE = 0.1 #defines how thick an diagonal edge is relative to the node size
RELATIVE_CURVED_EDGE_THICKNESS_TO_NODE_SIZE = 0.08 #defines how thick an curved edge is relative to the node size

RELATIVE_CURVED_EDGE_HEIGHT_TO_RS_LAYER_DISTANCE = 0.7 #defines the height a curved edge can take in relation to the rs layer distance
RELATIVE_CURVED_EDGE_WIDTH_TO_HEIGHT = 0.1 #defines how far away in horizontal direction the control points will be placed for a curved edge in relation to the height of the control point. Lower values (also <0) make the curve harsher

RELATIVE_ARROW_HEAD_HEIGHT_TO_NODE_SIZE = 0.5 #defines how tall an arrow head is in relation to a node
RELATIVE_ARROW_HEAD_WIDTH_TO_NODE_SIZE = 0.8 #defines how wide an arrow head is in relation to a node
RELATIVE_ARROW_HEAD_EDGE_MEDIAN_OFFSET_TO_NODE_SIZE = 0.4 #defines how far an arrow head will be offset from the middle of the edge


# time constants
REFRESH_INTERVAL_TIME = 1000 # defines how many milliseconds will be between each refresh

class Analyzer():
    """
    A class for creating structured representations of skip plus graph data.
    It offers the following public attributes:
    `nodeToIndexMap`, `prefixToNodesMap` and `prefixes`.
    """

    def __init__(self, nodes: List[SkipNode]):
        self.nodes = sorted(nodes) # sort nodes by id
        # mapping nodes to their horizontal positional index
        self.nodeToIndexMap = dict((n, index) for index, n in enumerate(self.nodes))
        self.prefixToNodesMap = self._calculatePrefixToNodesMap()
        # a list of all prefixes with actual nodes, sorted by prefix length and then by random string, ascending
        self.prefixes = sorted(self.prefixToNodesMap.keys(), key=lambda rs: (len(rs), rs))
        
    def _calculatePrefixToNodesMap(self):
        """
        Returns a dict that maps an rs-prefix to lists of nodes with that rs-prefix.
        Prefixes with empty node lists are not contained.
        """
        map = {}
        for node in self.nodes:
            rs = node.rs
            # iterate over rs prefix length
            for prefixLength in range(1, len(rs)):
                rsPrefix = prefix(prefixLength, rs)
                if rsPrefix in map:
                    map[rsPrefix].append(node)
                else:
                    map[rsPrefix] = [node]
        return map

class ElementDrawer:
    def __init__(self, screenWidth, screenHeight, factory: NodeFactory):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.nodeFactory = factory
        self.nodes = factory.nodes
        self.analyzer = Analyzer(self.nodes)

    def calculateSizes(self) -> None:
        '''
        Calculates the absolute sizes of the elements drawn on screen bases
        on screen size and prior set constants.
        '''
        # how large is a node
        self.nodeSize = (self.screenWidth - ((4*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +2) *RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth)) / (self.amountNodes + ((self.amountNodes -1) * RELATIVE_DISTANCE_NODES_HORIZONTAL))
        self.nodeSize = max(RELATIVE_MINIMUM_NODE_SIZE*self.screenWidth, self.nodeSize)
        self.nodeSize = min(RELATIVE_MAXIMUM_NODE_SIZE*self.screenWidth, self.nodeSize)
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
        # how tall and wide is an arrowhead and how far is it offset from the edge median
        self.arrowHeadHeight = RELATIVE_ARROW_HEAD_HEIGHT_TO_NODE_SIZE*self.nodeSize
        self.arrowHeadWidth = RELATIVE_ARROW_HEAD_WIDTH_TO_NODE_SIZE*self.nodeSize
        self.arrowHeadEdgeMedianOffset = RELATIVE_ARROW_HEAD_EDGE_MEDIAN_OFFSET_TO_NODE_SIZE*self.nodeSize
        # how large is a clique grouping
        self.cliqueDistanceSide = RELATIVE_CLIQUE_DISTANCE_SIDE*self.nodeSize
        self.cliqueDistanceAbove = RELATIVE_CLIQUE_DISTANCE_ABOVE*self.nodeSize
        self.cliqueDistanceBelow = RELATIVE_CLIQUE_DISTANCE_BELOW*self.nodeSize
        # how large is a level marking - currently using a BAD solution
        self.levelMarkingMaxWidth = RELATIVE_TEXT_WIDTH_TO_SCREEN*self.screenWidth
        self.sideWidth = (2*RELATIVE_BREAK_NEXT_TO_LEFT_COLUMN_TEXT +1)*self.levelMarkingMaxWidth
        self.levelTextFontSize = self.calculateFontSizeToFitWidth(LAYER_TEXT_FONT, self.levelMarkingMaxWidth, self.rsLength+6) #there are 6 additional characters: rs=...  
        # how large is the id text - currently using a BAD solution
        self.widthOfRsText = RELATIVE_WIDTH_OF_RS_TEXTS*self.nodeSize  
        self.rsTextFontSize = self.calculateFontSizeToFitWidth(RS_TEXT_FONT, self.widthOfRsText, self.rsLength)  
        # calculate the canvas width and height
        self.canvasWidth = self.sideWidth*2 + ((self.amountNodes-1)*self.distanceNodesHorizontal) + self.nodeSize

    def calculateFontSizeToFitWidth (self, fontface: str, allowedWidth: float, maxTextLength: int) -> int:
        '''
        Calculates the fontsize a textelement is allowed to have
        given its font and maximum text length.
        At the moment this is not a good solution but the only one I found as
        you cannot directly calculate the fontsize over the textsize.
        '''
        self.cr.select_font_face(fontface)
        #set the font size to a huge value
        self.cr.set_font_size(10000)
        # get the extents if the font was scaled by 10000
        width = (self.cr.text_extents("0"*maxTextLength))[2]
        # calculate scale factor
        scaleFactor : float = allowedWidth/width
        newFontSize = 10000*scaleFactor

        return newFontSize

    def calculateVerticalPositionOfNode(self, node:Node, iLayer: int) -> float:
        '''
        Calculates the absolute vertical position of the center of
        a node based on its iLayer and rsLayer.
        '''
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
        '''Calculates the absolute horizontal position of a node based on its index of all nodes'''
        return self.sideWidth+ self.distanceNodesHorizontal * nodeXPos

    def draw_rounded(self, upperLeftX: float, upperLeftY: float, lowerRightX: float, lowerRightY: float) -> None:
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
        '''
        Draws a rounded rectangle encasing all nodes in the interval beginning
        with node1 and ending with node2.
        Only uses one specific iLayer and rsLayer
        '''
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
        
    def drawArrowHead(self, edgeMedianX:float, edgeMedianY:float, edgeMedianAngle:float) -> None:
        ''' draws a triangle symbolizing an arrow head located on an edge, given the median point of the edge and its angle at that point'''
        #precalculate the cos and sin values of the angle
        cosAngle = math.cos(edgeMedianAngle)
        sinAngle = math.sin(edgeMedianAngle)

        # calculate the point where the base intersects with the edge
        headStartingPointX = edgeMedianX + cosAngle*self.arrowHeadEdgeMedianOffset
        headStartingPointY = edgeMedianY - sinAngle*self.arrowHeadEdgeMedianOffset

        # calculate the point for the arrow tip
        headSideX = edgeMedianX + (cosAngle*(self.arrowHeadEdgeMedianOffset+self.arrowHeadWidth))
        headSideY = edgeMedianY - (sinAngle*(self.arrowHeadEdgeMedianOffset+self.arrowHeadWidth))
        
        # calculate the offsets from the edge intersection point to the base limiters
        headBaseOffsetX = sinAngle*self.arrowHeadHeight/2.0
        headBaseOffsetY = cosAngle*self.arrowHeadHeight/2.0

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

    def drawHorizontalEdge(self, fromNode:Node, toNode:Node, iLayer: int, isBidirectional:bool) -> None:
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

        #draw
        self.cr.move_to(x1Pos,yPos)
        self.cr.line_to(x2Pos,yPos)
        self.cr.stroke()

        if not isBidirectional:
            if fromIndex<toIndex: #arrowhead points right
                arrowHeadAngle = 0
            else: #arrowHead points left
                arrowHeadAngle = math.pi

            self.drawArrowHead((x2Pos-x1Pos)/2.0+x1Pos, yPos, arrowHeadAngle)


    def drawDiagonalEdge(self, fromNode:Node, toNode:Node, iLayer: int, isBidirectional:bool) -> None:
        ''' draws a diagonal edge from fromNode from to toNode'''
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


        if not isBidirectional:
            # calculate the arrow head angle. Multiply by -1 because GTK uses DirectX coordinates
            arrowHeadAngle = -math.atan((y2Pos-y1Pos)/(x2Pos-x1Pos)) 

            if fromIndex>toIndex: #arrowhead points left. Add pi. Flip it 180°
                arrowHeadAngle = arrowHeadAngle + math.pi

            self.drawArrowHead((x2Pos-x1Pos)/2.0+x1Pos, (y2Pos-y1Pos)/2.0+y1Pos, arrowHeadAngle)

    def drawCurvedEdge(self, fromNode:Node, toNode:Node, iLayer: int, isBidirectional:bool) -> None:
        ''' draws a bezier curve from fromNode from to toNode'''
        #set color
        self.cr.set_source_rgb(*EDGE_CURVED_COLOR)
        #set line thickness
        self.cr.set_line_width (self.curvedEdgeThickness)
        # calculate positions
        fromIndex = self.getIndexOfNode(fromNode)
        toIndex = self.getIndexOfNode(toNode)
        leftIndex = min(fromIndex, toIndex)
        rightIndex = max(fromIndex, toIndex)
        x1Pos = self.calculateHorizontalPositionOfNode(leftIndex)
        x2Pos = self.calculateHorizontalPositionOfNode(rightIndex)
        yPos = self.calculateVerticalPositionOfNode(fromNode, iLayer)

        control1X = x1Pos+self.curvedEdgeControlPointWidth
        control2X = x2Pos-self.curvedEdgeControlPointWidth
        if (fromIndex-toIndex)%2 == 0: #alternate between even and odd distances
            controlY = yPos+self.curvedEdgeControlPointHeight
            arrowHeadY = yPos+ (3.0*self.curvedEdgeControlPointHeight/4.0)
        else:
            controlY = yPos-self.curvedEdgeControlPointHeight
            arrowHeadY = yPos- (3.0*self.curvedEdgeControlPointHeight/4.0)

        if fromIndex<toIndex: #arrowhead points right
            arrowHeadAngle = 0
        else: #arrowHead points left
            arrowHeadAngle = math.pi

        # draw
        self.cr.move_to(x1Pos,yPos)
        self.cr.curve_to(control1X,controlY,  control2X,controlY,  x2Pos,yPos)
        self.cr.stroke()
        if not isBidirectional:
            self.drawArrowHead((x2Pos-x1Pos)/2.0+x1Pos, arrowHeadY, arrowHeadAngle)

    def drawNodeAndRsText(self, node: Node, iLayer: int) -> None:
        #calculate position for node
        xPos = self.calculateHorizontalPositionOfNode(self.getIndexOfNode(node))
        yPos = self.calculateVerticalPositionOfNode(node, iLayer)
        #set color for node
        rsLayer = self.calculateRsLayerOfNode(node, iLayer)
        if rsLayer%2 == 0:
            self.cr.set_source_rgb(*NODE_COLOR_EVEN_RS)
        else:
            self.cr.set_source_rgb(*NODE_COLOR_ODD_RS)
        #place single node
        self.cr.arc(xPos, yPos, self.nodeSize/2.0, 0, 2 * math.pi)
        self.cr.fill()
        #calculate position of the id text
        yPosText = yPos+ ((RELATIVE_OFFSET_OF_RS_TEXTS+0.5)*self.nodeSize)
        #set color for text
        self.cr.set_source_rgb(*TEXT_COLOR)
        #set font face
        self.cr.set_font_size(self.rsTextFontSize)
        #place single id text
        rsText = node.rs.to01()
        x_bearing, y_bearing, width, height = self.cr.text_extents(rsText)[:4]
        self.cr.move_to(xPos - width / 2 - x_bearing, yPosText - height / 2 - y_bearing)
        self.cr.show_text(rsText)

    def drawLayerMarkings(self) ->None:
        '''draws all side texts for the iLayers and rsLayers for the'''
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
        '''given a node and its iLayer this function calculates the rsLayer the node is located on'''
        return int(node.rs.to01()[:iLayer+1], 2)

    def getIndexOfNode (self, node:Node) -> int:
        '''returns the index or the relative horizontal position of the node'''
        return self.analyzer.nodeToIndexMap[node]

    def checkForIntermediateNodes (self, node1:Node, node2:Node, rsPrefix) -> bool:
        '''checks if there exists an intermediate node between node1 and node2. Both of them need to be on the same rsLayer'''
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
        '''takes a node and draws it on the appropriate position on the skip+ graph'''
        # for each i-layer
        for iLayer in range(self.rsLength-1):
            # call drawNodeAndRsText
            self.drawNodeAndRsText(node, iLayer)
        

    def connectNode(self, node:Node) ->None:
        '''takes a node and draws edges for each neighbor the node has alternating between horizontal, diagonal, and curved edges when necessary'''
        # for each i-layer
        for iLayer in range(self.rsLength-1):
            for neighbor in node.ranges[iLayer]:
                isBidirectional = False
                # check if that neighbor also has a connection to node.
                # if so, only draw if node<neighbor. This makes for an ordering
                #isBidirectional = node in neighbor.ranges[iLayer]
                if not isBidirectional or ( isBidirectional and self.getIndexOfNode(node) < self.getIndexOfNode(neighbor)):                    
                    # find out if you need to draw a horizontal, diagonal, or curved edge
                    if node.rs[:iLayer+1] != neighbor.rs[:iLayer+1]:
                        #draw a diagonal edge
                        self.drawDiagonalEdge(node, neighbor, iLayer, isBidirectional)
                    elif self.checkForIntermediateNodes(node,neighbor,node.rs[:iLayer+1]):
                        #draw a curved edge
                        self.drawCurvedEdge(node, neighbor, iLayer, isBidirectional)
                    else:
                        #draw a horizontal edge
                        self.drawHorizontalEdge(node, neighbor, iLayer, isBidirectional)

    def groupNodes(self, nodes: list) ->None:
        # find out which cliques exist

        # find i-layer
        # find rs-layer
        # find lowest horizontal position
        # find highest horizontal position
        # call drawCliqueGrouping
        pass

    def drawSkipPlusGraph(self, widget, cr) -> None:
        '''draw call for the entire skip+ graph'''
        self.cr = cr
        self.widget = widget

        # get id length
        self.rsLength = self.nodes[0].rs.length()
        # get amount of nodes
        self.amountNodes = len(self.nodes)#int(math.pow(2,self.rsLength))
        # calculate sizes for individual elements
        self.calculateSizes()

        #paint background color
        self.cr.set_source_rgb(*BACKGROUND_COLOR)
        self.cr.paint()

        # draw edges
        for node in self.nodes:
            self.connectNode(node)

        # draw nodes
        for node in self.nodes:
            self.placeNode(node)
              
        # draw layer markings
        self.drawLayerMarkings()

    def redraw(self) -> bool:
        # tell the drawing area to queue a new redraw
        self.widget.queue_draw()
        # needs to return True to continue updates
        return True

class Visualizer(Gtk.Window):

    def __init__(self, factory: NodeFactory):
        # Call Window constructor
        super(Visualizer, self).__init__()
        
        #set title
        self.set_title("Skip+ Graph")
        # build a scrollable window
        self.scrolledWindow = Gtk.ScrolledWindow()
        # set the scrollable window to always show the scrollbars
        self.scrolledWindow.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        # get the screen component
        self.screen = self.scrolledWindow.get_screen()
        # Using the screen of the Window, the monitor it's on can be identified
        self.m = self.screen.get_monitor_at_window(self.screen.get_active_window())
        # Then get the geometry of that monitor
        self.monitor = self.screen.get_monitor_geometry(self.m)
        # assign the screen's width and height accordingly
        self.screenWidth = self.monitor.width
        self.screenHeight = self.monitor.height
        # set window to fill entire screen
        self.set_default_size(self.screenWidth,self.screenHeight)
        # connect the close button to the quit action
        self.connect('delete-event', Gtk.main_quit)
        # build a drawing area
        self.drawingArea=Gtk.DrawingArea()
        # make  a new instance of elementDrawer with appropriate parameters
        self.elementDrawer = ElementDrawer(self.screenWidth, self.screenHeight, factory)
        # connect the draw event to the drawSkipPlusGraph method
        self.drawingArea.connect('draw', self.elementDrawer.drawSkipPlusGraph)        
        # start timer for draw refreshes
        GLib.timeout_add(REFRESH_INTERVAL_TIME, self.elementDrawer.redraw ) 
        # add the drawing area to the scrollable window
        self.scrolledWindow.add(self.drawingArea)
        # add the scrollable window to the GTK window
        self.add(self.scrolledWindow)
        # show all elements
        self.show_all()
