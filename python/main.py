from threading import Thread, Event
from queue import Queue
import numpy as np
import spkit as sp
from scipy import signal
import UnicornPy
from UnicornPy import Unicorn
import numpy as np
from scipy.stats import ranksums


class EEG_Recorder(Thread):

    def __init__(self, eeg_data_queue: Queue, bufferLength:int=250, acquisitionDurationInSeconds:int=-1, writeDataTo:str="data.csv", device=None):
        super().__init__()
        self.data_queue = eeg_data_queue
        self.bufferLength = bufferLength
        self.writeDataTo = writeDataTo
        self.frameLength = 1
        self.acquisitionDurationInSeconds = acquisitionDurationInSeconds
        self.device = device


    def run(self):
        TestsignaleEnabled = False
        global deviceName

        try:
            deviceList = UnicornPy.GetAvailableDevices(True)

            if len(deviceList) <= 0 or deviceList is None:
                raise Exception(
                    "No device available. Please pair with a Unicorn first.")

            # Open device.
            # -------------------------------------------------------------------------------------
            print()
            print("Trying to connect to '%s'." % deviceList[0])
            device = UnicornPy.Unicorn(deviceList[0])
            print("Connected to '%s'." % deviceList[0])
            print()

            self.device = deviceList[0]

            # Create a file to store data.
            file = open(self.writeDataTo, "wb")

            # Initialize acquisition members.
            # -------------------------------------------------------------------------------------
            numberOfAcquiredChannels = device.GetNumberOfAcquiredChannels()
            configuration = device.GetConfiguration()

            # Print acquisition configuration
            print("Acquisition Configuration:")
            print("Sampling Rate: %i Hz" % UnicornPy.SamplingRate)
            print("Frame Length: %i" % self.frameLength)
            print("Number Of Acquired Channels: %i" % numberOfAcquiredChannels)
            print("Data Acquisition Length: %i s" %
                  self.acquisitionDurationInSeconds)
            print()

            # Allocate memory for the acquisition buffer.
            receiveBufferBufferLength = self.frameLength * numberOfAcquiredChannels * 4
            receiveBuffer = bytearray(receiveBufferBufferLength)

            try:
                # Start data acquisition.
                # -------------------------------------------------------------------------------------
                device.StartAcquisition(TestsignaleEnabled)
                print("Data acquisition started.")

                # Calculate number of get data calls.
                numberOfGetDataCalls = int(
                    self.acquisitionDurationInSeconds * UnicornPy.SamplingRate / self.frameLength)

                # Limit console update rate to max. 25Hz or slower to prevent acquisition timing issues.
                consoleUpdateRate = int(
                    (UnicornPy.SamplingRate / self.frameLength) / 25.0)
                if consoleUpdateRate == 0:
                    consoleUpdateRate = 1

                # Acquisition loop.
                # -------------------------------------------------------------------------------------
                databuffer = np.zeros((0, 8))
                i = 0
                while True:
                # for i in range(0, numberOfGetDataCalls):
                    if (self.acquisitionDurationInSeconds != -1):
                        i += 1
                        if i >= numberOfGetDataCalls:
                            break
                    # Receives the configured number of samples from the Unicorn device and writes it to the acquisition buffer.
                    device.GetData(self.frameLength, receiveBuffer,
                                   receiveBufferBufferLength)

                    # Convert receive buffer to numpy float array
                    data = np.frombuffer(
                        receiveBuffer, dtype=np.float32, count=numberOfAcquiredChannels * self.frameLength)
                    data = np.reshape(
                        data, (self.frameLength, numberOfAcquiredChannels))[:, :8]
                    np.savetxt(file, data, delimiter=',',
                               fmt='%.3f', newline='\n')

                    databuffer = np.append(databuffer, data, axis=0)

                    if len(databuffer) >= self.bufferLength:
                        self.data_queue.put(databuffer)
                        databuffer = np.zeros((0, 8))

                # Stop data acquisition.
                # -------------------------------------------------------------------------------------
                device.StopAcquisition()
                print()
                print("Data acquisition stopped.")

            except UnicornPy.DeviceException as e:
                print(e)
            except Exception as e:
                print("An unknown error occured. %s" % e)
            finally:
                # release receive allocated memory of receive buffer
                del receiveBuffer

                # close file
                file.close()

                # Close device.
                # -------------------------------------------------------------------------------------
                del device
                print("Disconnected from Unicorn")

        except Unicorn.DeviceException as e:
            print(e)
        except Exception as e:
            print("An unknown error occured. %s" % e)

        input("\n\nPress ENTER key to exit")


