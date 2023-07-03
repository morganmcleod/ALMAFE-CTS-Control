from TestEquipment.Agilent11713 import AttenuatorSwitchController
import copy

class Attenuator():
    MAX_ATTENUATION = 121
    DIVISORS = (40, 40, 20, 10, 4, 4, 2, 1)

    def __init__(self, resource="GPIB0::28::INSTR", reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        # don't reset here because that would set attenuation to 0:
        self.switchController = AttenuatorSwitchController(resource, reset = False)

        if reset:
            self.reset()

    def reset(self):
        # set attenuation to max:
        self.switchController.setSwitches([True] * 10)

    def setValue(self, atten: int = MAX_ATTENUATION):
        if atten < 0 or atten > self.MAX_ATTENUATION:
            atten = self.MAX_ATTENUATION
        
        remaining = copy.copy(atten)
        switches = []

        for div in self.DIVISORS:
            if remaining < div:
                switches.append(False)
            else:
                remaining -= div
                switches.append(True)

        switches.append(False)
        switches.append(False)
        self.switchController.setSwitches(switches)



            

    

