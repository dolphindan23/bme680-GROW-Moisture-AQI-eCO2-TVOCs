#!/usr/bin/env python

import time

import bme680
from datetime import datetime
print("""read-all.py - Displays temperature, pressure, humidity, and gas.

Press Ctrl+C to exit!

""")

try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# These calibration data can safely be commented
# out, if desired.

print('Calibration data:')
for name in dir(sensor.calibration_data):

    if not name.startswith('_'):
        value = getattr(sensor.calibration_data, name)

        if isinstance(value, int):
            print('{}: {}'.format(name, value))

# These oversampling settings can be tweaked to
# change the balance between accuracy and noise in
# the data.

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)


print('\n\nInitial reading:')
for name in dir(sensor.data):
    value = getattr(sensor.data, name)

    if not name.startswith('_'):
        print('{}: {}'.format(name, value))
sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

def gas_resistance_to_aqi(gas_resistance):
    """
    Converts gas resistance (Ohms) to an AQI value (1-500).
    
    Parameters:
        gas_resistance (float): The gas resistance in Ohms.
    
    Returns:
        int: AQI value (1-500).
    """
    min_gas_resistance = 10
    max_gas_resistance = 1400000
    gas_resistance = max(min_gas_resistance, min(gas_resistance, max_gas_resistance))
    aqi = 500 - int((gas_resistance - min_gas_resistance) / (max_gas_resistance - min_gas_resistance) * 499)
    return aqi

def aqi_to_co2(aqi):
    """
    Converts AQI to an estimated CO2 concentration in ppm.
    This is an approximation, as AQI and CO2 are not directly correlated.
    
    Parameters:
        aqi (int): The AQI value (1-500).
    
    Returns:
        float: Estimated CO2 concentration in ppm.
    """
    # Rough estimation based on AQI, adjust coefficients as needed
    # We assume AQI 50 corresponds to approximately 400 ppm (clean air)
    # and AQI 500 corresponds to higher CO2 levels (indoor environment)
    base_co2 = 400   # ppm for AQI 50 (typical outdoor clean air)
    max_co2 = 2500   # ppm for AQI 500 (potentially unhealthy levels)
    
    # Scale AQI (1-500) to CO2 (400-2500 ppm)
    estimated_co2 = base_co2 + (max_co2 - base_co2) * (aqi / 500)
    
    return estimated_co2

def gas_resistance_to_tvoc(gas_resistance):
    min_gas_resistance = 10   # Ohms, high pollution
    max_gas_resistance = 1400000   # Ohms, very clean air
    gas_resistance = max(min_gas_resistance, min(gas_resistance, max_gas_resistance))
    
    max_tvoc_ppb = 1000  # Maximum estimated TVOC (ppb) in poor air quality
    min_tvoc_ppb = 0     # Minimum estimated TVOC (clean air)
    
    tvoc = max_tvoc_ppb - ((gas_resistance - min_gas_resistance) / (max_gas_resistance - min_gas_resistance)) * max_tvoc_ppb
    return tvoc

# Initialize the sensor
sensor = bme680.BME680()

# Set up the sensor (you might need to adjust this depending on the BME688 library)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

# Polling loop for live data
try:
    while True:
        if sensor.get_sensor_data():

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Get sensor data
            temperature = sensor.data.temperature  # in Celsius
            pressure = sensor.data.pressure        # in hPa
            humidity = sensor.data.humidity        # in %
            gas_resistance = sensor.data.gas_resistance  # in Ohms
            
            # Convert gas resistance to AQI
            aqi_value = gas_resistance_to_aqi(gas_resistance)
            

            # Estimate CO2 based on AQI
            estimated_co2 = aqi_to_co2(aqi_value)

            estimated_tvoc = gas_resistance_to_tvoc(gas_resistance)
            
            # Print the live sensor data
            print(f"Time: {current_time}")
            print(f"Temperature: {temperature:.2f} °C")
            print(f"Pressure: {pressure:.2f} hPa")
            print(f"Humidity: {humidity:.2f} %")
            print(f"Gas resistance: {gas_resistance} Ohms -> AQI: {aqi_value}")
            print(f"Estimated CO2: {estimated_co2:.2f} ppm")
            print(f"Estimated TVOC: {estimated_tvoc:.2f} ppb")
            print("-" * 40)

        # Delay between polls (e.g., 5 seconds)
        time.sleep(5)

except KeyboardInterrupt:
    print("Polling stopped.")


# Up to 10 heater profiles can be configured, each
# with their own temperature and duration.
# sensor.set_gas_heater_profile(200, 150, nb_profile=1)
# sensor.select_gas_heater_profile(1)

