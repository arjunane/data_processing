class Pool:
   'Common base class for all Pools'
   poolCount = 0

   def __init__(self, name, position):
      self.name = name
      self.position = position
      Pool.poolCount += 1
      #Pool.displayName(self)

   def displayName(self):
      print("Pool Label : ", self.name)

