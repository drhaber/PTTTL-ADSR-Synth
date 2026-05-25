"""
This module is based on ptttl:
https://github.com/eriknyquist/ptttl

Copyright (c) 2018 Erik Nyquist

Licensed under the MIT License.
"""

import sys
import os
import yaml
import math
import logging

_LOGGER = logging.getLogger(__name__)

#config parser for default values
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configuration.yaml")
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

def get_cfg(key, subkey=None):
    if subkey: return CONFIG.get(key, {}).get(subkey)
    return CONFIG.get(key)

def load_instrument(instrument_name):
    """
    Load an instrument definition from the instruments/ directory.
    Returns a dict with 'layers' key containing list of layer definitions,
    or None if the instrument file doesn't exist.
    """
    instruments_dir = os.path.join(os.path.dirname(__file__), "instruments")
    instrument_path = os.path.join(instruments_dir, f"{instrument_name}.yaml")
    
    if not os.path.exists(instrument_path):
        return None
    
    with open(instrument_path, "r") as f:
        return yaml.safe_load(f)

def is_instrument_name(patch_spec):
    """
    Check if a patch specification is an instrument name rather than WADSR values.
    Instrument names are single words without commas.
    WADSR specs contain commas (e.g., "i,0,50,1000,200,0.8").
    """
    return patch_spec and ',' not in patch_spec and patch_spec.isalpha()

# Initialize variables straight from your conffiguration.yaml file up front as the fallback
default_bpm = get_cfg("global_defaults", "bpm")
default_duration = get_cfg("global_defaults", "duration")
default_octave = get_cfg("global_defaults", "octave")
default_vfreq = get_cfg("global_defaults", "vibrato_freq_hz")
default_vvar = get_cfg("global_defaults", "vibrato_var_hz")

w = get_cfg("fallback_instrument", "wave")
a = get_cfg("fallback_instrument", "attack")
d = get_cfg("fallback_instrument", "decay")
s = get_cfg("fallback_instrument", "sustain")
r = get_cfg("fallback_instrument", "release")
g = get_cfg("fallback_instrument", "gain")
o = get_cfg("fallback_instrument", "octave_offset")

default_wadsr = f"{w},{a},{d},{s},{r},{g},{o}"

NOTES = {
    "c": 261.625565301,
    "c#": 277.182630977,
    "db": 277.182630977,
    "d": 293.664767918,
    "d#": 311.126983723,
    "eb": 311.126983723,
    "e": 329.627556913,
    "e#": 349.228231433,
    "f": 349.228231433,
    "f#": 369.994422712,
    "gb": 369.994422712,
    "g": 391.995435982,
    "g#": 415.30469758,
    "ab": 415.30469758,
    "a": 440.0,
    "a#": 466.163761518,
    "bb": 466.163761518,
    "b": 493.883301256
}

class PTTTLSyntaxError(Exception): pass
class PTTTLValueError(Exception): pass

def _invalid_note_duration(orig): raise PTTTLValueError(f"invalid note duration '{orig}'")
def _invalid_note(orig): raise PTTTLValueError(f"invalid note '{orig}'")
def _invalid_octave(note): raise PTTTLValueError(f"invalid octave in note '{note}'")
def _invalid_vibrato(vdata): raise PTTTLValueError(f"invalid vibrato settings: '{vdata}'")

def _ignore_line(line):
    return (line == "") or line.startswith('!') or line.startswith('#')

class PTTTLNote(object):
    """
    Represents a single musical note, with a pitch and duration.
    """
    def __init__(self, pitch, duration, vfreq=None, vvar=None):
        self.pitch = pitch
        self.duration = duration
        self.vibrato_frequency = vfreq
        self.vibrato_variance = vvar

    def has_vibrato(self):
        if None in [self.vibrato_frequency, self.vibrato_variance]:
            return False
        if 0.0 in [self.vibrato_frequency, self.vibrato_variance]:
            return False
        return (self.vibrato_frequency > 0.0) and (self.vibrato_variance > 0.0)

    def __str__(self):
        ret = f"{self.__class__.__name__}(pitch={self.pitch:.4f}, duration={self.duration:.4f}"
        if self.has_vibrato():
            ret += f", vibrato={self.vibrato_frequency:.1f}:{self.vibrato_variance:.1f}"
        return ret + ")"

    def __repr__(self):
        return self.__str__()


