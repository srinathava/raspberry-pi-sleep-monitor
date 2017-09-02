import ConfigParser
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
            config = ConfigParser.RawConfigParser()
            config.read(configPath)

            for (key, val) in config.items('Main'):
                if hasattr(self, key):
                    setattr(self, key, val)

    def getConfigFilePath(self):
        return os.path.join(os.environ['HOME'], 'sleep_monitor.cfg')

    def write(self):
       config = ConfigParser.RawConfigParser()

       config.add_section('Main')
       for propName in self.paramNames:
           config.set('Main', propName, str(getattr(self, propName)))

       with open(self.getConfigFilePath(), 'wb') as configfile:
           config.write(configfile)
