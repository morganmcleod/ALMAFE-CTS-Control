from CTSDevices.MotorControl.GalilDMCSocket import MotorController, MotorStatus, Position

m = MotorController()
m.setup()

print(m.getMotorStatus())
p = m.getPosition()
print(p)

d = Position(x=20,y=20,z=30)
t = m.estimateMoveTime(p, d)
print(t)

m.SetNextPos(d)
m.startMove(False)
print(m.waitForPosition(t))