class EEG_Processor(Thread):
    def __init__(self, data_queue: Queue, path: str = None, isCalibrating=False, p_value_event:Event = None, threshold = 0.05):
        super().__init__()
        self.fs = 250
        self.data_queue = data_queue
        self.path = path
        self.isCalibrating = isCalibrating
        # self.p_value_queue = p_value_queue
        self.p_value_event = p_value_event
        self.threshold = threshold

        if not isCalibrating:
            try:
                self.baseline_asymmetry_index = np.load(path)[0]
            except Exception as e:
                raise Exception("You must provide a calibration path. Please calibrate the device first")


    def run(self):
        while True:
            # Get data from queue
            data = self.data_queue.get()

            # Process data
            processed_data = self.process(data)

            # Save baseline index in CSV file if path is not None
            if self.isCalibrating:
                # with open(self.path, mode='w') as file:
                # file.write(str(processed_data["ai"]))
                np.save(self.path, [processed_data["ai"]])
                # np.savetxt(file, [processed_data["ai"]], fmt='%0.20f')
                print(np.mean(processed_data["ai"]))
            else:
                # print(processed_data["ai"][0],
                #       self.baseline_asymmetry_index[0])
                z_stat, p_val = ranksums(
                    processed_data['ai'], self.baseline_asymmetry_index)
                print("p-value:", p_val)
                if p_val < self.threshold:
                    self.p_value_event.set()
                else:
                    self.p_value_event.clear()

            # Send processed data to output queue
            self.data_queue.task_done()

    def process(self, rows):
        Xf = sp.filter_X(rows, band=[0.5],
                         btype='highpass', fs=self.fs, verbose=0)

        # define alpha bandpass filter
        f_low = 8  # lower cutoff frequency
        f_high = 13  # upper cutoff frequency
        order = 4  # filter order
        b, a = signal.butter(
            order, [2*f_low/self.fs, 2*f_high/self.fs], btype='bandpass')

        # Apply the filter to the EEG data
        filtered_data = signal.filtfilt(b, a, Xf, padlen=1)

        # Perform the Fourier transform
        fft_data = np.fft.fft(filtered_data)

        # Calculate the frequencies for each data point in the FFT
        # freqs = np.fft.fftfreq(len(filtered_data), d=1/250)

        # Take the absolute value of the FFT data
        abs_fft_data = np.abs(fft_data)

        # Only keep the positive frequencies (since FFT produces a mirrored spectrum)
        # positive_freqs = freqs[:len(filtered_data)//2]
        abs_fft_data = abs_fft_data[:len(filtered_data)//2]

        # attribute left hemisphere channels: 2, 6
        left_channels = abs_fft_data[:, [1, 5]]
        x_left1 = left_channels[:, 0]
        x_left2 = left_channels[:, 1]

        # attribute right hemisphere channels: 4, 7
        right_channels = abs_fft_data[:, [3, 6]]
        x_right1 = right_channels[:, 0]
        x_right2 = right_channels[:, 1]

        # calculate asymmetry
        alpha_power_left = np.mean([x_left1, x_left2], axis=0)
        alpha_power_right = np.mean([x_right1, x_right2], axis=0)

        asymmetry_index = (alpha_power_right - alpha_power_left) / \
            (alpha_power_right + alpha_power_left)

        r_data = {
            "ai": asymmetry_index
        }
        return r_data


if __name__ == "__main__":
    EEG_data_queue = Queue()

    recorder = EEG_Recorder(EEG_data_queue, bufferLength=250)
    processor = EEG_Processor(EEG_data_queue, path="calibration.npy")

    recorder.start()
    processor.start()
