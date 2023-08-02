# from ... import settings  # This is relative import so change if directory changes

# config = settings.REDIS_SERVER

# print(config)

from .core import RedisChannelLayer
from dotenv import load_dotenv

load_dotenv()

try:
    from ...settings import CHANNEL_LAYERS
    # print("Channel: ", CHANNEL_LAYERS)
except:
    CHANNEL_LAYERS = {
        "default": {
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],
            },
        },
    }


class ChannelLayerManager:
    """
    Takes a settings dictionary of backends and initialises them on request.
    """

    def __init__(self):
        self.backends = {}
        # print("Layers.py: ", self.configs)
        # FASTAPICHANNEL

    @property
    def configs(self):
        # Lazy load settings so we can be imported
        return CHANNEL_LAYERS  # FASTAPICHANNEL - Returning the config json from main setting file

    def make_backend(self, name):
        """
        Instantiate channel layer.
        """
        config = self.configs[name].get("CONFIG", {}) # Defaulting to local redis ()
        return self._make_backend(name, config)

    def make_test_backend(self, name):
        """
        Instantiate channel layer using its test config.
        """
        try:
            config = self.configs[name]["TEST_CONFIG"]
        except KeyError:
            raise InvalidChannelLayerError("No TEST_CONFIG specified for %s" % name)
        return self._make_backend(name, config)

    def _make_backend(self, name, config):
        # Check for old format config
        if "ROUTING" in self.configs[name]:
            raise InvalidChannelLayerError(
                "ROUTING key found for %s - this is no longer needed in Channels 2."
                % name
            )
        # Load the backend class
        try:
            backend_class = RedisChannelLayer  # import_string(self.configs[name]["BACKEND"])
        except ImportError:
            raise InvalidChannelLayerError(
                "Cannot import RedisChannelLayer"
            )
        # Initialise and pass config
        return backend_class(**config)

    def __getitem__(self, key):
        if key not in self.backends:
            self.backends[key] = self.make_backend(key)
        return self.backends[key]

    def __contains__(self, key):
        return key in self.configs

    def set(self, key, layer):
        """
        Sets an alias to point to a new ChannelLayerWrapper instance, and
        returns the old one that it replaced. Useful for swapping out the
        backend during tests.
        """
        old = self.backends.get(key, None)
        self.backends[key] = layer
        return old


def get_channel_layer(alias='default'):
    try:
        # Default global instance of the channel layer manager
        Redis_layers = ChannelLayerManager()
        return Redis_layers[alias]
    except KeyError:
        return None


# if __name__ == "__main__":
#     REDIS_SERVER = {
#         "hosts": [("127.0.0.1", 6379)],  # IP & port in a tuple
#         "auth": "",  # Blank if not configured
#     }
# else:
#     from ... import settings
#     REDIS_SERVER = settings.REDIS_SERVER
