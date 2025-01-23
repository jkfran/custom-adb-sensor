import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.helpers import template

DOMAIN = "adb_sensor"
DEFAULT_NAME = "ADB Sensor"
# Default interval of 30 seconds as a timedelta
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

# 1) PLATFORM SCHEMA
#    - Use cv.time_period to ensure we get a timedelta for `scan_interval`
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
        vol.Required("adb_entity_id"): cv.string,
        vol.Required("adb_command"): cv.string,
        vol.Optional("value_template"): cv.string,
    }
)


# 2) SETUP PLATFORM
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the ADB Sensor platform."""
    name = config[CONF_NAME]
    scan_interval_td = config[CONF_SCAN_INTERVAL]  # This is a timedelta
    adb_entity_id = config["adb_entity_id"]
    adb_command = config["adb_command"]
    value_template = config.get("value_template")

    # Create and add our sensor entity
    sensor = ADBSensor(
        hass=hass,
        name=name,
        adb_entity_id=adb_entity_id,
        adb_command=adb_command,
        value_template=value_template,
        scan_interval=scan_interval_td,
    )

    # `update_before_add=True` triggers one update before adding to Home Assistant
    async_add_entities([sensor], update_before_add=True)


# 3) ADB SENSOR ENTITY
class ADBSensor(SensorEntity):
    """Representation of an ADB Sensor."""

    def __init__(
        self,
        hass,
        name,
        adb_entity_id,
        adb_command,
        value_template,
        scan_interval,
    ):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self._attributes = {}
        self._adb_entity_id = adb_entity_id
        self._adb_command = adb_command
        self._value_template = value_template

        # Store the user-defined scan_interval as a timedelta
        # (Home Assistant expects a timedelta in scan_interval)
        self._scan_interval = scan_interval

    @property
    def should_poll(self):
        """Return True to let Home Assistant poll at our scan_interval."""
        return True

    @property
    def scan_interval(self):
        """
        Return the polling interval as a timedelta.
        Home Assistant will poll `async_update()` at this interval.
        """
        return self._scan_interval

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch the state by running the ADB command."""
        if not self.hass.services.has_service("androidtv", "adb_command"):
            _LOGGER.warning(
                "Service 'androidtv.adb_command' is not available. Skipping update."
            )
            return

        try:
            # 1) Call the androidtv.adb_command service
            await self.hass.services.async_call(
                "androidtv",
                "adb_command",
                {
                    "entity_id": self._adb_entity_id,
                    "command": self._adb_command,
                },
                blocking=True,
            )

            # 2) Retrieve the updated entity state for the ADB entity
            entity_state = self.hass.states.get(self._adb_entity_id)

            if entity_state is None:
                # Handle the case where the ADB entity does not exist
                self._state = "Entity Not Found"
                self._attributes = {
                    "error": f"Entity '{self._adb_entity_id}' not found"
                }
                return

            # 3) Extract the adb_response from the entity's attributes
            adb_response = entity_state.attributes.get("adb_response", "")

            if adb_response:
                # If a template is provided, render it; otherwise, use the raw response
                if self._value_template:
                    self._state = await self._render_template(adb_response)
                else:
                    self._state = adb_response.strip()

                self._attributes = {"adb_response": adb_response}
            else:
                self._state = "Unknown"
                self._attributes = {"adb_response": "No response"}

        except Exception as e:
            _LOGGER.error(f"Error while running ADB command: {e}")
            self._state = "Error"
            self._attributes = {"error": str(e)}

    async def _render_template(self, adb_response: str) -> str:
        """Render the value using the provided template asynchronously."""
        try:
            tpl = template.Template(self._value_template, self.hass)
            rendered = tpl.async_render({"value": adb_response})
            return rendered.strip() or "Empty Template Result"
        except Exception as e:
            _LOGGER.error(f"ADB sensor - Template rendering error: {e}")
            self._attributes["error"] = f"Template rendering error: {e}"
            return "Template Error"
