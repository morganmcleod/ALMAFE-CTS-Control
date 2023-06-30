from TestEquipment.Agilent11713 import AttenuatorSwitchController
import copy

class Attenuator():
    def __init__(self, resource="GPIB0::28::INSTR", reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        # don't reset here because that would set attenuation to 0:
        self.attenuatorSwitchController = AttenuatorSwitchController(resource, reset = False)

        if reset:
            self.reset()

    def reset(self):
        # set attenuation to max:
        self.attenuatorSwitchController.setSwitches([True] * 8)

    def setValue(self, atten: int = 101):
        divisors = (30, 30, 20, 10, 4, 4, 2, 1)
        values = []
        target = copy.copy(atten)
        for div in divisors:
            if target >= div:
                values.append(True)
                target -= div
            else:
                values.append(False)
        self.attenuatorSwitchController.setSwitches(values)



            

    

