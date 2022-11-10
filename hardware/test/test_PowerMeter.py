from hardware.PowerMeter.Keysight import StdErrConfig, PowerMeter

p = PowerMeter()

# print(p.autoRead())

config = StdErrConfig(
    minS = 5,
    maxS = 0,
    stdErr = 1,
    timeout = 1
)

print(config.getUseCase())

print(p.averagingRead(config))

print(p.errorQuery().strip())

