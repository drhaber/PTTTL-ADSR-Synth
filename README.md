# PTTTL with ADSR Synth

This synth uses an extended version of the Nokia RTTTL (Ring Tone Text Transfer Language) format, adding support for multiple tracks (polyphony), ADSR envelopes, vibrato, and custom instrument definitions.

## Song String Syntax

A song string consists of four colon-separated fields:
`Name : Settings : Notes : Instruments`

Example:
`hot_cross_buns:d=4,o=4,b=120:e,d,c,2e,d,c,2d,8c,8c,8c,8c,8d,8d,8d,8d,e,d,2c|e,d,c,2e,d,c,2d,8c,8c,8c,8c,8d,8d,8d,8d,e,d,2c:piano|flute`

---

### 1. Name
A descriptive name for the sequence. Used for the filename when rendering to WAV.

### 2. Settings
A comma-separated list of song defaults for the sequence:
*   `b=int`: BPM (Beats Per Minute).
*   `d=int`: Song note duration (1, 2, 4, 8, 16, 32).
*   `o=int`: Song octave (0-8).
*   `f=float`: Song vibrato frequency (Hz).
*   `v=float`: Song vibrato variance (Hz).

### 3. Notes (Polyphonic & Multi-track)
Notes are organized into **tracks** and **blocks**.

*   **Track Separator (`|`)**: Used to play different notes at the same time.

#### Note Format:
`[duration]note[octave][.][v[freq-var]]`

*   **Duration**: Optional. (e.g., `8` for an eighth note).
*   **Note**: `a` through `g`, with `#` for sharps or `b` for flats. `p` represents a rest (pause).
*   **Octave**: Optional. (e.g., `4`).
*   **Dot (`.`)**: Optional. Increases duration by 50%.
*   **Vibrato (`v`)**: Optional. 
    *   `v`: Uses global default vibrato.
    *   `v7-20`: Sets vibrato to 7Hz frequency and 20Hz variance for that specific note.

**Example Multi-track**
`hot_cross_buns_whistle:d=4,o=5,b=120:bv4-150,av4-150,2gv4-150,bv4-150,av4-150,2gv4-150,8g,8g,8g,8g,8a,8a,8a,8a,bv4-150,av4-150,2gv4-150 | bv4-150,av4-150,2gv4-150,bv4-150,av4-150,2gv4-150,8g,8g,8g,8g,8a,8a,8a,8a,bv4-150,av4-150,2gv4-150 : i,20,50,900,40 | t,25,0,1000,30`

---

### 4. Instruments / Patches
This field defines the sound profile for each track, separated by `|`.
Intrument Patches match tracks one to one

#### Option A: Named Instrument
Reference a YAML file in the `instruments/` directory (e.g., `flute`). If the instrument has multiple layers, the corresponding note track will be duplicated for each layer automatically.

[Here is a Flute](instruments/flute.yaml)

#### Option B: Positional Patch
`wave,attack,decay,sustain,release,gain,octave_offset`
*   **wave**: `i` (Sine), `q` (Square), `t` (Triangle), `s` (Sawtooth).
*   **ADR**: Time in milliseconds.
*   **Sustain**: Level from 0 to 1000.
*   **Gain**: 0.0 to 1.0.
*   **Octave Offset**: Relative change to the note's octave (e.g., `-1`).

`i,10,50,800,100,0.8,0`

#### Option C: Keyed Patch
`w=i,a=10,s=800,g=0.5` (Unspecified values use defaults).

---

## Examples

**Simple Sine Melody:**
`Scale:b=120:c,d,e,f,g,a,b,c5:i,10,10,1000,10,1.0,0`

**Polyphonic Flute:**
`Harmony:b=100,d=4:c,d,e,f,g,a,b,c5|e,f,g,a,b,c5,d5,e5|g,a,b,c5,d5,e5,f5,g5:flute|flute|flute`

**Dotted Notes & Vibrato:**
`UFO:b=80:2c.v5-30,4p,4g:i,100,100,1000,500,0.7,0`


RTTTL Collection
https://picaxe.com/rtttl-ringtones-for-tune-command/

---

## Resources

[Original ptttl library by Erik Nyquist](https://github.com/eriknyquist/ptttl) ⚖️ [MIT License](https://github.com/eriknyquist/ptttl?tab=MIT-1-ov-file#readme)


[Orginal Tone Generator by Erik Nyquist](https://github.com/eriknyquist/tones) ⚖️ [Apache 2.0 License](https://github.com/eriknyquist/tones?tab=Apache-2.0-1-ov-file#readme)

---

## License

[MIT License](https://github.com/drhaber/PTTTL-ADSR-Synth?tab=MIT-1-ov-file#readme)
