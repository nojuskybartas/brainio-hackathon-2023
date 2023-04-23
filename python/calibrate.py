from queue import Queue
from main import EEG_Processor, EEG_Recorder

if __name__ == "__main__":
    calibrate_queue = Queue()

    recorder = EEG_Recorder(calibrate_queue, acquisitionDurationInSeconds=25)
    processor = EEG_Processor(
        calibrate_queue, path='calibration.npy', isCalibrating=True)

    recorder.start()
    processor.start()
