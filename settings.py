from configparser import ConfigParser

class Settings:
    def __init__(self, config_file='config.ini'):
        self.config = ConfigParser()
        self.config.read(config_file)

    def __getitem__(self, key):
        if key in self.config['DEFAULT']:
            return self.config['DEFAULT'][key]
        elif key in self.config['DATA_CALCULATION']:
            return self.config['DATA_CALCULATION'][key]
        raise KeyError(f"Setting '{key}' not found in configuration.")


settings = Settings()