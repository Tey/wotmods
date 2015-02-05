from util import override,checkPluginsImports,getCodeForImports
import __builtin__

#dynamic import
modules = [ ('orig',['Orig']) ]
checkPluginsImports('demo',modules)
exec(getCodeForImports())


class A:
    #the new function
    @staticmethod
    def newtest(self):
        print "world"
    
#overriding class function
c = Orig()
old = override(Orig,"test",A.newtest)
c.test() # print world
override(Orig,"test",old)
c.test() # print hello

print ""


#overriding object function
c = Orig()
old = override(c,"test",A.newtest)
c.test() # print world
Orig().test() # print Hello 

print ""

#adding new function to object only
c = Orig()
override(c,"test2",A.newtest)
print hasattr(Orig, "test2")
print hasattr(c, "test2")
c.test2()
