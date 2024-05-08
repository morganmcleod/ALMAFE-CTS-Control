from measProcedure.Scripted import CTSNoiseTemp, CartTest, TestTypeIds

NT = CTSNoiseTemp()

settings = NT.get_nt_common_settings()
print(settings)

settings = NT.get_nt_settings()
print(settings)
settings.loStart = 221
settings.loStop = 225
settings.loStep = 1
settings.ifStart = 3.0
settings.ifStop = 20.0
settings.ifStep = 0.1
NT.set_nt_settings(settings)

cartTest = CartTest(
    configId = 629,
    fkTestType = TestTypeIds.NOISE_TEMP,
    description = 'scripted stepping test',
    operator = 'MM'
)

NT.start(cartTest)
NT.set_modes(if_mode = 'step', chopper_mode = 'spin')
done = False
while not done:
    success, msg = NT.set_lo(step = 'next')
    print(msg)

    ifDone = False
    while success and not ifDone:
        success, msg = NT.set_if(step = 'next')

        if success:
            success, msg = NT.check_cold_load()

        if success:
            success, msg = NT.measure_ir()
    
        if success:
            success, msg = NT.measure_nt()

        ifDone = not success
    done = not success

NT.stop()
