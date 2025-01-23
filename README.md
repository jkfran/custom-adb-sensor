# Custom ADB Sensor

**Custom ADB Sensor** is a highly flexible [Home Assistant](https://www.home-assistant.io/) custom component that allows you to create sensors based on the output of ADB commands. Use it to monitor various aspects of your Android TV, Fire TV, or any ADB-compatible device. This repository includes a sample configuration for detecting the current app on Android TV/Fire TV by parsing the `mCurrentFocus` output.

## Features

- Supports any ADB command to create custom sensors tailored to your needs.
- Designed for easy integration with the `androidtv.adb_command` service.
- Provides raw ADB response data as state attributes for debugging or additional logic.
- Includes an example for detecting the currently open app on Android TV/Fire TV.

## Installation

### Manual Installation

1. Clone or download this repository.
2. Copy the `custom_adb_sensor` folder into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

### HACS Installation (Planned)

Stay tuned for future HACS compatibility!

## Configuration

Add a sensor configuration to your `configuration.yaml` file. Here's the example for detecting the currently open app on an Android TV/Fire TV device:

```yaml
sensor:
  - platform: custom_adb_sensor
    name: Fire TV Current App
    adb_entity_id: media_player.fire_tv_192_168_1_202
    adb_command: "dumpsys window | grep mCurrentFocus"
```

### Parameters

| Parameter       | Description                                                                 | Required | Default       |
|-----------------|-----------------------------------------------------------------------------|----------|---------------|
| `name`          | The name of the sensor.                                                    | Yes      | `ADB Sensor`  |
| `adb_entity_id` | The entity ID of the Android TV/Fire TV media player.                      | Yes      | None          |
| `adb_command`   | The ADB command to run.                                                    | Yes      | None          |

## Example Use Case: Detect Current App

The example above will run the `dumpsys window | grep mCurrentFocus` command to extract the `mCurrentFocus` value from the ADB response and display the currently open app as the sensor state.

## Advanced Configuration

You can extend the sensor to support other ADB commands. For example:

### Monitor Lockscreen Status
```yaml
sensor:
  - platform: custom_adb_sensor
    name: Fire TV Lockscreen Status
    adb_entity_id: media_player.fire_tv_192_168_1_202
    adb_command: "dumpsys window | grep mDreamingLockscreen"
```

The state will update to "Locked" or "Unlocked" based on the ADB output.

### Custom Logic
The component can be adapted to parse custom data from any ADB command output. Review the `sensor.py` file for details on how to add your own parsing logic.

## Debugging

The raw ADB response is stored in the `adb_response` attribute of the sensor for easy debugging or creating templates.

## Contribution

Contributions are welcome! Please fork this repository, create a feature branch, and submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
