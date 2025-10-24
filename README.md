# Installation

1. Copy "bootloader" to device:

```shell
uv run mpremote cp main.py :main.py
```

2. Copy libraries to device (answer "y"):

```shell
uv run ota.py sync lib
```

3. Copy program code to device (answer "y"):

```shell
uv run ota.py sync code
```
