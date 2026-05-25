from setuptools import setup

setup(
    name="ptttlis_play",
    version="0.1",
    py_modules=["ptttlwadsr_parser", "audio", "play", "tone", "mixer"],
    entry_points={
        "console_scripts": [
            "play=play:main",
        ],
    },
)