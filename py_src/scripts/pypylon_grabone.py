import pypylon.pylon as py
icam = py.InstantCamera(py.TlFactory.GetInstance().CreateFirstDevice())

icam.Open()
img = icam.GrabOne(4000)

img = img.Array

print(img.shape)
