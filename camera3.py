from time import sleep, time
import numpy as np
from picamera import PiCamera
from picamera.array import PiRGBAnalysis
from sklearn.cluster import DBSCAN
scan = DBSCAN(eps=2, min_samples=3)

class Analysis(PiRGBAnalysis):
    def __init__(self, camera, size=None):
        #super(PiAnalysisOutput, self).__init__()
        self.camera = camera
        self.size = size
        self.x0 = np.array(0)
        self.i = 0
        self.t = time()
        self.misc = []
    
    def analyse(self, x):
        x = x[:,:,1]
        d = self.x0-x
        d[self.x0<x] = 0
        xy = np.argwhere(d>10)
        if xy.shape[0]>2 and xy.shape[0]<1200:
            clust = scan.fit_predict(xy)
            ind = clust>-1
            clust = clust[ind]
            xy = xy[ind]
            denom = np.bincount(clust)
            numerx = np.bincount(clust, xy[:,0])
            numery = np.bincount(clust, xy[:,1])
            xc = numerx/denom
            yc = numery/denom
            self.misc.append(xc)
        self.x0 = x
        self.i += 1
        if self.i % 10 == 0:
            td = time() - self.t
            self.t += td
            print("\r" + str(10/td), end="")
        


rectime = 4
camera = PiCamera()
output = Analysis(camera)
camera.resolution = (640, 640)
camera.framerate = 24
camera.color_effects = (128,128)
camera.start_preview(fullscreen=False, window = (20, 40, 640, 640))
sleep(2)
camera.start_recording(output, format='rgb')
#camera.start_recording('/home/pi/video2.h264')
camera.wait_recording(rectime)
camera.stop_recording()
camera.stop_preview()
        
print("\n%s fps" % ((output.i+6)/rectime))
print(output.misc)

#omxplayer -o hdmi video2.h264
#avconv -i video.h264 -s 640x640 -q:v 1 imgs/video-%03d.jpg

