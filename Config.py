from __future__ import print_function
import configparser
import os

class Config:
    def __init__(self):
        self.paramNames = ('sustainedTime', 'calmTime', 'awakeBpm', 'spo2AlarmThreshold', 'spo2AlarmTime')

        # Time (in seconds) for which we need to see sustained motion to claim that
        # the baby is moving
        self.sustainedTime = 90

        # Time (in seconds) for which if there is no motion, we think the baby has
        # gone back to sleep
        self.calmTime = 30

        # Heart rate (beats per minute) above which we think of the baby as being
        # awake. This is used in addition to any motion detected by the camera
        self.awakeBpm = 140

        # SPO2 threshold below which we want to see an alarm
        self.spo2AlarmThreshold = 94

        # Time (in seconds) for which we need to see the SPO2 fall below
        # `spo2AlarmThreshold` to raise an alarm
        self.spo2AlarmTime = 20

        configPath = self.getConfigFilePath()
        if os.path.isfile(configPath):
            config = self.getConfigParser()
            config.read(configPath, encoding='utf-8')

            for key in config['Main']:
                val = config['Main'][key]
                if hasattr(self, key):
                    setattr(self, key, int(val))

    def getConfigParser(self):
        config = configparser.ConfigParser()
        # The below option preserves case of the key names. Otherwise, they
        # all get converted to lowercase by default (!)
        config.optionxform = str
        return config

    def getConfigFilePath(self):
        return '/home/pi/sleep_monitor.cfg'

    def write(self):
        config = self.getConfigParser()

        config['Main'] = {}
        for propName in self.paramNames:
            propvalstr = str(getattr(self, propName))
            config['Main'][propName] = propvalstr

        with open(self.getConfigFilePath(), 'w') as configfile:
            config.write(configfile)

if __name__ == "__main__":
    config = Config()
    for name in config.paramNames:
        print('%s: %s' % (name, getattr(config, name)))