print('\n\nPolling:')
try:
    while True:
        if sensor.get_sensor_data():
            output = '{0:.2f} C,{1:.2f} hPa,{2:.2f} %RH'.format(
                sensor.data.temperature,
                sensor.data.pressure,
                sensor.data.humidity)

            if sensor.data.heat_stable:
                print('{0},{1} Ohms'.format(
                    output,
                    sensor.data.gas_resistance))

            else:
                print(output)

        time.sleep(1)

except KeyboardInterrupt:
    pass




#grow-python moisture.py file

import RPi.GPIO as GPIO

MOISTURE_1_PIN = 23
MOISTURE_2_PIN = 8
MOISTURE_3_PIN = 25
MOISTURE_INT_PIN = 4


class Moisture(object):
    """Grow moisture sensor driver."""

    def __init__(self, channel=1, wet_point=None, dry_point=None):
        """Create a new moisture sensor.

        Uses an interrupt to count pulses on the GPIO pin corresponding to the selected channel.

        The moisture reading is given as pulses per second.

        :param channel: One of 1, 2 or 3. 4 can optionally be used to set up a sensor on the Int pin (BCM4)
        :param wet_point: Wet point in pulses/sec
        :param dry_point: Dry point in pulses/sec

        """
        self._gpio_pin = [MOISTURE_1_PIN, MOISTURE_2_PIN, MOISTURE_3_PIN, MOISTURE_INT_PIN][channel - 1]

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._gpio_pin, GPIO.IN)

        self._count = 0
        self._reading = 0
        self._history = []
        self._history_length = 200
        self._last_pulse = time.time()
        self._new_data = False
        self._wet_point = wet_point if wet_point is not None else 0.7
        self._dry_point = dry_point if dry_point is not None else 27.6
        self._time_last_reading = time.time()
        try:
            GPIO.add_event_detect(self._gpio_pin, GPIO.RISING, callback=self._event_handler, bouncetime=1)
        except RuntimeError as e:
            if self._gpio_pin == 8:
                raise RuntimeError("""Unable to set up edge detection on BCM8.

Please ensure you add the following to /boot/config.txt and reboot:

dtoverlay=spi0-cs,cs0_pin=14 # Re-assign CS0 from BCM 8 so that Grow can use it

""")
            else:
                raise e

        self._time_start = time.time()

    def _event_handler(self, pin):
        self._count += 1
        self._last_pulse = time.time()
        if self._time_elapsed >= 1.0:
            self._reading = self._count / self._time_elapsed
            self._history.insert(0, self._reading)
            self._history = self._history[:self._history_length]
            self._count = 0
            self._time_last_reading = time.time()
            self._new_data = True

    @property
    def history(self):
        history = []

        for moisture in self._history:
            saturation = float(moisture - self._dry_point) / self.range
            saturation = round(saturation, 3)
            history.append(max(0.0, min(1.0, saturation)))

        return history

    @property
    def _time_elapsed(self):
        return time.time() - self._time_last_reading

    def set_wet_point(self, value=None):
        """Set the sensor wet point.

        This is the watered, wet state of your soil.

        It should be set shortly after watering. Leave ~5 mins for moisture to permeate.

        :param value: Wet point value to set in pulses/sec, leave as None to set the last sensor reading.

        """
        self._wet_point = value if value is not None else self._reading

    def set_dry_point(self, value=None):
        """Set the sensor dry point.

        This is the unwatered, dry state of your soil.

        It should be set when the soil is dry to the touch.

        :param value: Dry point value to set in pulses/sec, leave as None to set the last sensor reading.

        """
        self._dry_point = value if value is not None else self._reading

    @property
    def moisture(self):
        """Return the raw moisture level.

        The value returned is the pulses/sec read from the soil moisture sensor.

        This value is inversely proportional to the amount of moisture.

        Full immersion in water is approximately 50 pulses/sec.

        Fully dry (in air) is approximately 900 pulses/sec.

        """
        self._new_data = False
        return self._reading

    @property
    def active(self):
        """Check if the moisture sensor is producing a valid reading."""
        return (time.time() - self._last_pulse) < 1.0 and self._reading > 0 and self._reading < 28

    @property
    def new_data(self):
        """Check for new reading.

        Returns True if moisture value has been updated since last reading moisture or saturation.

        """
        return self._new_data

    @property
    def range(self):
        """Return the range sensor range (wet - dry points)."""
        return self._wet_point - self._dry_point

    @property
    def saturation(self):
        """Return saturation as a float from 0.0 to 1.0.

        This value is calculated using the wet and dry points.

        """
        saturation = float(self.moisture - self._dry_point) / self.range
        saturation = round(saturation, 3)
        return max(0.0, min(1.0, saturation))
