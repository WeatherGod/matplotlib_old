#!/usr/bin/env python
import matplotlib
matplotlib.use('GTKAgg')
import pylab
import gtk
import matplotlib.numerix as numerix

fig = pylab.figure(1)
ind = numerix.arange(60)
x_tmp=[]
for i in range(100):
    x_tmp.append(numerix.sin((ind+i)*numerix.pi/15.0))

X=numerix.array(x_tmp)
lines = pylab.plot(X[:,0],'o')

manager = pylab.get_current_fig_manager()
def updatefig(*args):
    updatefig.count += 1
    if updatefig.count>59: updatefig.count=0
    lines[0].set_ydata(X[:,updatefig.count])
    manager.canvas.draw()
    return True

updatefig.count=-1

gtk.timeout_add(25,updatefig)
pylab.show()
