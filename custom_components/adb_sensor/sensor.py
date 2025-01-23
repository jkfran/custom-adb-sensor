from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers import template

DOMAIN = "adb_sensor"


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):
    """Set up the ADB Sensor."""
    name = config.get(CONF_NAME, "ADB Sensor")
    adb_entity_id = config.get("adb_entity_id")
    adb_command = config.get("adb_command")
    value_template = config.get("value_template")

    if not adb_entity_id or not adb_command:
        raise ValueError("Missing required configuration for ADB Sensor")

    async_add_entities(
        [ADBSensor(hass, name, adb_entity_id, adb_command, value_template)]
    )


class ADBSensor(SensorEntity):
    """Representation of an ADB Sensor."""

    def __init__(self, hass, name, adb_entity_id, adb_command, value_template):
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._state = None
        self._adb_entity_id = adb_entity_id
        self._adb_command = adb_command
        self._value_template = value_template
        self._attributes = {}

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
        # Call the androidtv.adb_command service
        await self.hass.services.async_call(
            "androidtv",
            "adb_command",
            {
                "entity_id": self._adb_entity_id,
                "command": self._adb_command,
            },
            blocking=True,
        )

        # Retrieve the entity state
        entity_state = self.hass.states.get(self._adb_entity_id)

        if entity_state is None:
            # Handle the case where the ADB entity does not exist
            self._state = "Entity Not Found"
            self._attributes = {
                "error": f"Entity {self._adb_entity_id} not found"
            }
            return

        # Retrieve the adb_response from the entity's state attributes
        adb_response = entity_state.attributes.get("adb_response", "")

        if adb_response:
            # Use the template to parse the value if provided
            if self._value_template:
                self._state = await self._render_template(adb_response)
            else:
                self._state = adb_response.strip()
            self._attributes = {"adb_response": adb_response}
        else:
            self._state = "Unknown"
            self._attributes = {"adb_response": "No response"}

    async def _render_template(self, adb_response: str) -> str:
        """Render the value using the provided template asynchronously."""
        try:
            # Create the Template object, passing in 'hass' so it has access
            # to all of Home Assistant's template features.
            tpl = template.Template(self._value_template, self.hass)
            rendered = await tpl.async_render({"value": adb_response})
            return rendered.strip() or "Empty Template Result"
        except Exception as e:
            self._attributes["error"] = f"Template rendering error: {e}"
            return "Template Error"
