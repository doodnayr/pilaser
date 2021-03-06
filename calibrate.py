import numpy as np
from picamera import PiCamera
from picamera.array import PiRGBAnalysis
from sklearn.cluster import DBSCAN
from binascii import unhexlify, hexlify
from scipy.interpolate import griddata
import os
from hipsterplot import plot

scan = DBSCAN(eps=2, min_samples=3, metric='euclidean', algorithm='ball_tree', leaf_size=30)
#import RPi.GPIO as GPIO
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(26, GPIO.OUT)

def tohex(v):
    return unhexlify("%0.4X" % (v+4096))

def printr(s):
    print("\r" + s + "       ", end="")

class Analysis(PiRGBAnalysis):
    def __init__(self, camera, size=None):
        self.camera = camera
        self.size = size
        self.z0 = np.array(0)
        self.stable_counter = 0
        self.background_sum = np.zeros((480, 640), dtype=np.uint16)
        self.background = np.array(0)
        #self.campoints = np.zeros((480, 640), dtype=np.uint16)
        #self.campoints[:] = numpy.nan
        self.laser_cal_points = np.append(np.arange(0, 2048, 256), 2047)
        self.npoints = self.laser_cal_points.shape[0]
        self.laser_xi = 0
        self.laser_yi = 0
        self.x_inc = -1
        self.inc_change = False
        self.campoints = []
        self.x_vals = []
        self.y_vals = []

    def analyse(self, z):
        z = z[:,:,1]
        d = (z>self.z0) & (z-self.z0>25)
        self.z0 = z
        xy = np.where(d.ravel())[0]
        if xy.shape[0]>999:
            pass
            #self.laser_xi = 0
            #self.laser_yi = 0
        elif xy.shape[0]>4:
            xy = np.transpose(np.unravel_index(xy, d.shape))
            clust = scan.fit_predict(xy)
            ind = clust==0
            if ind.sum()>1:
                xc = xy[ind,0].mean()
                yc = xy[ind,1].mean()
                xint = int(xc.round())
                yint = int(yc.round())
                self.campoints.append([xint, yint])
                self.x_vals.append(self.laser_xi)
                self.y_vals.append(self.laser_yi)
                #printr("%s %s" % (xint, yint))
                os.system('clear')
                x_plot = np.concatenate(([0,600], xy[:,0]))
                y_plot = np.concatenate(([0,600], 600-xy[:,1]))
                plot(y_plot, x_plot, 20, 20)

        if self.laser_xi > 0 and self.laser_xi < self.npoints - 1:
            self.laser_xi += self.x_inc
        elif self.inc_change:
            self.x_inc = -1 * self.x_inc
            self.laser_xi += self.x_inc
            self.inc_change = False
        elif self.laser_yi < self.npoints - 1:
            self.laser_yi += 1
            self.inc_change = True
        else:
            self.laser_xi = 0
            self.laser_yi = 0
            #self.camera.stop_recording()
        laser_x = self.laser_cal_points[self.laser_xi]
        laser_y = self.laser_cal_points[self.laser_yi]
        open('/dev/spidev0.0', 'wb').write(tohex(laser_x))
        open('/dev/spidev0.1', 'wb').write(tohex(laser_y))

camera = PiCamera(resolution=(640, 480), framerate=3)
camera.awb_mode = 'off'
camera.awb_gains = (1.2, 1.2)
#camera.iso = 400 # 400 500 640 800
camera.color_effects = (128,128)
camera.exposure_mode = 'sports'
camera.shutter_speed = 12000
camera.video_denoise = True

camera.start_preview(fullscreen=False, window=(160,0,640,480))
tracker = Analysis(camera)
camera.start_recording(tracker, format='rgb')
#camera.start_recording('/home/pi/video2.h264')

try:
    camera.wait_recording(9999) # sleep(9999)
except KeyboardInterrupt:
    pass

#GPIO.cleanup()
camera.stop_recording()
camera.stop_preview()


grid_x, grid_y = np.mgrid[0:640, 0:480]
"""
x_map_lin = griddata(campoints, x_vals, (grid_x, grid_y), method='linear')
y_map_lin = griddata(campoints, y_vals, (grid_x, grid_y), method='linear')

not_nan = ~np.isnan(x_map_lin)
campoints2 = np.argwhere(not_nan)
x_vals2 = x_map_lin[not_nan]
y_vals2 = y_map_lin[not_nan]

x_map = griddata(campoints2, x_vals2, (grid_x, grid_y), method='nearest')
y_map = griddata(campoints2, y_vals2, (grid_x, grid_y), method='nearest')
"""
