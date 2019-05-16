import math
import numpy as np
import matplotlib.path as mppath
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.path as mppath
from scipy.spatial import ConvexHull
from MiscFunctions import *


class Circularization:
    
    ''' Class which finds the optimal circle containing the appropriate amount of points. '''

    def __init__(self, _points, _detectionFraction):

        self.points = _points
        self.detectionFraction = _detectionFraction
        self.numPoints = len(self.points)
        
    def getFractionalItems(self, startingPoint, returnFmt = 0, refinements = 1):
    
        """ 
        Function that hones in on closest density of points and then finds all near points to it by calculating the average of those points and then 
        appending the closest to the average to the list. It will return one of the following things:
        -1). Fractional detection points
         0). [list(tuples), mppath.Path] of cut fractional points
         1). [list(tuples), mppath.Path] of uncut (Polygon) points
         2). [[list(tuples), mppath.Path], [list(tuples), mppath.Path]] fractional cut and uncut respectively
        """

        def chaikins_corner_cutting(coords, refinements=1):
            coords = np.array(coords)

            for _ in range(refinements):
                L = coords.repeat(2, axis=0)
                R = np.empty_like(L)
                R[0] = L[0]
                R[2::2] = L[1:-1:2]
                R[1:-1:2] = L[2::2]
                R[-1] = L[-1]
                coords = L * 0.75 + R * 0.25

            return coords

        def closest_node(node, nodes):

            """ returns closest node using dot vectorization, slightly faster see https://codereview.stackexchange.com/questions/28207/finding-the-closest-point-to-a-list-of-points """

            if node in nodes:
                nodes.remove(node)

            nodes = np.asarray(nodes)
            deltas = nodes - node
            dist_2 = np.einsum('ij,ij->i', deltas, deltas)
            temp = nodes[np.argmin(dist_2)]
            return (temp[0], temp[1])

        def averagePoints(nodeList):
            #Consider switching to numpy mean arrays if performance is an issue
            #inits
            tempX, tempY = 0, 0
            for node in nodeList:
                tempX += node[0]
                tempY += node[1]
            
            avX, avY = tempX/len(nodeList), tempY/len(nodeList)
            avPoint = [avX, avY]

            return avPoint

        def fractionalPoints(totalNodeList, recNodeList, fracPoints):

            """ Starts out with one point should be in a place of high density #NOTE this is not automated yet. Keep adding points (it will add the closest)
            point to the set over and over until 50% of the points are encircled. Then it will return a list of those points """

            avPoint = averagePoints(recNodeList)

            for i in range(0, fracPoints):
                closestPoint = closest_node(avPoint, totalNodeList) #Finds closest point
                totalNodeList.remove(closestPoint)
                recNodeList.append(closestPoint)

                printProgressBar(i, fracPoints)    

            return recNodeList 

        #Gets fractional points 
        numPointsFrac = math.floor(self.numPoints * self.detectionFraction)
        fracPoints = fractionalPoints(self.points, [startingPoint], numPointsFrac)
        
        #Hull creation and getting of verticies
        hull = ConvexHull(fracPoints)
        polyVertices = [fracPoints[vertex] for vertex in hull.vertices] 
        cutVertices = chaikins_corner_cutting(polyVertices, refinements)

        #Path creation 
        polyCodes = [mppath.Path.LINETO] * len(polyVertices)
        polyCodes[0] = mppath.Path.MOVETO
        polyCodes[-1] = mppath.Path.CLOSEPOLY

        cutCodes = [mppath.Path.LINETO] * len(cutVertices)
        cutCodes[0] = mppath.Path.MOVETO
        cutCodes[-1] = mppath.Path.CLOSEPOLY

        polyPath = mppath.Path(polyVertices, polyCodes)
        cutPath = mppath.Path(cutVertices, cutCodes)

        #How you want the information returned 
        if returnFmt == -2:
            return [[cutVertices, cutPath], fracPoints]
        if returnFmt == -1:
            return fracPoints
        if returnFmt == 0:
            return [cutVertices, cutPath]
        if returnFmt == 1:
            return [polyVertices, polyPath]
        if returnFmt == 2:
            return [[cutVertices, cutPath], [polyVertices, polyPath]]


    def greedyHeuristicUniModal(self):

        ''' See file:///home/n/Downloads/Setup/9449-Fadallah.pdf greedy heuristic '''

        #Inits
        criticalValue = 1 - self.detectionFraction

        fracPoints = self.points


        for j in range(0, math.floor(self.detectionFraction * self.numPoints)):
            
            #Creating convex hull and calculating vertices
            hull = ConvexHull(fracPoints)
            hullVertices = [fracPoints[vertex] for vertex in hull.vertices] 
            hullVertM = np.zeros((1, len(hullVertices)))
            areaBefore = PolyArea(hullVertices)

            for k in range(0, len(hullVertices)):
                element = hullVertices[k]
                hullVertices.pop(k)

                areaAfter = PolyArea(hullVertices)
                diffArea = areaBefore - areaAfter
                hullVertM[0, k] = diffArea

                hullVertices.insert(k, element)

            #Testing
            x, y = zip(*self.points)
            plt.scatter(x, y, s = 1, c='b')
            x,y = zip(*hullVertices)
            plt.scatter(x,y, c='r', label = diffArea)
            plt.xlim([-4, 4])
            plt.ylim([-4, 4])
            plt.savefig("Frames/Frame{0:03d}".format(j))
            plt.close()
            #Testing

            throwAway, indexMax = np.unravel_index(hullVertM.argmax(), hullVertM.shape)
            valToRem = hullVertices[indexMax]
            fracPoints.remove(valToRem)

        return hullVertices

    def greedyAngleHeuristicUniModal(self, minSharpness):
    
        ''' See file:///home/n/Downloads/Setup/9449-Fadallah.pdf greedy heuristic '''

        #Inits
        criticalValue = 1 - self.detectionFraction

        fracPoints = self.points


        for j in range(0, math.floor(self.detectionFraction * self.numPoints)):
            
            #Creating convex hull and calculating vertices
            hull = ConvexHull(fracPoints)
            hullVertices = [fracPoints[vertex] for vertex in hull.vertices] 
            
            #Finding all angles and comparing to minimal sharpness
            angleArray = np.zeros([1, len(hullVertices)])
            for i, vertex in enumerate(hullVertices):
                angle = angleBetweenPoints(i, hullVertices)
                angleArray[0, i] = angle

            if np.amin(angleArray) < minSharpness:
                throwAway, index = np.unravel_index(angleArray.argmin(), angleArray.shape)
                valToRem = hullVertices[index]
                fracPoints.remove(valToRem)
            
            #Begins checking areas 
            else:
                hullVertM = np.zeros((1, len(hullVertices)))
                areaBefore = PolyArea(hullVertices)

                for k in range(0, len(hullVertices)):
                    element = hullVertices[k]
                    hullVertices.pop(k)

                    areaAfter = PolyArea(hullVertices)
                    diffArea = areaBefore - areaAfter
                    hullVertM[0, k] = diffArea

                    hullVertices.insert(k, element)

                #Testing
                x, y = zip(*self.points)
                plt.scatter(x, y, s = 1, c='b')
                x,y = zip(*hullVertices)
                plt.scatter(x,y, c='r', label = diffArea)
                plt.xlim([-4, 4])
                plt.ylim([-4, 4])
                plt.savefig("Frames/Frame{0:03d}".format(j))
                plt.close()
                #Testing

                throwAway, indexMax = np.unravel_index(hullVertM.argmax(), hullVertM.shape)
                valToRem = hullVertices[indexMax]
                fracPoints.remove(valToRem)

        return hullVertices


    def greedyHeuristicMultiModal(self):
    
        ''' See file:///home/n/Downloads/Setup/9449-Fadallah.pdf greedy heuristic '''

        #Inits
        criticalValue = 1 - self.detectionFraction

        fracPoints = self.points


        for j in range(0, math.floor(self.detectionFraction * self.numPoints)):
            
            #Creating convex hull and calculating vertices
            hull = ConvexHull(fracPoints)
            hullVertices = [fracPoints[vertex] for vertex in hull.vertices] 
            hullVertM = np.zeros((1, len(hullVertices)))
            areaBefore = PolyArea(hullVertices)

            for k in range(0, len(hullVertices)):
                element = hullVertices[k]
                hullVertices.pop(k)

                areaAfter = PolyArea(hullVertices)
                diffArea = areaBefore - areaAfter
                hullVertM[0, k] = diffArea


                #Testing
                x, y = zip(*self.points)
                plt.scatter(x, y, s = 1, c='b')
                x,y = zip(*hullVertices)
                plt.scatter(x,y, c='r', label = diffArea)
                plt.legend()
                plt.xlim([-4, 4])
                plt.ylim([-4, 4])
                plt.savefig("Frames/{}_{}".format(j,k))
                plt.close()
                #Testing

                hullVertices.insert(k, element)

            throwAway, indexMax = np.unravel_index(hullVertM.argmax(), hullVertM.shape)
            valToRem = hullVertices[indexMax]
            fracPoints.remove(valToRem)

        return hullVertices

