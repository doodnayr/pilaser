import numpy as np
from picamera import PiCamera
from picamera.array import PiRGBAnalysis
from sklearn.cluster import DBSCAN
from binascii import unhexlify, hexlify

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
        self.i = 0
        #self.xc0 = np.float32(0)
        #self.yc0 = np.float32(0)
        self.calibration_mode = True
        self.stable_counter = 0
        self.background_sum = np.zeros((480, 640), dtype=np.uint16)
        self.background = np.array(0)
        self.inaction_counter = 0
        self.t0 = self.camera.timestamp

    def analyse(self, z):
        z = z[:,:,1]
        if self.calibration_mode:
            if np.any((self.z0>z) & (self.z0-z>50)):
                self.stable_counter = 0
                self.background_sum = np.zeros((480, 640), dtype=np.uint16)
            else:
                self.stable_counter += 1
                self.background_sum += z
                if self.stable_counter == 10:
                    self.background = (self.background_sum/self.stable_counter).round(0).astype(np.uint8)
                    self.stable_counter = 0
                    self.background_sum = np.zeros((480, 640), dtype=np.uint16)
                    self.calibration_mode = False
                    printr("done")
            self.z0 = z

        else:
            d = (self.background>z) & (self.background-z>80)
            xy = np.where(d.ravel())[0]
            if xy.shape[0]>999:
                #laseroff
                #GPIO.output(26, 0)
                self.inaction_counter = 99
                self.calibration_mode = True
                printr("calibrating")
            elif xy.shape[0]>4:
                xy = np.transpose(np.unravel_index(xy, d.shape))
                clust = scan.fit_predict(xy)
                ind = clust==0
                if ind.sum()>1:
                    xc = xy[ind,0].mean()
                    yc = xy[ind,1].mean()
                    #xc2 = 2 * xc - self.xc0
                    #yc2 = 2 * yc - self.yc0
                    #xp = np.linspace(self.xc0,xc2,10)
                    #yp = np.linspace(self.yc0,yc2,10)
                    xint = int(xc.round())
                    yint = int(yc.round())
                    open('/dev/spidev0.0', 'wb').write(tohex(1900-xint*3))
                    open('/dev/spidev0.1', 'wb').write(tohex(1900-yint*3))
                    #self.xc0 = xc
                    #self.yc0 = yc
                    printr("%s %s" % (xint, yint))
                if self.inaction_counter>30:
                    #laseron
                    #GPIO.output(26, 1)
                    self.inaction_counter=0
            else:
                self.inaction_counter+=1
                if self.inaction_counter>30:
                    #laseroff
                    #GPIO.output(26, 0)
                    printr('standby')
        self.i += 1

camera = PiCamera(resolution=(640, 480), framerate=20)
camera.awb_mode = 'off'
camera.awb_gains = (1.2, 1.2)
#camera.iso = 400 # 400 500 640 800
camera.color_effects = (128,128)
camera.exposure_mode = 'sports'
camera.shutter_speed = 12000
camera.video_denoise = True

camera.start_preview(fullscreen=False, window=(160,0,640,480))
printr("calibrating")
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
print("%s frames" % tracker.i)
td = (tracker.camera.timestamp - tracker.t0)/1000000
print("%s fps" % (tracker.i/td))

