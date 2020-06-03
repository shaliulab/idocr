class Top:

    def __init__(self):
        self.settings = {}
        self.settings = {"super_class": "Top"}


class Car(Top):

    settings = {}

    def __init__(self):
        super().__init__()
        self.settings["class"] = "Car"

class Moto(Top):

    def __init__(self):
        super().__init__()
        self.settings["class"] = "Moto"


car = Car()
print(car.settings)
moto = Moto()
print(moto.settings)
print(car.settings)
