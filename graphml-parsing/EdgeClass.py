class Edge:
   'Common base class for all Edges'
   edgeCount = 0

   def __init__(self, source, target):
      self.source = source
      self.target = target
      Edge.edgeCount += 1
      #Edge.displayName(self)

   def displayName(self):
      print("Edge from ",self.source," to : ", self.target)