def PolyArea(xy):
    zipped = list(zip(*xy))
    x, y = list(zipped[0]), list(zipped[1])
        
    return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

def angleBetweenPoints(pointIndex, points):
    if pointIndex - 1 == -1:
        
        a = np.array(points[-1])
        b = np.array(points[pointIndex])
        c = np.array(points[pointIndex + 1])

    elif pointIndex + 1 == len(points):
        
        a = np.array(points[pointIndex - 1])
        b = np.array(points[pointIndex])
        c = np.array(points[0])

    else:
        a = np.array(points[pointIndex - 1])
        b = np.array(points[pointIndex])
        c = np.array(points[pointIndex + 1])
        
    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(cosine_angle)

    return angle


#from TEST_Dump import points
cov = [[1, 0], [0, 1]]
mean = [0, 0]
points = np.random.multivariate_normal(mean, cov, 500)
points = [list(element) for element in points]

testCirculizer = Circularization(points, .5)
greedHeur = testCirculizer.greedyAngleHeuristicUniModal(math.pi/2)
hull = ConvexHull(points)
hullVertices = [points[vertex] for vertex in hull.vertices] 
x, y = zip(*hullVertices)
plt.scatter(x,y,c='r')
xPoints = [point[0] for point in points]
yPoints = [point[1] for point in points]
plt.scatter(xPoints, yPoints, s=1)

plt.xlim([-1, 1])
plt.ylim([-1, 1])
plt.show()    