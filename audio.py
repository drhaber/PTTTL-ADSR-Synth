"""
This module is based on ptttl:
https://github.com/eriknyquist/ptttl

Copyright (c) 2018 Erik Nyquist

Licensed under the MIT License.
"""

import os
import wave
import math
import logging

from ptttlwadsr_parser import PTTTLParser, PTTTLData, is_instrument_name, load_instrument, get_cfg
from ptttlwadsr_parser import default_bpm, default_octave, default_wadsr
from mixer import Mixer

# Initialize logger for Home Assistant compatibility
_LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 44100

is_debug = get_cfg("debug")

def get_ptttl_output_path(ptttl_string, directory="/tmp"):
    """
    Generates a unique filename based on the PTTTL name also handles debug.
    """
    # Extract the name part (before the first colon) or use 'ptttl' as fallback
    name_prefix = ptttl_string.split(':')[0].strip().replace('/', '_') or "ptttl_wadsr"
    
    if is_debug:
        _LOGGER.warning("Debug mode is ON: Output will be saved to a fixed filename, PTTTL_WADSR_debug.wav, overwrites will occur.")
        return os.path.join(directory, "PTTTL_WADSR_debug.wav")
    else:
        return os.path.join(directory, f"{name_prefix}.wav")
    
    #return os.path.join(directory, f"{name_prefix}_{int(time.time())}.wav") 
    
    #will be implented later as the syntax for HASS "play Service" these files will autodelete after playback so no need to worry about cleanup
    #Using timestamp for uniqueness will ensure that multiple calls to play PTTTL strings won't overwrite each other's output

def _generate_samples(parsed, amplitude):
    """
    Generates audio samples using per-track ADSR and Waveform data.
    """
    mixer = Mixer(SAMPLE_RATE, amplitude)
    
    # Map string identifiers to tones library constants
    wave_map = {
        's': 3, # SAWTOOTH_WAVE
        'q': 1, # SQUARE_WAVE
        't': 2, # TRIANGLE_WAVE
        'i': 0, # SINE_WAVE
    }

    def unpack_patch(patch):
        p = [x.strip() for x in patch.split(',')]
        if len(p) != 7:
            raise ValueError(f"Expected 7 fields, got {len(p)}")
        # Return: wave_key, a, d, s, r, gain, octave_offset
        return p[0], float(p[1])/1000.0, float(p[2])/1000.0, float(p[3])/1000.0, float(p[4])/1000.0, float(p[5]), int(p[6])

    for i, track in enumerate(parsed.tracks):
        try:
            wave_key, a, d, s, r, gain, octave_offset = unpack_patch(parsed.wadsr[i])
        except (ValueError, IndexError):
            _LOGGER.warning("Track %d patch invalid (%s), falling back to default.", i, parsed.wadsr[i])
            wave_key, a, d, s, r, gain, octave_offset = unpack_patch(default_wadsr)

        wavetype = wave_map.get(wave_key)
        if wavetype is None:
            # Ensure fallback is the integer constant, not the string key
            fallback_key = get_cfg("fallback_instrument", "wave")
            wavetype = wave_map.get(fallback_key, 1)  # Default to Square if config is also broken
            _LOGGER.warning("Invalid wavetype '%s', defaulting to '%s'", wave_key, fallback_key)

        mixer.create_track(i, wavetype=wavetype, 
                           attack=a, decay=d, sustain=s, release=r, gain=gain)

        for note in track:
            if note.pitch <= 0.0:
                mixer.add_silence(i, duration=note.duration)
            else:
                pitch = note.pitch * math.pow(2, octave_offset) if octave_offset != 0 else note.pitch
                mixer.add_tone(i, frequency=pitch, duration=note.duration,
                               vibrato_frequency=note.vibrato_frequency,
                               vibrato_variance=note.vibrato_variance)
    return mixer

def ptttl_to_wav_samples(ptttl_data, amplitude=0.5):
    """
    Convert a PTTTL source string to a serialized list of audio samples.
    """
    parser = PTTTLParser()
    data = parser.parse(ptttl_data)
    return _generate_samples(data, amplitude).mix().serialize()

def ptttl_to_wav(ptttl_data, wav_filename, amplitude=0.5):
    """
    Convert a PTTTL source string to audio data and write to a .wav file.
    """
    parser = PTTTLParser()
    data = parser.parse(ptttl_data)
    mixer = _generate_samples(data, amplitude)
    mixer.write_wav(wav_filename)