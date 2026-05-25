"""
This module is a modified version of the original work found at:
https://github.com/eriknyquist/tones

Original Copyright:
Copyright (c) 2016 Erik Nyquist

Modifications:

---
This file has been updated to allow the mixing of multitrack intruments to create more complex sounds. 
This allow for the specification of ADSR envelope parameters on a per-track basis. 
The original code only supported a single track with a single set of fixed ADSR parameters.
---

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""

import struct
import math
from typing import List

# Wave type constants
SINE_WAVE = 0
SQUARE_WAVE = 1
TRIANGLE_WAVE = 2
SAWTOOTH_WAVE = 3

# Audio constants
MAX_SAMPLE_VALUE = 32767
NUM_CHANNELS = 1
DATA_SIZE = 2

# Utility functions (from tones._utils)
def _translate(val, in_min, in_max, out_min, out_max):
    """Translate a value from one range to another"""
    if in_max == in_min:
        return out_min
    return out_min + (val - in_min) * (out_max - out_min) / (in_max - in_min)

def _sine_wave_samples(freq, rate, amp, num):
    """
    Generates a set of audio samples taken at the given sampling rate 
    representing a sine wave oscillating at the given frequency with 
    the given amplitude lasting for the given duration.

    :param float freq The frequency of oscillation of the sine wave
    :param int rate The sampling rate
    :param float amp The amplitude of the sine wave
    :param float num The number of samples to generate.

    :return List[float] The audio samples representing the signal as 
                        described above.
    """
    step = (2.0 * math.pi * freq / rate)
    return [amp * math.sin(step * i) for i in range(num)]

def _square_wave_samples(freq, rate, amp, num):
    """
    Generates a set of audio samples taken at the given sampling rate 
    representing a square wave oscillating at the given frequency with 
    the given amplitude lasting for the given duration.

    :param float freq The frequency of oscillation of the square wave
    :param int rate The sampling rate
    :param float amp The amplitude of the square wave
    :param float num The number of samples to generate.

    :return List[float] The audio samples representing the signal as 
                        described above.
    """
    period = rate / freq
    half_period = period / 2.0
    return [amp if (i % period) < half_period else -amp for i in range(num)]

def _triangle_wave_samples(freq, rate, amp, num):
    """
    Generates a set of audio samples taken at the given sampling rate 
    representing a triangle wave oscillating at the given frequency with 
    the given amplitude lasting for the given duration.

    :param float freq The frequency of oscillation of the triangle wave
    :param int rate The sampling rate
    :param float amp The amplitude of the triangle wave
    :param float num The number of samples to generate.

    :return List[float] The audio samples representing the signal as 
                        described above.
    """
    period = rate / freq
    samples = []
    for i in range(num):
        phase = (i % period) / period
        if phase < 0.25:
            samples.append(amp * (phase * 4.0))
        elif phase < 0.75:
            samples.append(amp * (2.0 - phase * 4.0))
        else:
            samples.append(amp * (phase * 4.0 - 4.0))
    return samples

def _sawtooth_wave_samples(freq, rate, amp, num):
    """
    Generates a set of audio samples taken at the given sampling rate 
    representing a sawtooth wave oscillating at the given frequency with 
    the given amplitude lasting for the given duration.

    :param float freq The frequency of oscillation of the sawtooth wave
    :param int rate The sampling rate
    :param float amp The amplitude of the sawtooth wave
    :param float num The number of samples to generate.

    :return List[float] The audio samples representing the signal as 
                        described above.
    """
    period = rate / freq
    return [amp * (2.0 * ((i % period) / period) - 1.0) for i in range(num)]

class Samples(list):
    """
    Extension of list class with methods useful for manipulating audio samples
    """

    def _pack_sample(self, sample):
        ret = int(sample * MAX_SAMPLE_VALUE)
        maxp = int(MAX_SAMPLE_VALUE)

        if ret < -maxp:
            ret = -maxp
        elif ret > maxp:
            ret = maxp

        return struct.pack('h', ret)

    def serialize(self):
        """
        Serializes all samples

        :return: serialized samples
        :rtype: bytes
        """

        return bytes(b'').join([bytes(self._pack_sample(s)) for s in self])

class Tone(object):
    """
    Represents a fixed monophonic tone
    """

    _pitch_time_step = 0.001

    _sample_generators = {
        SINE_WAVE: _sine_wave_samples,
        SQUARE_WAVE: _square_wave_samples,
        TRIANGLE_WAVE: _triangle_wave_samples,
        SAWTOOTH_WAVE: _sawtooth_wave_samples
    }

    def __init__(self, rate, amplitude, wavetype):
        """
        Initializes a Tone

        :param int wavetype: waveform type
        :param float frequency: tone frequency
        :param int rate: sample rate for generating samples
        :param float amplitude: Tone amplitude, where 1.0 is the max. sample \
            value and 0.0 is total silence
        """

        try:
            self.samplefunc = self._sample_generators[wavetype]
        except KeyError:
            raise ValueError("Invalid wave type: %s" % wavetype)

        self._amp = amplitude
        self._rate = rate

    def _variable_pitch_tone(self, points, phase):
        sample_step = int(self._pitch_time_step * self._rate)

        i = 0
        ret = Samples()

        for freq in points:
            period = int(self._rate / freq)
            generated_samples = self.samplefunc(freq, self._rate, self._amp, period)
            i = self._phase_to_index(phase, period)

            for _ in range(sample_step):
                ret.append(generated_samples[i % period])
                i += 1

            phase = self._index_to_phase(i % period, period)

        return ret, phase

    def _vibrato_pitch_change(self, numsamples, freq, variance, phase):
        stepsamples = self._pitch_time_step * self._rate
        numsteps = float(numsamples) / stepsamples
        points = []
        half = variance / 2.0

        generated_samples = _sine_wave_samples(freq, int(1.0 / self._pitch_time_step), 1.0, int(numsteps))
        i = self._phase_to_index(phase, len(generated_samples))

        for _ in range(int(numsteps)):
            point = generated_samples[i]
            points.append(_translate(point, 0.0, 1.0, -half, half))
            i += 1

        return points, phase

    def _linear_pitch_change(self, numsamples, start, end):
        stepsamples = self._pitch_time_step * self._rate
        numsteps = float(numsamples) / stepsamples
        freqstep = (end - start) / numsteps

        freq = float(start)
        ret = [freq]

        for _ in range(int(numsteps) - 1):
            freq += freqstep
            ret.append(freq)

        return ret

    def samples(self, num, frequency, endfrequency=None, attack=0.05,
            decay=0.05, sustain=1.0, release=0.05, phase=0.0, vphase=0.0,
            vibrato_frequency=None, vibrato_variance=20.0):
        """
        Generate tone for a specific number of samples

        :param int num: number of samples to generate
        :param float frequency: tone frequency in Hz
        :param float endfrequency: If not None, the tone frequency will change \
            between 'frequency' and 'endfrequency' in increments of 1ms over \
            all samples
        :param float attack: tone attack in seconds
        :param float decay: tone decay in seconds
        :param float sustain: tone sustain level (0.0-1.0)
        :param float release: tone release time in seconds
        :param float phase: starting phase of generated tone in radians
        :param float vphase: starting phase of vibrato in radians
        :param float vibrato_frequency: vibrato frequency in Hz
        :param float vibrato_variance: vibrato variance in Hz
        :return: samples in the range of -1.0 to 1.0, tone phase, vibrato phase
        :rtype: tuple of the form (samples, phase, vibrato_phase)
        """

        points = None

        if not endfrequency is None:
            points = self._linear_pitch_change(num, frequency,
                endfrequency)

        if not vibrato_frequency is None:
            vpoints, vphase = self._vibrato_pitch_change(num, vibrato_frequency,
                vibrato_variance, vphase)

            if points is None:
                points = [frequency + p for p in vpoints]
            else:
                points = [points[i] + vpoints[i] for i in range(len(points))]

        if points is None:
            # Directly use the generated list to avoid redundant iteration
            samples = Samples(self.samplefunc(frequency, self._rate, self._amp, num))
            
            # Calculate phase for the next note based on the actual frequency period
            actual_period = self._rate / frequency
            phase = self._index_to_phase(num % actual_period, actual_period)
        else:
            samples, phase = self._variable_pitch_tone(points, phase)

        # Apply ADSR envelope
        nA = int(attack * self._rate) if attack else 0
        nD = int(decay * self._rate) if decay else 0
        nR = int(release * self._rate) if release else 0
        nTotal = len(samples)
        s_level = sustain if sustain is not None else 1.0

        # Linear Attack: 0.0 to 1.0
        if nA > 0:
            for i in range(min(nA, nTotal)):
                samples[i] *= (i / float(nA))

        # Linear Decay: 1.0 to Sustain level
        if nD > 0:
            for i in range(nA, min(nA + nD, nTotal)):
                # (1.0 - s_level) is the total drop. (i-nA)/nD is the progress.
                samples[i] *= (1.0 - (1.0 - s_level) * (i - nA) / float(nD))

        # Sustain: Maintain s_level until the release phase begins
        nS_end = max(0, nTotal - nR)
        if nS_end > (nA + nD):
            for i in range(nA + nD, nS_end):
                samples[i] *= s_level

        # Linear Release: Sustain level to 0.0
        if nR > 0:
            # Calculate start of release relative to the end of the sample buffer
            release_start = max(0, nTotal - nR)
            for i in range(release_start, nTotal):
                # Progression from 0 (start) to 1 (end of buffer)
                rel_i = i - release_start
                samples[i] *= (s_level * (1.0 - rel_i / float(nR)))

        return samples, phase, vphase

    @staticmethod
    def _index_to_phase(index, size):
        return (float(index) / size) * 360.0

    @staticmethod
    def _phase_to_index(phase, size):
        return int((float(phase) / 360.0) * size) % int(size)
