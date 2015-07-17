"""
A settings file defined in python code, to make usage simpler than parsing
a configuration file. A simple wrapper object is used over a base dictionary
so we can access keys via attributes rather than dict indexing.
"""

class SettingsDict(dict):
    def __getattr__(self, attr):
        return dict.__getitem__(self, attr)

    def __setattr__(self, attr, value):
        self[attr] = value

# Authentication settings
authentication = SettingsDict({
    "host": "0.0.0.0",
    "port": 56789,
})

# Receiver settings
receiver = SettingsDict({
    "host": "0.0.0.0",
    "port": 56790,
    "cache_size": 10
})

# Relay settings
relay = SettingsDict({
    "targets": [ ('1.1.1.1', 12345) ]
})

# Observer settings
observer = SettingsDict({
    
})
