from Measure.Shared.MeasurementStatus import MeasurementStatus

def measurementStatus() -> MeasurementStatus:
    try:
        ret = measurementStatus.instance
    except:
        ret = measurementStatus.instance = MeasurementStatus()
    return ret
