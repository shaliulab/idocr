from pypylon import pylon
from pypylon import genicam
import sys
import ipdb

try:
    cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    print('Sucess!')
except genicam._genicam.RuntimeException as e:
    print('Try again')
    sys.exit(1)

cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
grabResult = cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
img = grabResult.Array

ipdb.set_trace()
