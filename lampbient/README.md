# Lampbient

A synthesis project driven by a light sensor.

## Motivation

My apartment has a lot of windows, and is surrounded by trees. As a result, across the day my walls receive some enthralling dancing patterns of light. They feel very musical, so this project synthesizes some audio driven by the signal from an [Adafruit VEML7700 Ambient Light Sensor](https://learn.adafruit.com/adafruit-veml7700).

## Notes for future Ryan

- Try as you might, you have to build pyo from source on raspberry pi. `pipenv install` will only work to create the virtualenv.
- Try as it might, a Pi Zero W will not build wxpython.
- I2C must be done in a separate process or audio will stutter. That is why reading from the VEML7700 is done in a separate process.
