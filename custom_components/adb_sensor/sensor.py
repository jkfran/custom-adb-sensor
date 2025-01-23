import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.helpers import template

DOMAIN = "adb_sensor"
DEFAULT_NAME = "ADB Sensor"
DEFAULT_SCAN_INTERVAL = 30  # seconds

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 1) PLATFORM SCHEMA
# ------------------------------------------------------------------
# We extend Home Assistant's default PLATFORM_SCHEMA to handle:
#   - name (optional, default "ADB Sensor")
#   - scan_interval (optional, default 30s)
#   - adb_entity_id (required)
#   - adb_command (required)
#   - value_template (optional)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
        vol.Required("adb_entity_id"): cv.string,
        vol.Required("adb_command"): cv.string,
        vol.Optional("value_template"): cv.string,
    }
)


# ------------------------------------------------------------------
# 2) SETUP PLATFORM
# ------------------------------------------------------------------
# Called by Home Assistant to set up the sensor platform.
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the ADB Sensor platform."""
    name = config[CONF_NAME]
    scan_interval_seconds = config[CONF_SCAN_INTERVAL]
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
        scan_interval=scan_interval_seconds,
    )

    # `update_before_add=True` means it calls async_update() once before adding,
    # so you see an initial state quickly.
    async_add_entities([sensor], update_before_add=True)


# ------------------------------------------------------------------
# 3) ADB SENSOR ENTITY
# ------------------------------------------------------------------
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
        self._scan_interval = scan_interval  # in seconds

    @property
    def should_poll(self):
        """
        Return True to let Home Assistant schedule regular updates
        based on `scan_interval`.
        """
        return True

    @property
    def scan_interval(self):
        """
        Return a timedelta for Home Assistant to control how often
        async_update() is polled.
        """
        return timedelta(seconds=self._scan_interval)

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
        """
        Fetch the state by running the ADB command.
        Home Assistant calls this automatically at the scan_interval.
        """
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