class PTTTLData(object):
    """
    Represents song data extracted from a PTTTLIS file.
    Tracks parallel note listings and data-driven patch assignments.
    """
    def __init__(self, bpm=None, octave=None, duration=None,
                 vibrato_freq=None, vibrato_var=None):
        self.bpm = bpm if bpm is not None else default_bpm
        self.octave = octave if octave is not None else default_octave
        self.duration = duration if duration is not None else default_duration
        self.vibrato_freq = vibrato_freq if vibrato_freq is not None else default_vfreq
        self.vibrato_var = vibrato_var if vibrato_var is not None else default_vvar
        self.tracks = []
        self.wadsr = []

    def add_track(self, notes, patch=None):
        self.tracks.append(notes)
        self.wadsr.append(patch if patch is not None else default_wadsr)

    def __str__(self):
        # Updated to reference self.wadsr instead of the now-defunct self.instruments
        return f"{self.__class__.__name__}(Tracks: {len(self.tracks)}, Patches: {len(self.wadsr)})"

    def __repr__(self):
        return self.__str__()


class PTTTLParser(object):
    """
    Converts PTTTLIS 4-field source text to an orchestrated PTTTLData object.
    """
    def _is_valid_octave(self, octave):
        return octave >= 0 and octave <= 8

    def _is_valid_duration(self, duration):
        return duration in [1, 2, 4, 8, 16, 32]

    def _parse_config_line(self, conf):
        bpm, default, octave, vfreq, vvar = default_bpm, default_duration, default_octave, default_vfreq, default_vvar
        # Split comma-separated values and remove empty strings
        stripped = [f.strip() for f in conf.split(',')]
        values = [f for f in stripped if f != ""]

        # If the configuration line is completely empty, it just returns all the system defaults safely
        if not values:
            return bpm, default, octave, vfreq, vvar

        for value in values:
            fields = value.split('=')
            if len(fields) != 2:
                continue  # Bad formatting (missing '='): skip it and keep the default

            key = fields[0].strip().lower()
            val = fields[1].strip().lower()

            if not key or not val:
                continue  # Missing key or value: skip it and keep the default

            try:
                if key == 'b':
                    bpm = int(val)
                elif key == 'd':
                    test_dur = int(val)
                    if self._is_valid_duration(test_dur):
                        default = test_dur
                elif key == 'o':
                    test_oct = int(val)
                    if self._is_valid_octave(test_oct):
                        octave = test_oct
                elif key == 'f':
                    vfreq = float(val)
                elif key == 'v':
                    vvar = float(val)
            except ValueError:
                pass  # Parsing failed (e.g. text instead of a number): ignore and keep the default

        return bpm, default, octave, vfreq, vvar

    def _note_time_to_secs(self, note_time, bpm):
        whole = (60.0 / float(bpm)) * 4.0
        return whole / float(note_time)

    def _parse_note(self, string, bpm, default, octave, vfreq, vvar):
        i = 0
        orig = string
        sawdot = False
        dur = default
        vibrato_freq = None
        vibrato_var = None
        vdata = None

        fields = string.split('v')
        if len(fields) == 2:
            string = fields[0]
            vdata = fields[1]

        if len(string) == 0:
            raise PTTTLSyntaxError("Missing notes after comma")

        while i < len(string) and string[i].isdigit():
            if i > 1:
                _invalid_note_duration(orig)
            i += 1

        if i > 0:
            try:
                dur = int(string[:i])
            except ValueError:
                _invalid_note_duration(orig)
        else:
            if not string[0].isalpha():
                _invalid_note(orig)

        duration = self._note_time_to_secs(dur, bpm)
        string = string[i:]

        i = 0
        while i < len(string) and (string[i].isalpha() or string[i] == '#'):
            i += 1

        note = string[:i].strip().lower()
        if note == "":
            _invalid_note(orig)

        if i < len(string) and string[i] == '.':
            i += 1
            sawdot = True

        string = string[i:].strip()
        i = 0

        if note == 'p':
            pitch = -1
        else:
            if note not in NOTES:
                _invalid_note(orig)

            raw_pitch = NOTES[note]

            while i < len(string) and string[i].isdigit():
                i += 1

            if string[:i] != '':
                try:
                    octave = int(string[:i])
                except ValueError:
                    _invalid_octave(note)

                if not self._is_valid_octave(octave):
                    _invalid_octave(note)

            if octave < 4:
                pitch = raw_pitch / math.pow(2, (4 - octave))
            elif octave > 4:
                pitch = raw_pitch * math.pow(2, (octave - 4))
            else:
                pitch = raw_pitch

            string = string[i:].strip()
            i = 0

        if sawdot or ((i < len(string)) and string[-1] == '.'):
            duration += (duration / 2.0)

        if vdata is not None:
            if vdata.strip() == '':
                vibrato_freq = vfreq
                vibrato_var = vvar
            else:
                fields = vdata.split('-')
                if len(fields) == 2:
                    try:
                        vibrato_freq = float(fields[0])
                        vibrato_var = float(fields[1])
                    except:
                        _invalid_vibrato(vdata)
                elif len(fields) == 1:
                    try:
                        vibrato_freq = float(vdata)
                    except:
                        _invalid_vibrato(vdata)
                    vibrato_var = vvar

        return PTTTLNote(pitch, duration, vibrato_freq, vibrato_var)

    def _parse_notes(self, track_list, wadsr_list, bpm, default, octave, vfreq, vvar):
        ret = PTTTLData(bpm, octave, default, vfreq, vvar)
        
        for i, track in enumerate(track_list):
            if track.strip() == "": continue
            
            buf = []
            for note_str in track.split(','):
                buf.append(self._parse_note(note_str.strip(), bpm, default, octave, vfreq, vvar))

            # Pass the patch string to the track
            ret.add_track(buf, patch=wadsr_list[i])

        return ret

    def _layer_to_wadsr(self, layer):
        """
        Convert an instrument layer definition to a WADSR patch string.
        Format: wave,attack,decay,sustain,release,gain
        """
        wave = layer.get('wave', 'i')
        attack = layer.get('attack', 0)
        decay = layer.get('decay', 0)
        sustain = layer.get('sustain', 1000)
        release = layer.get('release', 0)
        gain = layer.get('gain', 1.0)
        octave_offset = layer.get('octave_offset', 0)

        return f"{wave},{attack},{decay},{sustain},{release},{gain},{octave_offset}"

    def parse(self, ptttl_string):
        """
        Extracts song data from 4-field PTTTLIS source text.
        """

        lines = [x.strip() for x in ptttl_string.split('\n')]
        cleaned = ''.join([x for x in lines if not _ignore_line(x)])
        fields = [f.strip() for f in cleaned.split(':')]

        if len(fields) == 3:
            fields.append(default_wadsr)
        elif len(fields) != 4:
            raise PTTTLSyntaxError('expecting 3 or 4 colon-separated fields (name:config:notes:[instruments])')

        self.name = fields[0].strip()
        
        # Capture the variables returned from config parser
        bpm, default, octave, vfreq, vvar = self._parse_config_line(fields[1])

        # Track compilation
        numtracks = -1
        blocks = fields[2].split(';')
        trackdata = []

        for block in blocks:
            tracks = [x.strip().strip(',') for x in block.split('|')]
            if (numtracks > 0) and (len(tracks) != numtracks):
                raise PTTTLSyntaxError('All blocks must have the same number of tracks')

            numtracks = len(tracks)
            trackdata.append(tracks)

        tracks = [''] * numtracks
        for i in range(len(trackdata)):
            for j in range(numtracks):
                tracks[j] += trackdata[i][j]
                if i < (len(trackdata) - 1):
                    tracks[j] += ","

        if vfreq is None: vfreq = default_vfreq
        if vvar is None: vvar = default_vvar
        patches = [p.strip() for p in fields[3].split('|') if p.strip() != ""]

        # Expand instruments to all layers, duplicating corresponding tracks
        expanded_tracks = []
        expanded_patches = []
        
        for track_idx, track in enumerate(tracks):
            patch = patches[track_idx] if track_idx < len(patches) else default_wadsr
            
            if is_instrument_name(patch):
                instrument = load_instrument(patch)
                if instrument and 'layers' in instrument and len(instrument['layers']) > 0:
                    # Duplicate this track for each layer
                    for layer in instrument['layers']:
                        expanded_tracks.append(track)
                        expanded_patches.append(self._layer_to_wadsr(layer))
                else:
                    _LOGGER.warning("Instrument '%s' not found. Using default patch.", patch)
                    expanded_tracks.append(track)
                    expanded_patches.append(default_wadsr)
            else:
                expanded_tracks.append(track)
                expanded_patches.append(patch)
        
        tracks = expanded_tracks
        patches = expanded_patches

        return self._parse_notes(tracks, patches, bpm, default, octave, vfreq, vvar)